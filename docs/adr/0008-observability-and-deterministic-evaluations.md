# ADR 0008: Self-Hosted Observability and Deterministic Evaluations

## Status
Accepted

## Context
Understanding agent decisions, token consumption, QA quality, and pipeline reliability requires tracing and regression testing. Relying on paid SaaS observability services poses privacy risks and credential barriers in CI.

## Decision
1. **Self-Hosted Langfuse**: Integrated via Docker Compose using pinned images (`langfuse:2.100.0`, `postgres:16-alpine`, `redis:7-alpine`).
2. **Application-Owned Tracing Port**: Tracing sits behind `TracingPort`. The pipeline continues normally if Langfuse is unavailable (`NoOpTracingPort`).
3. **Structured Correlated Logging**: Centralized JSON logging on stdout binding `run_id`, `trace_id`, `span_id`, and `node_name`, with automated secret scrubbing.
4. **12-Brief Evaluation Framework**: `backend/evals/` contains 12 validated briefs across diverse client archetypes, measuring build reliability, QA pass rate, Lighthouse scores, cost, duration, and copy quality using deterministic rubrics.
5. **Zero-Cost CI**: Pull requests run evaluations strictly in `FakeLLM` mode, producing Markdown and CSV reports without external network or paid API keys.

## Consequences
- Full observability available locally with zero vendor cost.
- Regression testing runs automatically in pull request CI.
- Real LLM evaluations are opt-in and budget-capped.
