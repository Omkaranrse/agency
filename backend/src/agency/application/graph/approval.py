"""Human approval contracts and validation logic for workflow gates."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agency.application.graph.errors import StaleApprovalError


class ApprovalDecisionType(StrEnum):
    """Permitted human approval gate decisions."""

    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


class ApprovalDecision(BaseModel):
    """Structured decision submitted at the human approval gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision: ApprovalDecisionType
    revision: int = Field(ge=0, description="The revision number being evaluated.")
    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Mandatory for revisions; optional for approvals or rejections.",
    )
    approver: str = Field(
        default="client",
        min_length=1,
        max_length=100,
        description="Identifier of the human authority making the decision.",
    )

    @field_validator("approver", mode="before")
    @classmethod
    def _strip_approver(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Approver cannot be empty or whitespace.")
            return stripped
        return value

    @field_validator("comment", mode="before")
    @classmethod
    def _strip_comment(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value

    @model_validator(mode="after")
    def _validate_revision_requires_comment(self) -> "ApprovalDecision":
        if self.decision == ApprovalDecisionType.REVISE:
            if not self.comment or not self.comment.strip():
                raise ValueError(
                    "Revision decisions require a non-empty descriptive comment."
                )
        return self


def validate_approval_decision(
    decision: ApprovalDecision, current_revision: int
) -> None:
    """Validate approval decision freshness against the current workflow revision."""
    if decision.revision != current_revision:
        raise StaleApprovalError(
            f"Stale approval decision: submitted revision {decision.revision} does not "
            f"match current active revision {current_revision}."
        )
