"""BuilderAgent generating safe, minimal file edit proposals.

Synthesizes edits from design and QA context without direct filesystem access.
"""

from agency.application.agents.file_edit_policy import FileEditPolicy
from agency.application.agents.input_sanitizer import InputSanitizer
from agency.application.agents.models import (
    BuilderContext,
    BuilderOutputSchema,
    BuilderResult,
)
from agency.application.agents.prompt_loader import PromptLoader
from agency.application.ports.llm import LLMPort


class BuilderAgent:
    """Builder agent synthesizing file modifications without direct filesystem I/O."""

    def __init__(
        self,
        llm: LLMPort,
        file_edit_policy: FileEditPolicy | None = None,
        prompt_loader: PromptLoader | None = None,
        prompt_version: str = "v1",
    ) -> None:
        self.llm = llm
        self.file_edit_policy = file_edit_policy or FileEditPolicy()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.prompt_version = prompt_version

    def propose_edits(self, context: BuilderContext) -> BuilderResult:
        """Analyze specifications, design assets, and QA reports to propose edits."""
        # 1. Load versioned prompt
        system_prompt = self.prompt_loader.load_prompt("builder", self.prompt_version)

        # 2. Package context into isolated untrusted data payloads
        context_data = {
            "spec": context.spec.model_dump(mode="json"),
            "tokens": context.tokens.model_dump(mode="json"),
            "pages": [p.model_dump(mode="json") for p in context.pages],
            "revision": context.current_revision,
            "allow_component_escalation": context.allow_component_escalation,
        }
        context_payload = InputSanitizer.wrap_untrusted(
            "untrusted_context", context_data
        )

        qa_payload = ""
        if context.qa_report is not None:
            failed_checks = [
                c.model_dump(mode="json")
                for c in context.qa_report.checks
                if not c.passed
            ]
            qa_summary = {
                "overall_passed": context.qa_report.overall_passed,
                "failed_checks": failed_checks,
            }
            qa_payload = "\n\n" + InputSanitizer.wrap_untrusted(
                "untrusted_qa_report", qa_summary
            )

        instructions = (
            "Review the approved design and any QA issues, "
            "then propose necessary file edits:\n\n"
        )
        full_prompt = (
            f"{system_prompt}\n\n{instructions}{context_payload}{qa_payload}\n"
        )

        # 3. Request structured edit proposal from LLM
        response: BuilderOutputSchema = self.llm.generate_structured(
            schema=BuilderOutputSchema,
            prompt=full_prompt,
            role="builder",
            run_id=context.run_id,
            correlation_id=context.correlation_id,
        )

        # 4. Enforce strict, server-side security and schema validation
        validated_edits = self.file_edit_policy.validate_edits(
            raw_edits=response.edits,
            context=context,
            prompt_version=self.prompt_version,
        )

        return BuilderResult(
            edits=validated_edits,
            prompt_version=self.prompt_version,
            revision_number=context.current_revision,
        )
