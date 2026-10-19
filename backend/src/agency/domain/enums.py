"""Domain enums for the Agency workflow."""

from enum import StrEnum


class RunState(StrEnum):
    """The explicit states representing a Run lifecycle in the state machine."""

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    PROTOTYPING = "PROTOTYPING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    DEPLOYING = "DEPLOYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
