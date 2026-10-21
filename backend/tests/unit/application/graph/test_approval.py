"""Unit tests for human approval decisions and freshness validation."""

import pytest
from pydantic import ValidationError

from agency.application.graph.approval import (
    ApprovalDecision,
    ApprovalDecisionType,
    validate_approval_decision,
)
from agency.application.graph.errors import StaleApprovalError


def test_approval_decision_approve() -> None:
    """Approval decision accepts valid approve payload."""
    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
        approver="client-alice",
    )
    assert decision.decision == ApprovalDecisionType.APPROVE
    assert decision.revision == 0
    assert decision.approver == "client-alice"


def test_approval_decision_revise_requires_comment() -> None:
    """Revision decision requires a non-empty comment."""
    with pytest.raises(ValidationError, match="Revision decisions require a non-empty"):
        ApprovalDecision(
            decision=ApprovalDecisionType.REVISE,
            revision=1,
            comment="",
        )

    decision = ApprovalDecision(
        decision=ApprovalDecisionType.REVISE,
        revision=1,
        comment="Increase hero headline contrast.",
    )
    assert decision.comment == "Increase hero headline contrast."


def test_approval_decision_reject() -> None:
    """Reject decision allows optional comment."""
    decision = ApprovalDecision(
        decision=ApprovalDecisionType.REJECT,
        revision=0,
        comment="Client cancelled budget.",
    )
    assert decision.decision == ApprovalDecisionType.REJECT


def test_validate_approval_decision_freshness() -> None:
    """validate_approval_decision passes when revision matches current revision."""
    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=2,
    )
    validate_approval_decision(decision, current_revision=2)


def test_validate_approval_decision_stale_rejected() -> None:
    """validate_approval_decision raises StaleApprovalError when revisions mismatch."""
    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=1,
    )
    with pytest.raises(StaleApprovalError, match="Stale approval decision"):
        validate_approval_decision(decision, current_revision=2)
