"""Domain exceptions hierarchy for Agency."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agency.domain.enums import RunState


class DomainError(Exception):
    """Base class for all domain-level exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidStateTransitionError(DomainError):
    """Raised when an illegal state transition is requested."""

    def __init__(
        self,
        from_state: "RunState",
        to_state: "RunState",
        message: str | None = None,
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        detailed_message = (
            message
            or f"Cannot transition Run from '{from_state.value}' to '{to_state.value}'."
        )
        super().__init__(detailed_message)


class ApprovalRequiredError(DomainError):
    """Raised when an operation requires ungranted prototype approval."""

    def __init__(
        self,
        run_id: str,
        state: "RunState",
        message: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.state = state
        detailed_message = message or (
            f"Run '{run_id}' in state '{state.value}' requires explicit "
            "prototype approval before proceeding."
        )
        super().__init__(detailed_message)


class InvalidApprovalError(DomainError):
    """Raised when an approval decision is invalid or violates invariants."""

    def __init__(
        self,
        run_id: str,
        reason: str,
        message: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.reason = reason
        detailed_message = message or f"Invalid approval for Run '{run_id}': {reason}"
        super().__init__(detailed_message)


class InvalidRevisionRequestError(DomainError):
    """Raised when a revision request violates lifecycle invariants or limits."""

    def __init__(
        self,
        run_id: str,
        reason: str,
        message: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.reason = reason
        detailed_message = (
            message or f"Invalid revision request for Run '{run_id}': {reason}"
        )
        super().__init__(detailed_message)


class InvalidTerminalStateOperationError(DomainError):
    """Raised when an operation is attempted on a run in a terminal state."""

    def __init__(
        self,
        state: "RunState",
        operation: str,
        message: str | None = None,
    ) -> None:
        self.state = state
        self.operation = operation
        detailed_message = message or (
            f"Cannot perform operation '{operation}' on Run in terminal "
            f"state '{state.value}'."
        )
        super().__init__(detailed_message)


class DomainInvariantError(DomainError):
    """Raised when a general domain invariant is violated."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
