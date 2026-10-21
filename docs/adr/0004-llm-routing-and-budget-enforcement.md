# ADR 0004: Swappable LLM Routing and Token Budget Enforcement

## Status
Accepted

## Context
Multi-agent systems can easily incur unexpected cloud costs and model vendor lock-in if agents directly invoke third-party proprietary APIs. Additionally, development and CI must operate completely free of paid credentials.

## Decision
We implemented `LLMPort` and a model router supporting:
1. `GeminiLLM`: Google Gemini 1.5 Pro and Flash adapters.
2. `OllamaLLM`: Local open-weights model adapter.
3. `FakeLLM`: Deterministic in-memory fake with pre-recorded golden outputs for tests and evaluations.
4. `TokenBudgetTracker`: Tracks input tokens, output tokens, cached tokens, and provider cost, capping each run at a configurable limit (default $5.00).

## Consequences
- The system functions with zero network credentials during ordinary test runs and CI evaluations.
- Production costs are strictly bounded and transparently reported.
- Swapping LLM vendors requires implementing only the `LLMPort` interface.
