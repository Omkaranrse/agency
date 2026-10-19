# Agency

**Agency** is an AI-powered software agency platform designed to transform client briefs into production-grade, full-stack web applications using a controlled, multi-agent workflow.

> [!NOTE]
> **Phase 0 Status**: The repository is currently in its foundational setup phase. The core directory structure, architectural guidelines, quality tooling, and smoke test suite are established. The AI agents, application APIs, business entities, database repositories, deployment integrations, and dashboard UI have **not yet been implemented**.

---

## Architecture Boundaries

Agency follows **Clean Architecture** to maintain strict decoupling between domain logic, orchestration workflows, and external adapters:

- **Domain (`backend/src/agency/domain/`)**: Pure business logic, core entities, domain events, and domain exceptions. Completely independent of frameworks, databases, and external libraries.
- **Application (`backend/src/agency/application/`)**: Use cases, state orchestration (LangGraph state graphs), and application-defined ports (interfaces).
- **Infrastructure (`backend/src/agency/infrastructure/`)**: Concrete implementations of application ports, including LLM provider integrations, code execution sandboxes, version control systems (VCS), deployment adapters, persistence, and telemetry/observability.
- **Interfaces (`backend/src/agency/interfaces/`)**: Inbound entrypoints such as REST/WebSocket APIs (FastAPI) and CLI tooling.
- **Dependency Inversion**: Dependencies always flow inward toward the domain (`Domain <- Application <- Infrastructure / Interfaces`). API routes and LangGraph nodes delegate execution to use cases rather than embedding business logic.

---

## Directory Layout

```text
agency/
├── AGENTS.md                  # Mandatory engineering rules and architectural standards
├── README.md                  # Project overview, layout, and setup documentation
├── .gitignore                 # Exclusions for Python, Node, OS, logs, and secrets
├── .env.example               # Safe environment variable template (no credentials)
├── .editorconfig              # Consistent cross-editor whitespace and formatting
├── .pre-commit-config.yaml    # Git hooks for linting, formatting, and secret checks
├── Makefile                   # Developer workflows executed from repository root
├── backend/                   # Python backend package root
│   ├── pyproject.toml         # Build backend, dependencies, and tool configs
│   ├── src/
│   │   └── agency/            # Core Python package root
│   │       ├── __init__.py    # Exposes package version (0.1.0)
│   │       ├── domain/        # Entities, events, and domain errors
│   │       ├── application/   # Use cases, ports, and LangGraph workflow graphs
│   │       ├── infrastructure/# LLM, sandbox, VCS, deploy, persistence, observability
│   │       ├── interfaces/    # Inbound entrypoints (FastAPI, CLI)
│   │       └── config/        # Environment-based configuration models
│   ├── tests/
│   │   ├── unit/              # Isolated, fast unit tests (includes test_smoke.py)
│   │   ├── integration/       # Component and adapter integration tests
│   │   ├── e2e/               # Full system end-to-end test suites
│   │   └── fakes/             # In-memory test doubles for external ports
│   └── evals/                 # Benchmark evals for LLM prompts and agent outputs
├── templates/
│   └── site-astro/            # Astro full-stack application template
├── dashboard/                 # Next.js App Router operator and client UI
├── docker/
│   ├── sandbox/               # Isolated code execution container definitions
│   └── compose/               # Local multi-service compose specifications
└── docs/
    ├── architecture/          # Architecture design records and system diagrams
    ├── adr/                   # Architecture Decision Records
    └── runbooks/              # Operational and debugging runbooks
```

---

## Prerequisites

- **Python**: `3.12` (`>=3.12,<3.13` required)
- **Make**: Standard POSIX `make`
- **Git**: `>=2.30`

---

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url> agency
   cd agency
   ```

2. **Initialize Environment & Dependencies**:
   ```bash
   make install-dev
   ```
   This will:
   - Create a local Python 3.12 virtual environment at `.venv/`.
   - Upgrade `pip` to latest.
   - Install the `agency` backend package in editable mode (`-e`) along with all developer tooling (`pytest`, `ruff`, `mypy`, `black`, `pre-commit`).

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Adjust local values in .env as needed
   ```

4. **Install Pre-commit Git Hooks**:
   ```bash
   make pre-commit-install
   ```

---

## Verification & Quality Commands

All commands can be executed directly from the repository root:

- **Run all checks** (linting, type checking, unit tests):
  ```bash
  make check
  ```
- **Run unit tests**:
  ```bash
  make test
  ```
- **Run lint checks** (Ruff):
  ```bash
  make lint
  ```
- **Format code** (Ruff):
  ```bash
  make format
  ```
- **Run static type checking** (mypy strict mode):
  ```bash
  make typecheck
  ```
