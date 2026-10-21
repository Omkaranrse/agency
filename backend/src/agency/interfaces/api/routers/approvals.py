"""API route handlers for human approval, revision requests, and cancellation."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.application.graph.errors import StaleApprovalError
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.services.workflow_runner import WorkflowRunner
from agency.application.use_cases.cancel_run import CancelRun, CancelRunCommand
from agency.application.use_cases.get_run import GetRun
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.errors import InvalidApprovalError, InvalidRevisionRequestError
from agency.interfaces.api.dependencies import (
    get_api_key,
    get_event_bus,
    get_run_repository,
    get_workflow_runner,
    limit_write_ops,
)
from agency.interfaces.api.schemas.approvals import (
    ApproveRunRequest,
    ApproveRunResponse,
    CancelRunRequest,
    CancelRunResponse,
    ReviseRunRequest,
    ReviseRunResponse,
)

router = APIRouter(prefix="/runs", tags=["Approvals"])


@router.post(
    "/{run_id}/approve",
    status_code=status.HTTP_200_OK,
    response_model=ApproveRunResponse,
    dependencies=[Depends(get_api_key), Depends(limit_write_ops)],
)
async def approve_run(
    run_id: str,
    request: ApproveRunRequest,
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    runner: Annotated[WorkflowRunner, Depends(get_workflow_runner)],
) -> ApproveRunResponse:
    """Submit explicit human approval to resume compilation and deployment."""
    use_case = GetRun(repository=repository)
    run = use_case.execute(run_id=run_id)

    if run.state != RunState.AWAITING_APPROVAL:
        raise InvalidApprovalError(
            run_id=run_id,
            reason=(
                f"Cannot approve run in state '{run.state.value}'. "
                "Must be in 'AWAITING_APPROVAL'."
            ),
        )

    if request.revision != run.revision_count:
        raise StaleApprovalError(
            f"Approval revision {request.revision} is stale. "
            f"Current preview revision is {run.revision_count}."
        )

    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=request.revision,
        approver=request.approver,
    )

    runner.submit_approval(
        run_id=run_id,
        decision=decision,
        idempotency_key=request.idempotency_key,
    )

    return ApproveRunResponse(
        run_id=run_id,
        status="approved",
        decision="approved",
        revision=request.revision,
    )


@router.post(
    "/{run_id}/revise",
    status_code=status.HTTP_200_OK,
    response_model=ReviseRunResponse,
    dependencies=[Depends(get_api_key), Depends(limit_write_ops)],
)
async def revise_run(
    run_id: str,
    request: ReviseRunRequest,
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    runner: Annotated[WorkflowRunner, Depends(get_workflow_runner)],
) -> ReviseRunResponse:
    """Reject current prototype and request design/copy revisions."""
    use_case = GetRun(repository=repository)
    run = use_case.execute(run_id=run_id)

    if run.state != RunState.AWAITING_APPROVAL:
        raise InvalidRevisionRequestError(
            run_id=run_id,
            reason=(
                f"Cannot request revision for run in state '{run.state.value}'. "
                "Must be in 'AWAITING_APPROVAL'."
            ),
        )

    if request.revision != run.revision_count:
        raise StaleApprovalError(
            f"Revision request revision {request.revision} does not match "
            f"current preview revision {run.revision_count}."
        )

    clean_comment = request.comment.strip()

    decision = ApprovalDecision(
        decision=ApprovalDecisionType.REVISE,
        revision=request.revision,
        comment=clean_comment,
    )

    runner.submit_approval(
        run_id=run_id,
        decision=decision,
        idempotency_key=request.idempotency_key,
    )

    return ReviseRunResponse(
        run_id=run_id,
        status="revised",
        decision="revised",
        new_revision=run.revision_count + 1,
        comment=clean_comment,
    )


@router.post(
    "/{run_id}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=CancelRunResponse,
    dependencies=[Depends(get_api_key), Depends(limit_write_ops)],
)
async def cancel_run(
    run_id: str,
    request: CancelRunRequest,
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    event_bus: Annotated[EventBusPort, Depends(get_event_bus)],
    runner: Annotated[WorkflowRunner, Depends(get_workflow_runner)],
) -> CancelRunResponse:
    """Request immediate cancellation of an active workflow."""
    use_case = GetRun(repository=repository)
    run = use_case.execute(run_id=run_id)

    # Idempotent response if already in a terminal state
    if run.state in Run.TERMINAL_STATES:
        return CancelRunResponse(
            run_id=run_id,
            status=run.state.value,
            reason=run.failure_reason or "Run already finished",
        )

    clean_reason = request.reason.strip() if request.reason else "Cancelled by user"
    cancel_cmd = CancelRunCommand(run_id=run_id, reason=clean_reason)
    cancel_use_case = CancelRun(repository=repository, event_bus=event_bus)
    cancel_use_case.execute(cancel_cmd)

    try:
        runner.cancel_run(run_id=run_id, reason=clean_reason)
    except Exception:
        pass

    return CancelRunResponse(
        run_id=run_id,
        status="cancelled",
        reason=clean_reason,
    )
