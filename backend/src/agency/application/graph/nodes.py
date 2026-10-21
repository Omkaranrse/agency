"""Graph node implementations orchestrating application agents and ports."""

import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from langgraph.types import interrupt

from agency.application.agents.builder_agent import BuilderAgent
from agency.application.agents.designer_agent import DesignerAgent
from agency.application.agents.models import (
    BuilderContext,
    DesignerResult,
    PMClarificationResult,
    PMSpecResult,
)
from agency.application.agents.pm_agent import PMAgent
from agency.application.graph.approval import (
    ApprovalDecision,
    ApprovalDecisionType,
    validate_approval_decision,
)
from agency.application.graph.errors import (
    ApprovalValidationError,
    GraphStateError,
)
from agency.application.graph.state import WorkflowState
from agency.application.ports.deploy import DeployPort
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.ports.sandbox import SandboxPort
from agency.application.ports.tracing import NoOpTracingPort, TracingPort
from agency.application.qa.models import QAContext
from agency.application.qa.service import QAService
from agency.domain.entities.brief import Brief
from agency.domain.entities.design_tokens import DesignTokens
from agency.domain.entities.page_content import PageContent
from agency.domain.entities.qa_report import QAReport
from agency.domain.entities.run import Run
from agency.domain.entities.spec import Spec
from agency.domain.enums import RunState

logger = logging.getLogger(__name__)


def _traced_node(
    node_name: str,
) -> Callable[[Callable[..., dict[str, Any]]], Callable[..., dict[str, Any]]]:
    """Decorator to trace node execution spans and record errors or pauses."""

    def decorator(
        func: Callable[..., dict[str, Any]],
    ) -> Callable[..., dict[str, Any]]:
        @wraps(func)
        def wrapper(self: Any, state: WorkflowState) -> dict[str, Any]:
            run_id = str(state.get("run_id", "unknown"))
            span = self.tracing.start_span(
                trace_id=run_id,
                name=f"node.{node_name}",
                metadata={"run_id": run_id, "stage": node_name},
            )
            try:
                result = func(self, state)
                status = "error" if result.get("current_stage") == "fail" else "success"
                error = result.get("failure_message") if status == "error" else None
                self.tracing.end_span(span, status=status, error=error)
                return result
            except Exception as exc:
                if type(exc).__name__ == "GraphInterrupt":
                    self.tracing.end_span(
                        span, status="paused", metadata={"paused": True}
                    )
                else:
                    self.tracing.end_span(span, status="error", error=str(exc))
                raise

        return wrapper

    return decorator


class GraphNodes:
    """Injectable workflow node handlers coordinating existing use cases and ports."""

    def __init__(
        self,
        repository: RunRepositoryPort,
        event_bus: EventBusPort,
        pm_agent: PMAgent,
        designer_agent: DesignerAgent,
        builder_agent: BuilderAgent,
        qa_service: QAService,
        sandbox: SandboxPort,
        deploy_port: DeployPort,
        tracing: TracingPort | None = None,
    ) -> None:
        self.repository = repository
        self.event_bus = event_bus
        self.pm_agent = pm_agent
        self.designer_agent = designer_agent
        self.builder_agent = builder_agent
        self.qa_service = qa_service
        self.sandbox = sandbox
        self.deploy_port = deploy_port
        self.tracing = tracing or NoOpTracingPort()

    def _save_and_publish_events(self, run: Run) -> None:
        """Drain domain events before aggregate save to avoid re-emission."""
        events = run.clear_events()
        self.repository.save(run)
        self.event_bus.publish_all(events)

    @_traced_node("intake")
    def intake(self, state: WorkflowState) -> dict[str, Any]:
        """Validate input brief, initialize or retrieve Run aggregate, start run."""
        run_id = state["run_id"]
        project_id = state["project_id"]
        brief = Brief(**state["brief"])

        run = self.repository.get_by_id(run_id)
        if run is None:
            run = Run(run_id=run_id, project_id=project_id, brief=brief)
            run.start_planning()
            self._save_and_publish_events(run)

        return {
            "current_stage": "intake",
            "prompt_versions": dict(state.get("prompt_versions", {})),
        }

    @_traced_node("pm_spec")
    def pm_spec(self, state: WorkflowState) -> dict[str, Any]:
        """Call PMAgent to generate technical specification or request clarification."""
        if state.get("cancel_requested"):
            return {"current_stage": "cancel"}

        brief_data = dict(state["brief"])
        if answers := state.get("clarification_answers"):
            lines = [f"- {q}: {a}" for q, a in answers.items()]
            notes = brief_data.get("content_notes", "")
            brief_data["content_notes"] = (
                f"{notes}\n\nClient Clarification:\n" + "\n".join(lines)
            )

        brief = Brief(**brief_data)
        result = self.pm_agent.generate_spec(brief)

        versions = dict(state.get("prompt_versions", {}))
        versions["pm"] = result.prompt_version

        if isinstance(result, PMClarificationResult):
            return {
                "current_stage": "pm_clarification",
                "clarification_questions": result.questions,
                "prompt_versions": versions,
            }

        if isinstance(result, PMSpecResult):
            run = self.repository.get_by_id(state["run_id"])
            if run and run.state == RunState.PLANNING:
                run.finish_planning(spec=result.spec)
                self._save_and_publish_events(run)

            return {
                "current_stage": "pm_spec",
                "spec": result.spec.model_dump(mode="json"),
                "clarification_questions": [],
                "prompt_versions": versions,
            }

        return {
            "current_stage": "fail",
            "failure_code": "UNKNOWN_PM_RESULT",
            "failure_message": "PMAgent returned unexpected result type.",
        }

    @_traced_node("await_clarification")
    def await_clarification(self, state: WorkflowState) -> dict[str, Any]:
        """Pause execution using interrupt to collect missing client clarification."""
        request = {
            "type": "clarification",
            "run_id": state["run_id"],
            "questions": state.get("clarification_questions", []),
        }
        raw_answers = interrupt(request)

        answers: dict[str, str] = {}
        if isinstance(raw_answers, dict):
            answers = {str(k): str(v) for k, v in raw_answers.items()}
        elif isinstance(raw_answers, str):
            answers = {"general": raw_answers}

        brief_data = dict(state["brief"])
        return {
            "brief": brief_data,
            "clarification_answers": answers,
            "clarification_questions": [],
            "current_stage": "clarified",
        }

    @_traced_node("designer")
    def designer(self, state: WorkflowState) -> dict[str, Any]:
        """Synthesize design tokens and authentic section copy via DesignerAgent."""
        if state.get("cancel_requested"):
            return {"current_stage": "cancel"}

        spec_data = state.get("spec")
        if not spec_data:
            raise GraphStateError("Cannot invoke DesignerAgent without validated Spec.")

        spec = Spec(**spec_data)
        result: DesignerResult = self.designer_agent.create_design(spec)

        versions = dict(state.get("prompt_versions", {}))
        versions["designer"] = result.prompt_version

        return {
            "current_stage": "designer",
            "design_tokens": result.tokens.model_dump(mode="json"),
            "page_content": [p.model_dump(mode="json") for p in result.pages],
            "prompt_versions": versions,
        }

    @_traced_node("preview")
    def preview(self, state: WorkflowState) -> dict[str, Any]:
        """Generate prototype preview reference and submit prototype to domain Run."""
        if state.get("cancel_requested"):
            return {"current_stage": "cancel"}

        revision = state.get("approval_revision", 0)
        run_id = state["run_id"]
        project_id = state["project_id"]

        preview_ref = f"preview-{run_id}-rev{revision}"
        preview_url = f"https://preview.agency.run/{project_id}/rev{revision}"

        run = self.repository.get_by_id(run_id)
        if run and run.state == RunState.PROTOTYPING:
            run.submit_prototype(prototype_ref=preview_ref)
            self._save_and_publish_events(run)

        return {
            "current_stage": "preview",
            "preview_result": {
                "preview_ref": preview_ref,
                "preview_url": preview_url,
                "revision": revision,
            },
            "approval_status": "pending",
        }

    @_traced_node("await_approval")
    def await_approval(self, state: WorkflowState) -> dict[str, Any]:
        """Pause at human approval gate using interrupt, resuming upon decision."""
        revision = state.get("approval_revision", 0)
        preview_res = state.get("preview_result") or {}
        preview_ref = str(preview_res.get("preview_ref", ""))
        preview_url = str(preview_res.get("preview_url", ""))
        summary = (
            f"Prototype approval for {state['brief'].get('client_name', 'Client')} "
            f"({state['brief'].get('site_type', 'Website')})"
        )

        request = {
            "type": "approval",
            "run_id": state["run_id"],
            "preview_ref": preview_ref,
            "preview_url": preview_url,
            "revision": revision,
            "summary": summary,
        }

        raw_decision = interrupt(request)

        # Parse decision
        if isinstance(raw_decision, dict):
            decision = ApprovalDecision(**raw_decision)
        elif isinstance(raw_decision, str):
            decision = ApprovalDecision(
                decision=ApprovalDecisionType(raw_decision),
                revision=revision,
            )
        elif isinstance(raw_decision, ApprovalDecision):
            decision = raw_decision
        else:
            raise ApprovalValidationError(
                f"Invalid approval decision payload type: {type(raw_decision)}"
            )

        validate_approval_decision(decision, current_revision=revision)

        run = self.repository.get_by_id(state["run_id"])

        if decision.decision == ApprovalDecisionType.APPROVE:
            if run and run.state == RunState.AWAITING_APPROVAL:
                run.approve_prototype(
                    approver=decision.approver,
                    prototype_ref=preview_ref,
                )
                self._save_and_publish_events(run)

            return {
                "current_stage": "await_approval",
                "approval_status": "approved",
                "approval_approver": decision.approver,
                "approval_comment": decision.comment,
            }

        if decision.decision == ApprovalDecisionType.REVISE:
            comment = (decision.comment or "").strip()
            if not comment:
                raise ApprovalValidationError(
                    "Revision decision requires a non-empty comment."
                )

            if run and run.state == RunState.AWAITING_APPROVAL:
                run.request_revision(reason=comment)
                self._save_and_publish_events(run)

            return {
                "current_stage": "await_approval",
                "approval_status": "revised",
                "approval_revision": revision + 1,
                "approval_comment": comment,
            }

        if decision.decision == ApprovalDecisionType.REJECT:
            comment = (decision.comment or "Rejected by client").strip()
            if run and run.state == RunState.AWAITING_APPROVAL:
                run.reject_approval(reason=comment)
                self._save_and_publish_events(run)

            return {
                "current_stage": "await_approval",
                "approval_status": "rejected",
                "approval_comment": comment,
                "failure_code": "APPROVAL_REJECTED",
                "failure_message": f"Prototype approval rejected: {comment}",
            }

        return {
            "current_stage": "fail",
            "failure_code": "INVALID_DECISION",
            "failure_message": f"Unsupported approval decision: {decision.decision}",
        }

    @_traced_node("build")
    def build(self, state: WorkflowState) -> dict[str, Any]:
        """Execute build inside isolated sandbox workspace with validated edits."""
        if state.get("cancel_requested"):
            return {"current_stage": "cancel"}

        run = self.repository.get_by_id(state["run_id"])
        if run and run.state == RunState.AWAITING_APPROVAL:
            run.start_building(commit_sha="HEAD")
            self._save_and_publish_events(run)

        # Ensure sandbox environment exists
        sandbox_id = state.get("sandbox_id")
        if sandbox_id is None:
            sandbox_id = self.sandbox.create(template="default", timeout_seconds=300)

        # Apply design tokens
        tokens_data = state.get("design_tokens")
        if tokens_data:
            tokens_css = "/* Design Tokens */\n:root {\n"
            for k, v in tokens_data.get("colors", {}).items():
                tokens_css += f"  --color-{k.replace('_', '-')}: {v};\n"
            tokens_css += "}\n"
            self.sandbox.write_file(
                sandbox_id, "src/styles/tokens.css", tokens_css.encode("utf-8")
            )

        # Apply content files
        pages_data = state.get("page_content")
        if pages_data:
            for page in pages_data:
                slug = page.get("page_slug", "home")
                content_bytes = json.dumps(page, indent=2).encode("utf-8")
                self.sandbox.write_file(
                    sandbox_id, f"src/content/{slug}.json", content_bytes
                )

        # Run build command via sandbox.exec
        exec_res = self.sandbox.exec(sandbox_id, "npm run build")
        if exec_res.exit_code != 0:
            return {
                "current_stage": "build",
                "sandbox_id": sandbox_id,
                "build_result": {
                    "success": False,
                    "exit_code": exec_res.exit_code,
                    "stderr": exec_res.stderr,
                },
                "failure_code": "BUILD_FAILED",
                "failure_message": (
                    f"Build command failed with code {exec_res.exit_code}: "
                    f"{exec_res.stderr[:200]}"
                ),
            }

        if run and run.state == RunState.BUILDING:
            run.finish_building(
                commit_sha="HEAD", workspace_path=f"workspaces/{state['project_id']}"
            )
            self._save_and_publish_events(run)

        refs = list(state.get("artifact_references", []))
        workspace_ref = f"workspaces/{state['project_id']}"
        if workspace_ref not in refs:
            refs.append(workspace_ref)

        return {
            "current_stage": "build",
            "sandbox_id": sandbox_id,
            "build_result": {"success": True, "exit_code": 0, "commit_sha": "HEAD"},
            "artifact_references": refs,
        }

    @_traced_node("qa")
    def qa(self, state: WorkflowState) -> dict[str, Any]:
        """Execute automated QA checks and evaluate quality gate."""
        if state.get("cancel_requested"):
            return {"current_stage": "cancel"}

        preview_res = state.get("preview_result") or {}
        build_res = state.get("build_result") or {}
        sandbox_id = state.get("sandbox_id")

        qa_context = QAContext(
            run_id=state["run_id"],
            project_id=state["project_id"],
            preview_base_url=str(
                preview_res.get("preview_url", "http://localhost:4321")
            ),
            build_ok=bool(build_res.get("success", True)),
            build_exit_code=int(build_res.get("exit_code", 0)),
            artifacts=list(state.get("artifact_references", ["index.html"])),
            sandbox=self.sandbox,
            sandbox_id=sandbox_id,
        )
        qa_report: QAReport = self.qa_service.run(qa_context)

        passed_count = sum(1 for c in qa_report.checks if c.passed)
        self.tracing.record_score(
            trace_id=state["run_id"],
            name="qa.overall_passed",
            value=1.0 if qa_report.overall_passed else 0.0,
            comment=f"Passed {passed_count}/{len(qa_report.checks)} checks",
        )

        run = self.repository.get_by_id(state["run_id"])
        if qa_report.overall_passed:
            if run and run.state == RunState.TESTING:
                run.pass_qa(total_checks=len(qa_report.checks))
                self._save_and_publish_events(run)

            return {
                "current_stage": "qa",
                "qa_report": qa_report.model_dump(mode="json"),
            }

        # QA failed
        repair_attempts = state.get("repair_attempts", 0)
        if repair_attempts >= 3:
            failed_names = [c.name for c in qa_report.checks if not c.passed]
            if run and run.state == RunState.TESTING:
                run.fail_qa(
                    reason="QA repair cycles exhausted",
                    failed_checks=failed_names,
                )
                self._save_and_publish_events(run)

            return {
                "current_stage": "qa",
                "qa_report": qa_report.model_dump(mode="json"),
                "failure_code": "QA_EXHAUSTED",
                "failure_message": (
                    f"QA checks failed after 3 repair attempts: {failed_names}"
                ),
            }

        return {
            "current_stage": "qa",
            "qa_report": qa_report.model_dump(mode="json"),
        }

    @_traced_node("repair")
    def repair(self, state: WorkflowState) -> dict[str, Any]:
        """Propose and apply validated file repairs for QA failures."""
        if state.get("cancel_requested"):
            return {"current_stage": "cancel"}

        repair_attempts = state.get("repair_attempts", 0) + 1
        spec_data = state.get("spec")
        tokens_data = state.get("design_tokens")
        pages_data = state.get("page_content") or []
        qa_data = state.get("qa_report")

        if not spec_data or not tokens_data:
            raise GraphStateError(
                "Cannot repair without validated Spec and DesignTokens."
            )

        spec = Spec(**spec_data)
        tokens = DesignTokens(**tokens_data)
        pages = [PageContent(**p) for p in pages_data]
        qa_report = QAReport(**qa_data) if qa_data else None

        context = BuilderContext(
            run_id=state["run_id"],
            spec=spec,
            tokens=tokens,
            pages=pages,
            current_revision=state.get("approval_revision", 0),
            qa_report=qa_report,
            allow_component_escalation=False,
        )

        builder_result = self.builder_agent.propose_edits(context)
        sandbox_id = state.get("sandbox_id")

        if sandbox_id:
            for edit in builder_result.edits:
                self.sandbox.write_file(
                    sandbox_id,
                    edit.path,
                    edit.content.encode("utf-8"),
                )

        versions = dict(state.get("prompt_versions", {}))
        versions["builder"] = builder_result.prompt_version

        return {
            "current_stage": "repair",
            "repair_attempts": repair_attempts,
            "prompt_versions": versions,
        }

    @_traced_node("deploy")
    def deploy(self, state: WorkflowState) -> dict[str, Any]:
        """Deploy application to production after passing QA and human approval."""
        if state.get("cancel_requested"):
            return {"current_stage": "cancel"}

        # Idempotency check: if already deployed in this workflow, avoid redeploying
        if state.get("deployment_result"):
            return {
                "current_stage": "deploy",
                "deployment_result": state["deployment_result"],
            }

        build_res = state.get("build_result") or {}
        commit_sha = str(build_res.get("commit_sha", "HEAD"))
        project_id = state["project_id"]

        try:
            deployment = self.deploy_port.deploy_production(
                project_id=project_id, commit_sha=commit_sha
            )
        except Exception as exc:
            logger.error("Deployment failed for project %s: %s", project_id, exc)
            return {
                "current_stage": "deploy",
                "failure_code": "DEPLOYMENT_FAILED",
                "failure_message": f"Deployment failed: {exc}",
            }

        run = self.repository.get_by_id(state["run_id"])
        if run and run.state == RunState.DEPLOYING:
            run.complete_deployment(
                url=str(deployment.production_url or deployment.preview_url),
                provider=deployment.provider,
                is_production=True,
            )
            self._save_and_publish_events(run)

        return {
            "current_stage": "deploy",
            "deployment_result": {
                "provider": deployment.provider,
                "production_url": str(deployment.production_url)
                if deployment.production_url
                else None,
                "preview_url": str(deployment.preview_url),
                "deployed_at": deployment.deployed_at.isoformat(),
            },
        }

    @_traced_node("handover")
    def handover(self, state: WorkflowState) -> dict[str, Any]:
        """Generate structured handover report and clean up active sandbox."""
        deploy_res = state.get("deployment_result") or {}
        preview_res = state.get("preview_result") or {}
        preview_url = deploy_res.get("preview_url") or preview_res.get("preview_url")
        production_url = deploy_res.get("production_url")

        handover_report = {
            "run_id": state["run_id"],
            "client_summary": {
                "client_name": state["brief"].get("client_name"),
                "site_type": state["brief"].get("site_type"),
                "tone": state["brief"].get("tone"),
            },
            "preview_url": preview_url,
            "production_url": production_url,
            "repository_reference": f"workspaces/{state['project_id']}",
            "build_status": "success",
            "qa_status": "passed",
            "prompt_versions": state.get("prompt_versions", {}),
            "artifact_references": state.get("artifact_references", []),
            "known_limitations": [
                "Static Astro template without server-side database",
                "Contact form submissions are handled externally",
            ],
        }

        # Sandbox cleanup
        sandbox_id = state.get("sandbox_id")
        if sandbox_id:
            try:
                self.sandbox.destroy(sandbox_id)
            except Exception:
                logger.warning(
                    "Failed to destroy sandbox '%s' during handover", sandbox_id
                )

        return {
            "current_stage": "handover",
            "handover_report": handover_report,
        }

    @_traced_node("cancel")
    def cancel(self, state: WorkflowState) -> dict[str, Any]:
        """Record workflow cancellation and clean up active sandbox."""
        reason = state.get("cancellation_reason") or "Workflow cancelled"
        run = self.repository.get_by_id(state["run_id"])
        if run and run.state not in Run.TERMINAL_STATES:
            run.cancel(reason=reason)
            self._save_and_publish_events(run)

        sandbox_id = state.get("sandbox_id")
        if sandbox_id:
            try:
                self.sandbox.destroy(sandbox_id)
            except Exception:
                logger.warning(
                    "Failed to destroy sandbox '%s' during cancellation", sandbox_id
                )

        return {
            "current_stage": "cancel",
            "cancel_requested": True,
            "cancellation_reason": reason,
        }

    @_traced_node("fail")
    def fail(self, state: WorkflowState) -> dict[str, Any]:
        """Record workflow failure and clean up active sandbox."""
        reason = state.get("failure_message") or "Workflow failed"
        run = self.repository.get_by_id(state["run_id"])
        if run and run.state not in Run.TERMINAL_STATES:
            run.fail(reason=reason)
            self._save_and_publish_events(run)

        sandbox_id = state.get("sandbox_id")
        if sandbox_id:
            try:
                self.sandbox.destroy(sandbox_id)
            except Exception:
                logger.warning(
                    "Failed to destroy sandbox '%s' during failure", sandbox_id
                )

        return {
            "current_stage": "fail",
        }
