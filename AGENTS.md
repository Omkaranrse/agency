# AGENTS.md — Mandatory Engineering Rules

This document establishes the mandatory engineering rules, architectural constraints, and operational guidelines for all developers and AI agents working on the **Agency** project.

---

## 1. Architecture

- **Clean Architecture**: Adhere strictly to Clean Architecture principles across the entire codebase.
- **Domain Independence**: The Domain layer (`backend/src/agency/domain/`) must never depend on frameworks, libraries, databases, or infrastructure implementations.
- **Application Layer**: The Application layer (`backend/src/agency/application/`) contains business use cases and application-owned ports (abstract interfaces).
- **Infrastructure Layer**: The Infrastructure layer (`backend/src/agency/infrastructure/`) implements ports defined by the application layer (e.g., LLM providers, sandbox runtimes, VCS, persistence, observability).
- **Inward Dependency Flow**: Dependencies must always point inward toward the core domain (`Domain <- Application <- Infrastructure / Interfaces`).
- **Separation of Concerns**: API routes (`interfaces/api/`) and LangGraph nodes (`application/graph/`) must delegate orchestration to use cases rather than embedding business logic.

---

## 2. Python Standards

- **Python Version**: Target Python 3.12 (`>=3.12,<3.13`).
- **Static Typing**: Comprehensive type annotations are required for all function arguments, return values, and class attributes.
- **Strict Mode**: Enforce `mypy` strict mode without exceptions or untyped defs.
- **Linting & Formatting**: Use Ruff for linting and formatting with an 88-character line length limit.
- **Testing Framework**: Use `pytest` for all test execution and discovery.
- **Pre-commit**: Use `pre-commit` hooks for linting, formatting, whitespace, and secret hygiene checks.

---

## 3. Testing Discipline

- **Unit Test Coverage**: Every public function introduced in future implementation phases must have corresponding unit tests.
- **Isolation**: Unit tests must never make network calls, access live databases, or spawn external services.
- **Test Fakes**: Use in-memory fakes and test doubles for external integrations and ports rather than complex mock monkeypatching where feasible.
- **Test Categorization**: Maintain clear separation between test tiers:
  - `backend/tests/unit/`: Fast, isolated tests of domain logic and use cases.
  - `backend/tests/integration/`: Component interactions, database queries, and port implementations.
  - `backend/tests/e2e/`: Full end-to-end workflows.

---

## 4. Security & Safety

- **No Secrets**: Never commit or log secrets, tokens, credentials, or private keys in source code, prompts, test fixtures, or configuration files.
- **Configuration**: Use environment variables for runtime configuration (`.env` loaded via validated configuration models).
- **Sandbox Isolation**: Generated code and agent-executed commands must run only within an isolated sandbox environment.
- **Resource Limits**: Enforce strict execution timeouts and bounded retry limits on all agentic and sandbox operations.
- **Human Approval**: Require explicit human approval before executing production deployments or destructive operations.

---

## 5. AI & Workflow Architecture

- **Orchestration**: Use LangGraph for explicit, stateful, and observable multi-agent workflow orchestration.
- **Structured Contracts**: Exchange validated Pydantic models between agent stages; never pass unvalidated free-form text dictionaries where structured data is expected.
- **Ports & Adapters**: Route all external operations (code execution, Git commands, cloud deployments) through defined ports.
- **Provider Portability**: Keep LLM model providers swappable through abstracted interfaces to avoid lock-in.

---

## 6. Frontend Specifications

- **Framework**: Next.js App Router with TypeScript strict mode.
- **Component & Styling System**: Tailwind CSS and shadcn/ui.
- **Typography**: Poppins font only.
- **Aesthetic Constraints**: Clean, professional, and accessible. No gradients, neon colors, glassmorphism, or emoji icons.

---

## 7. Delivery & Collaboration

- **Atomic Increments**: Make small, focused, verifiable changes.
- **Preserve User Work**: Never delete, overwrite, reset, or reorganize existing work without explicit authorization.
- **Git Safety**: Never commit or push without explicit authorization from the user.
- **Transparent Reporting**: Always report changed files, executed commands, and actual test results.
- **Clarification**: Ask one focused question if a genuine blocking ambiguity exists.
