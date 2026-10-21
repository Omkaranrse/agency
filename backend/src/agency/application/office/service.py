"""OfficeStateService derives virtual office state and agent tasks
from authoritative aggregates.
"""

from datetime import datetime
from typing import Any

from agency.application.errors import RunNotFoundError
from agency.application.office.models import (
    AgentRoleEnum,
    EmployeeStatusEnum,
    OfficeEmployeeState,
    OfficeState,
    TaskRecord,
    TaskStatusEnum,
    WorkstationEnum,
    WorkstationState,
)
from agency.application.ports.artifact_storage import ArtifactStoragePort
from agency.application.ports.event_feed import EventEnvelope, EventFeedPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.entities.run import Run
from agency.domain.enums import RunState


class OfficeStateService:
    """Derives office state, employee statuses, and task records for a run."""

    def __init__(
        self,
        repository: RunRepositoryPort,
        event_feed: EventFeedPort | None = None,
        artifact_storage: ArtifactStoragePort | None = None,
    ) -> None:
        self.repository = repository
        self.event_feed = event_feed
        self.artifact_storage = artifact_storage

    def get_run_tasks(self, run_id: str) -> list[TaskRecord]:
        """Retrieve authoritative task records for a given run."""
        office_state = self.get_office_state(run_id)
        return office_state.tasks

    def get_office_state(self, run_id: str) -> OfficeState:
        """Derive the complete virtual office snapshot for a given run.

        Raises:
            RunNotFoundError: If the run aggregate does not exist.
        """
        run = self.repository.get_by_id(run_id)
        if run is None:
            raise RunNotFoundError(f"Run {run_id} not found.")

        # 1. Fetch domain events if event feed is available
        events: list[EventEnvelope] = []
        if self.event_feed is not None:
            try:
                events = self.event_feed.get_events(run_id=run_id, limit=200)
            except Exception:
                events = []

        # Index events by event_type for fast lookup
        events_by_type: dict[str, list[EventEnvelope]] = {}
        for ev in events:
            events_by_type.setdefault(ev.event_type, []).append(ev)

        # 2. Fetch artifact IDs if artifact storage is available
        artifacts: list[str] = []
        if self.artifact_storage is not None:
            try:
                artifact_metas = self.artifact_storage.list_artifacts(run_id)
                artifacts = [a.artifact_id for a in artifact_metas]
            except Exception:
                artifacts = []

        # 3. Derive TaskRecords
        tasks = self._derive_tasks(run, events_by_type, artifacts)

        # 4. Derive Employees
        employees = self._derive_employees(run, tasks, events_by_type)

        # 5. Derive Workstations
        workstations = self._derive_workstations(run, tasks)

        # 6. Identify active task and blockers
        active_task_id = None
        for t in tasks:
            if t.status in (
                TaskStatusEnum.IN_PROGRESS,
                TaskStatusEnum.WAITING_APPROVAL,
            ):
                active_task_id = t.id
                break

        blockers: list[str] = []
        if run.failure_reason:
            blockers.append(run.failure_reason)
        if run.cancellation_reason:
            blockers.append(run.cancellation_reason)

        return OfficeState(
            run_id=run.run_id,
            project_id=run.project_id,
            run_status=run.state.value,
            current_stage=run.state.value.lower(),
            employees=employees,
            workstations=workstations,
            tasks=tasks,
            active_task_id=active_task_id,
            blockers=blockers,
            updated_at=run.updated_at,
        )

    def _derive_tasks(
        self,
        run: Run,
        events: dict[str, list[EventEnvelope]],
        artifact_ids: list[str],
    ) -> list[TaskRecord]:
        """Derive all tasks across the delivery pipeline with real timestamps
        and status.
        """
        state = run.state

        # Helper to get timestamp of first or last occurrence
        def first_ts(event_type: str) -> datetime | None:
            evs = events.get(event_type)
            return evs[0].occurred_at if evs else None

        def last_ts(event_type: str) -> datetime | None:
            evs = events.get(event_type)
            return evs[-1].occurred_at if evs else None

        # Related artifacts partitioning
        spec_artifacts = [
            a for a in artifact_ids if "spec" in a.lower() or "brief" in a.lower()
        ]
        design_artifacts = [
            a for a in artifact_ids if "token" in a.lower() or "page" in a.lower()
        ]
        build_artifacts = [
            a for a in artifact_ids if "build" in a.lower() or "workspace" in a.lower()
        ]
        qa_artifacts = [
            a for a in artifact_ids if "qa" in a.lower() or "report" in a.lower()
        ]
        deploy_artifacts = [
            a for a in artifact_ids if "deploy" in a.lower() or "url" in a.lower()
        ]

        tasks: list[TaskRecord] = []

        # 1. PM Task: Planning
        planning_status = TaskStatusEnum.PENDING
        planning_started: datetime | None = first_ts("RunStarted") or run.created_at
        planning_completed = first_ts("PlanningCompleted")
        planning_blocker = None
        planning_progress = None

        if state == RunState.CREATED:
            planning_status = TaskStatusEnum.PENDING
            planning_started = None
        elif state == RunState.PLANNING:
            planning_status = TaskStatusEnum.IN_PROGRESS
            planning_progress = "Analyzing brief and drafting technical specification."
        elif state in (
            RunState.PROTOTYPING,
            RunState.AWAITING_APPROVAL,
            RunState.BUILDING,
            RunState.TESTING,
            RunState.DEPLOYING,
            RunState.COMPLETED,
        ):
            planning_status = TaskStatusEnum.COMPLETED
            planning_progress = "Specification and architecture completed."
        elif state == RunState.FAILED and not planning_completed:
            planning_status = TaskStatusEnum.FAILED
            planning_blocker = run.failure_reason
        elif state == RunState.CANCELLED and not planning_completed:
            planning_status = TaskStatusEnum.BLOCKED
            planning_blocker = run.cancellation_reason

        tasks.append(
            TaskRecord(
                id=f"{run.run_id}-task-planning",
                run_id=run.run_id,
                agent_role=AgentRoleEnum.PM,
                task_type="planning",
                title="Specification & Requirements Analysis",
                status=planning_status,
                started_at=planning_started,
                updated_at=planning_completed or planning_started or run.updated_at,
                completed_at=planning_completed,
                progress_details=planning_progress,
                blocker=planning_blocker,
                attempt_number=1,
                related_artifact_ids=spec_artifacts,
            )
        )

        # 2. Designer Task: Prototyping
        design_status = TaskStatusEnum.PENDING
        design_started = planning_completed or first_ts("PlanningCompleted")
        design_completed = last_ts("PrototypeReady")
        design_blocker = None
        design_progress = None

        if state in (RunState.CREATED, RunState.PLANNING):
            design_status = TaskStatusEnum.PENDING
            design_started = None
        elif state == RunState.PROTOTYPING:
            design_status = TaskStatusEnum.IN_PROGRESS
            design_progress = (
                f"Generating design tokens and UI sections "
                f"(Revision {run.revision_count})."
            )
        elif state in (
            RunState.AWAITING_APPROVAL,
            RunState.BUILDING,
            RunState.TESTING,
            RunState.DEPLOYING,
            RunState.COMPLETED,
        ):
            design_status = TaskStatusEnum.COMPLETED
            design_progress = "Design tokens and prototype content synthesized."
        elif state == RunState.FAILED and not design_completed and planning_completed:
            design_status = TaskStatusEnum.FAILED
            design_blocker = run.failure_reason
        elif (
            state == RunState.CANCELLED and not design_completed and planning_completed
        ):
            design_status = TaskStatusEnum.BLOCKED
            design_blocker = run.cancellation_reason

        tasks.append(
            TaskRecord(
                id=f"{run.run_id}-task-design",
                run_id=run.run_id,
                agent_role=AgentRoleEnum.DESIGNER,
                task_type="design",
                title="Design Tokens & Layout Synthesis",
                status=design_status,
                started_at=design_started,
                updated_at=design_completed or design_started or run.updated_at,
                completed_at=design_completed,
                progress_details=design_progress,
                blocker=design_blocker,
                attempt_number=run.revision_count + 1,
                related_artifact_ids=design_artifacts,
            )
        )

        # 3. Reviewer Task: Human Review
        review_status = TaskStatusEnum.PENDING
        review_started = design_completed or first_ts("PrototypeReady")
        review_completed = first_ts("PrototypeApproved")
        review_blocker = None
        review_progress = None

        if state in (RunState.CREATED, RunState.PLANNING, RunState.PROTOTYPING):
            review_status = TaskStatusEnum.PENDING
            review_started = None
        elif state == RunState.AWAITING_APPROVAL:
            review_status = TaskStatusEnum.WAITING_APPROVAL
            preview_url = run.prototype_ref or "Ready for preview"
            review_progress = f"Awaiting operator review on preview: {preview_url}"
        elif state in (
            RunState.BUILDING,
            RunState.TESTING,
            RunState.DEPLOYING,
            RunState.COMPLETED,
        ):
            review_status = TaskStatusEnum.COMPLETED
            review_progress = f"Approved by {run.approver or 'operator'}."
        elif state == RunState.FAILED and not review_completed and design_completed:
            review_status = TaskStatusEnum.FAILED
            review_blocker = run.failure_reason
        elif state == RunState.CANCELLED and not review_completed and design_completed:
            review_status = TaskStatusEnum.BLOCKED
            review_blocker = run.cancellation_reason

        tasks.append(
            TaskRecord(
                id=f"{run.run_id}-task-review",
                run_id=run.run_id,
                agent_role=AgentRoleEnum.REVIEWER,
                task_type="approval",
                title="Prototype Review & Operator Approval",
                status=review_status,
                started_at=review_started,
                updated_at=review_completed or review_started or run.updated_at,
                completed_at=review_completed,
                progress_details=review_progress,
                blocker=review_blocker,
                attempt_number=run.revision_count + 1,
                related_artifact_ids=[],
            )
        )

        # 4. Builder Task: Code Build
        build_status = TaskStatusEnum.PENDING
        build_started = first_ts("BuildStarted") or review_completed
        build_completed = first_ts("BuildCompleted")
        build_blocker = None
        build_progress = None

        if state in (
            RunState.CREATED,
            RunState.PLANNING,
            RunState.PROTOTYPING,
            RunState.AWAITING_APPROVAL,
        ):
            build_status = TaskStatusEnum.PENDING
            build_started = None
        elif state == RunState.BUILDING:
            build_status = TaskStatusEnum.IN_PROGRESS
            build_progress = (
                "Assembling Astro components and executing isolated sandbox build."
            )
        elif state in (RunState.TESTING, RunState.DEPLOYING, RunState.COMPLETED):
            build_status = TaskStatusEnum.COMPLETED
            build_progress = "Static assets generated and built in sandbox."
        elif state == RunState.FAILED and not build_completed and review_completed:
            build_status = TaskStatusEnum.FAILED
            build_blocker = run.failure_reason
        elif state == RunState.CANCELLED and not build_completed and review_completed:
            build_status = TaskStatusEnum.BLOCKED
            build_blocker = run.cancellation_reason

        tasks.append(
            TaskRecord(
                id=f"{run.run_id}-task-build",
                run_id=run.run_id,
                agent_role=AgentRoleEnum.BUILDER,
                task_type="build",
                title="Codebase Assembly & Sandbox Build",
                status=build_status,
                started_at=build_started,
                updated_at=build_completed or build_started or run.updated_at,
                completed_at=build_completed,
                progress_details=build_progress,
                blocker=build_blocker,
                attempt_number=1,
                related_artifact_ids=build_artifacts,
            )
        )

        # 5. QA Task: Testing
        qa_status = TaskStatusEnum.PENDING
        qa_started = build_completed or first_ts("BuildCompleted")
        qa_completed = first_ts("QAPassed")
        qa_blocker = None
        qa_progress = None

        if state in (
            RunState.CREATED,
            RunState.PLANNING,
            RunState.PROTOTYPING,
            RunState.AWAITING_APPROVAL,
            RunState.BUILDING,
        ):
            qa_status = TaskStatusEnum.PENDING
            qa_started = None
        elif state == RunState.TESTING:
            qa_status = TaskStatusEnum.IN_PROGRESS
            qa_progress = (
                "Running automated browser testing, accessibility, "
                "and SEO verification."
            )
        elif state in (RunState.DEPLOYING, RunState.COMPLETED):
            qa_status = TaskStatusEnum.COMPLETED
            qa_progress = "All QA checks passed successfully."
        elif state == RunState.FAILED and not qa_completed and build_completed:
            qa_status = TaskStatusEnum.FAILED
            qa_blocker = run.failure_reason
        elif state == RunState.CANCELLED and not qa_completed and build_completed:
            qa_status = TaskStatusEnum.BLOCKED
            qa_blocker = run.cancellation_reason

        tasks.append(
            TaskRecord(
                id=f"{run.run_id}-task-qa",
                run_id=run.run_id,
                agent_role=AgentRoleEnum.QA,
                task_type="qa_testing",
                title="Automated QA Verification",
                status=qa_status,
                started_at=qa_started,
                updated_at=qa_completed or qa_started or run.updated_at,
                completed_at=qa_completed,
                progress_details=qa_progress,
                blocker=qa_blocker,
                attempt_number=1,
                related_artifact_ids=qa_artifacts,
            )
        )

        # 6. DevOps Task: Deployment
        deploy_status = TaskStatusEnum.PENDING
        deploy_started = first_ts("DeploymentStarted") or qa_completed
        deploy_completed = first_ts("DeploymentCompleted")
        deploy_blocker = None
        deploy_progress = None

        if state in (
            RunState.CREATED,
            RunState.PLANNING,
            RunState.PROTOTYPING,
            RunState.AWAITING_APPROVAL,
            RunState.BUILDING,
            RunState.TESTING,
        ):
            deploy_status = TaskStatusEnum.PENDING
            deploy_started = None
        elif state == RunState.DEPLOYING:
            deploy_status = TaskStatusEnum.IN_PROGRESS
            deploy_progress = "Publishing production artifacts to edge network."
        elif state == RunState.COMPLETED:
            deploy_status = TaskStatusEnum.COMPLETED
            deploy_progress = "Production site deployed and live."
        elif state == RunState.FAILED and not deploy_completed and qa_completed:
            deploy_status = TaskStatusEnum.FAILED
            deploy_blocker = run.failure_reason
        elif state == RunState.CANCELLED and not deploy_completed and qa_completed:
            deploy_status = TaskStatusEnum.BLOCKED
            deploy_blocker = run.cancellation_reason

        tasks.append(
            TaskRecord(
                id=f"{run.run_id}-task-deploy",
                run_id=run.run_id,
                agent_role=AgentRoleEnum.DEVOPS,
                task_type="deployment",
                title="Edge Deployment & CDN Distribution",
                status=deploy_status,
                started_at=deploy_started,
                updated_at=deploy_completed or deploy_started or run.updated_at,
                completed_at=deploy_completed,
                progress_details=deploy_progress,
                blocker=deploy_blocker,
                attempt_number=1,
                related_artifact_ids=deploy_artifacts,
            )
        )

        # 7. Manager Task: Orchestration
        manager_status = TaskStatusEnum.IN_PROGRESS
        manager_progress = "Supervising multi-agent execution pipeline."
        manager_blocker = None

        if state == RunState.COMPLETED:
            manager_status = TaskStatusEnum.COMPLETED
            manager_progress = "All workflow milestones achieved successfully."
        elif state == RunState.AWAITING_APPROVAL:
            manager_status = TaskStatusEnum.WAITING_APPROVAL
            manager_progress = "Coordinating client approval gate."
        elif state == RunState.FAILED:
            manager_status = TaskStatusEnum.FAILED
            manager_blocker = run.failure_reason
            manager_progress = f"Run failure encountered: {run.failure_reason}"
        elif state == RunState.CANCELLED:
            manager_status = TaskStatusEnum.BLOCKED
            manager_blocker = run.cancellation_reason
            manager_progress = f"Run cancelled: {run.cancellation_reason}"

        tasks.append(
            TaskRecord(
                id=f"{run.run_id}-task-manager",
                run_id=run.run_id,
                agent_role=AgentRoleEnum.MANAGER,
                task_type="orchestration",
                title="Workflow Orchestration & Team Supervision",
                status=manager_status,
                started_at=run.created_at,
                updated_at=run.updated_at,
                completed_at=run.updated_at if state == RunState.COMPLETED else None,
                progress_details=manager_progress,
                blocker=manager_blocker,
                attempt_number=1,
                related_artifact_ids=[],
            )
        )

        return tasks

    def _derive_employees(
        self,
        run: Run,
        tasks: list[TaskRecord],
        events: dict[str, list[EventEnvelope]],
    ) -> list[OfficeEmployeeState]:
        """Derive employee operational states based on task status
        and workflow state.
        """
        task_by_role = {t.agent_role: t for t in tasks}

        def map_status(
            task: TaskRecord | None,
        ) -> tuple[EmployeeStatusEnum, str | None]:
            if task is None:
                return EmployeeStatusEnum.IDLE, None
            if task.status == TaskStatusEnum.IN_PROGRESS:
                return EmployeeStatusEnum.WORKING, task.progress_details
            if task.status == TaskStatusEnum.WAITING_APPROVAL:
                return EmployeeStatusEnum.WAITING_APPROVAL, task.progress_details
            if task.status == TaskStatusEnum.FAILED:
                return EmployeeStatusEnum.FAILED, task.blocker or "Task failed."
            if task.status == TaskStatusEnum.BLOCKED:
                return EmployeeStatusEnum.BLOCKED, task.blocker or "Task blocked."
            if task.status == TaskStatusEnum.COMPLETED:
                if run.state == RunState.COMPLETED:
                    return EmployeeStatusEnum.COMPLETED, "Completed delivery milestone."
                return EmployeeStatusEnum.IDLE, "Standby for subsequent requests."
            return EmployeeStatusEnum.IDLE, "Awaiting assignment."

        # Roster definitions
        roster_meta: list[dict[str, Any]] = [
            {
                "role": AgentRoleEnum.MANAGER,
                "name": "Alex Morgan",
                "title": "AI Agency Manager",
                "avatar": "manager",
                "workstation": WorkstationEnum.MANAGER_DESK,
                "is_logical_role": False,
            },
            {
                "role": AgentRoleEnum.PM,
                "name": "Sofia Chen",
                "title": "Project Manager",
                "avatar": "pm",
                "workstation": WorkstationEnum.PLANNING_DESK,
                "is_logical_role": False,
            },
            {
                "role": AgentRoleEnum.DESIGNER,
                "name": "Liam Vance",
                "title": "UI/UX Designer",
                "avatar": "designer",
                "workstation": WorkstationEnum.DESIGN_STATION,
                "is_logical_role": False,
            },
            {
                "role": AgentRoleEnum.REVIEWER,
                "name": "Operator / Reviewer",
                "title": "Client Review Gate",
                "avatar": "reviewer",
                "workstation": WorkstationEnum.REVIEW_AREA,
                "is_logical_role": True,
            },
            {
                "role": AgentRoleEnum.BUILDER,
                "name": "Marcus Brody",
                "title": "Full-Stack Builder",
                "avatar": "builder",
                "workstation": WorkstationEnum.DEVELOPMENT_STATION,
                "is_logical_role": False,
            },
            {
                "role": AgentRoleEnum.QA,
                "name": "Elena Rostova",
                "title": "QA Engineer",
                "avatar": "qa",
                "workstation": WorkstationEnum.QA_STATION,
                "is_logical_role": False,
            },
            {
                "role": AgentRoleEnum.DEVOPS,
                "name": "DevOps Engineer",
                "title": "Infrastructure & Edge Deploy",
                "avatar": "devops",
                "workstation": WorkstationEnum.OPERATIONS_STATION,
                "is_logical_role": False,
            },
        ]

        employees: list[OfficeEmployeeState] = []
        for meta in roster_meta:
            role = meta["role"]
            task = task_by_role.get(role)
            status, activity = map_status(task)

            # Count completed steps for this role
            completed_steps = (
                1 if task and task.status == TaskStatusEnum.COMPLETED else 0
            )

            employees.append(
                OfficeEmployeeState(
                    role=role,
                    name=meta["name"],
                    title=meta["title"],
                    avatar=meta["avatar"],
                    workstation=meta["workstation"],
                    status=status,
                    active_task_id=task.id
                    if task
                    and task.status
                    in (
                        TaskStatusEnum.IN_PROGRESS,
                        TaskStatusEnum.WAITING_APPROVAL,
                    )
                    else None,
                    current_activity=activity,
                    last_active_at=task.updated_at if task else run.updated_at,
                    is_logical_role=meta["is_logical_role"],
                    completed_steps_count=completed_steps,
                )
            )

        return employees

    def _derive_workstations(
        self,
        run: Run,
        tasks: list[TaskRecord],
    ) -> list[WorkstationState]:
        """Derive workstation status and assigned/queued tasks."""
        task_by_role = {t.agent_role: t for t in tasks}

        workstation_meta: list[dict[str, Any]] = [
            {
                "id": WorkstationEnum.MANAGER_DESK,
                "name": "Manager Desk",
                "description": "Executive oversight and workflow tracking.",
                "role": AgentRoleEnum.MANAGER,
            },
            {
                "id": WorkstationEnum.PLANNING_DESK,
                "name": "Planning Desk",
                "description": "Requirements breakdown and technical specifications.",
                "role": AgentRoleEnum.PM,
            },
            {
                "id": WorkstationEnum.DESIGN_STATION,
                "name": "Design Station",
                "description": "Design tokens, color palettes, and layout synthesis.",
                "role": AgentRoleEnum.DESIGNER,
            },
            {
                "id": WorkstationEnum.REVIEW_AREA,
                "name": "Review Area",
                "description": "Interactive prototype inspection and human approval.",
                "role": AgentRoleEnum.REVIEWER,
            },
            {
                "id": WorkstationEnum.DEVELOPMENT_STATION,
                "name": "Development Station",
                "description": "Component synthesis and Astro template assembly.",
                "role": AgentRoleEnum.BUILDER,
            },
            {
                "id": WorkstationEnum.QA_STATION,
                "name": "QA Station",
                "description": "Automated headless testing, accessibility, and SEO.",
                "role": AgentRoleEnum.QA,
            },
            {
                "id": WorkstationEnum.OPERATIONS_STATION,
                "name": "Operations Station",
                "description": "VCS commits and edge production deployment.",
                "role": AgentRoleEnum.DEVOPS,
            },
        ]

        workstations: list[WorkstationState] = []
        for meta in workstation_meta:
            role = meta["role"]
            task = task_by_role.get(role)

            station_status = "idle"
            active_task_id = None
            queued_ids: list[str] = []

            if task:
                if task.status == TaskStatusEnum.IN_PROGRESS:
                    station_status = "active"
                    active_task_id = task.id
                elif task.status == TaskStatusEnum.WAITING_APPROVAL:
                    station_status = "waiting_approval"
                    active_task_id = task.id
                elif task.status == TaskStatusEnum.COMPLETED:
                    station_status = "completed"
                elif task.status == TaskStatusEnum.FAILED:
                    station_status = "failed"
                elif task.status == TaskStatusEnum.BLOCKED:
                    station_status = "blocked"
                elif task.status == TaskStatusEnum.PENDING:
                    station_status = "idle"
                    queued_ids.append(task.id)

            workstations.append(
                WorkstationState(
                    id=meta["id"],
                    name=meta["name"],
                    description=meta["description"],
                    assigned_role=role,
                    active_task_id=active_task_id,
                    queued_task_ids=queued_ids,
                    status=station_status,
                )
            )

        return workstations
