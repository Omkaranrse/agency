# ADR 0002: LangGraph Stateful Multi-Agent Workflow and Durable Checkpointing

## Status
Accepted

## Context
Multi-agent website generation requires explicit, stateful, and observable pipeline execution across planning, designing, building, QA auditing, human approval, repair iterations, and deployment. The execution must be pauseable, resumable, and auditable across process restarts.

## Decision
We chose **LangGraph** (`langgraph>=0.2.0`) as the orchestration framework, backed by SQLite checkpointers (`SqliteSaver` / `AsyncSqliteSaver`).
- Workflow state is represented as a structured TypedDict (`WorkflowState`) with validated Pydantic models.
- Execution progresses deterministically through 13 discrete nodes.
- Human approval is handled using LangGraph's native `interrupt()` mechanism at the `human_approval` node.
- Durable checkpoints preserve full execution state at every node boundary.

## Alternatives Considered
- *Custom loop / Celery state machine*: Rejected due to lack of graph visualization, high maintenance cost, and lack of native human-in-the-loop interruption primitives.
- *Temporal / Cadence*: Powerful, but introduces significant infrastructure overhead and operational complexity unsuitable for lightweight local developer workflows.

## Consequences
- Workflows survive application restarts; approvals resume from exact state snapshots.
- Repair iterations are explicitly bounded (max 3 QA repair attempts).
- State transitions are transparent, inspectable, and auditable.
