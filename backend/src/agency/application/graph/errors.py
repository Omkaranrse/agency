"""Graph-specific exceptions for LangGraph workflow execution."""

from agency.application.errors import ApplicationError


class GraphExecutionError(ApplicationError):
    """Base exception for all workflow graph orchestration errors."""


class GraphStateError(GraphExecutionError):
    """Raised when graph state is invalid or missing required stage fields."""


class ApprovalValidationError(GraphExecutionError):
    """Raised when an approval decision payload violates domain or policy rules."""


class StaleApprovalError(ApprovalValidationError):
    """Raised when approval references an outdated specification revision."""


class ClarificationRequiredError(GraphExecutionError):
    """Raised when a stage requires client clarification before proceeding."""


class RepairLimitExceededError(GraphExecutionError):
    """Raised when QA repair retries exceed the maximum bounded cycles."""


class WorkflowCancelledError(GraphExecutionError):
    """Raised when an operation cannot proceed because the run was cancelled."""
