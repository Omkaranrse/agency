# ADR 0005: Explicit Human Approval Gate and Revision Semantics

## Status
Accepted

## Context
Deploying an AI-generated website directly to production without human review carries significant brand, security, and quality risks. Operators must be able to review static prototypes, request specific revisions, or approve the design before production promotion occurs.

## Decision
1. **Mandatory Approval Gate**: Execution automatically pauses at `RunState.AWAITING_APPROVAL`. The workflow cannot proceed to production build or deployment without an explicit human approval decision.
2. **Revision Binding**: Approvals and revision requests must specify the exact `revision` number being reviewed. Requests targeting stale revisions are rejected with `ConflictError` (HTTP 409).
3. **Idempotency**: Submissions accept an `idempotency_key` ensuring duplicate clicks in the UI do not spawn conflicting pipeline branches.
4. **Finite Revisions**: Workflows bound revision loops to protect resources.

## Consequences
- No site can be deployed without explicit human authorization.
- Revisions are deterministic and traceable.
- Operators can request targeted modifications with feedback that directly feeds back into PM, Designer, and Builder agents.
