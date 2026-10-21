# Agency — Multi-Agent AI Software Agency

**Agency** is an autonomous multi-agent AI software agency that converts client briefs into customized, tested, reviewed, and deployed websites through a controlled delivery pipeline.

```text
[ Client Brief ]
       │
       ▼
[ Product Manager Agent ] ──> Structured Product Specification
       │
       ▼
[ Designer Agent ]       ──> Curated Design Tokens & Theme
       │
       ▼
[ Prototype & Approval ] ──> Interactive Preview (Awaiting Operator Approval)
       │
  ( Approved )
       ▼
[ Builder Agent ]        ──> Astro + Tailwind Site Code
       │
       ▼
[ QA Service ]           ──> Automated Playwright, SEO, and Build Checks
       │
       ▼
[ Deployment Adapters ]  ──> GitHub Repo & Cloudflare Pages CDN
       │
       ▼
[ Production Delivery ]  ──> Handover Report & Verified Live URL
```

---

## Key Features

- **Clean Architecture**: Domain layer has zero external dependencies; all external systems are abstracted behind ports (`SandboxPort`, `GitPort`, `DeployPort`, `LLMPort`, `TracingPort`).
- **Stateful Multi-Agent Orchestration**: Stateful pipeline orchestrated via **LangGraph** with durable SQLite checkpointing and explicit pause/resume at the human approval gate.
- **Isolated Docker Sandboxes**: AI-generated code builds and tests inside unprivileged containers (`user=1000:1000`, `network=none`, `cap_drop=ALL`, hard memory/CPU limits) with path traversal guards.
- **SSRF Defense Policy**: All user-supplied links and reference URLs are validated against private, loopback, and cloud metadata IP addresses (`169.254.169.254`, `127.0.0.1`, RFC 1918).
- **FastAPI REST API & SSE**: Streaming domain events via Server-Sent Events with constant-time HMAC API authentication and sliding-window rate limiting.
- **Next.js Operator Dashboard**: Modern dashboard built with Next.js App Router, Tailwind CSS, and shadcn/ui components for real-time monitoring and approval review.
- **Observability & Distributed Tracing**: Distributed spans and token tracking via self-hosted **Langfuse**, with automated credential redaction in structured JSON logs.
- **Repeatable Evaluation Framework**: 12 diverse evaluation briefs measuring build success, QA pass rate, Lighthouse scores, cost, duration, and copy quality.

---

## Architecture and System Layout

```text
agency/
├── AGENTS.md                  # Mandatory engineering and architectural standards
├── README.md                  # System overview, setup, and operations guide
├── docker-compose.yml         # Full-stack production & local compose specification
├── .gitleaks.toml             # Secret scanning configuration
├── backend/                   # Python backend application
│   ├── pyproject.toml         # Python packaging, tool configurations, dependencies
│   ├── Dockerfile             # Multi-stage production container image (Python 3.12-slim)
│   ├── src/agency/
│   │   ├── domain/            # Entities (Run, Brief, Specs), state machine, SSRF policy
│   │   ├── application/       # Use cases, graph nodes, ports, workflow runner supervisor
│   │   ├── infrastructure/    # Sandbox, VCS (GitHub), Deploy (Cloudflare), LLM, Langfuse
│   │   └── interfaces/        # FastAPI REST/SSE routes, CLI tooling
│   ├── tests/                 # Unit, integration, API, and fake test suites
│   └── evals/                 # 12-brief dataset, scorers, runner, Markdown/CSV reports
├── dashboard/                 # Next.js 14 operator dashboard
│   ├── Dockerfile             # Multi-stage production container image (Node.js 20-alpine)
│   ├── src/                   # App Router pages, components, queries, and mutations
│   └── tests/                 # Vitest component and schema tests
├── templates/
│   └── site-astro/            # Astro + Tailwind static website starter template
├── docker/
│   ├── sandbox/               # Isolated code execution container (agency-sandbox:latest)
│   └── compose/               # Langfuse self-hosting compose stack
└── docs/
    ├── architecture.md        # Comprehensive architecture diagram (Mermaid)
    ├── security.md            # Threat model, attack surfaces, and security controls
    ├── runbook.md             # Operational procedures, recovery, and diagnostics
    ├── demo.md                # Repeatable demo script without external credentials
    ├── production-readiness.md# Evidence-based production readiness assessment
    ├── adr/                   # Architecture Decision Records (ADR 0001 - 0009)
    └── openapi.json           # Exported OpenAPI 3.1 specification
```

---

## Quick Start (Local Full Stack)

### Prerequisites
- **Python**: `>=3.12,<3.13`
- **Node.js**: `>=20` and `pnpm >=9`
- **Docker**: Docker Engine and Docker Compose

### 1. Launch with Docker Compose
The easiest way to run the complete stack (Backend, Dashboard, and Langfuse):
```bash
# Copy environment configuration
cp .env.example .env

# Start all containers in the background
docker compose up -d

# Verify all services are healthy
docker compose ps
```

Access services:
- **Operator Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI REST API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Langfuse UI**: [http://localhost:3001](http://localhost:3001)

### 2. Manual Development Setup
```bash
# 1. Setup Python virtual environment
make install-dev
source .venv/bin/activate

# 2. Start FastAPI API server
PYTHONPATH=backend/src:backend uvicorn agency.interfaces.api.app:create_app --factory --port 8000 --reload

# 3. Start Next.js Dashboard (in a separate terminal)
cd dashboard
pnpm install
pnpm dev
```

---

## Quality, Testing, and Verification Commands

Execute quality checks directly from the repository root:

```bash
# Run all Python backend checks (Ruff lint, formatting, mypy strict, pytest)
make check

# Run pytest suite
.venv/bin/pytest backend/tests

# Run Ruff linting and formatting
.venv/bin/ruff check backend
.venv/bin/ruff format --check backend

# Run strict type checking (0 errors across 222 source files)
cd backend && ../.venv/bin/mypy src evals tests

# Run dashboard linting, type checks, and tests
cd dashboard && pnpm lint && pnpm typecheck && pnpm test
```

---

## Evaluation Framework

Agency includes a deterministic evaluation suite testing 12 representative client archetypes (developer, designer, photographer, small business, consultant, etc.):

```bash
# Run all 12 briefs in zero-cost fake mode (no API keys required)
PYTHONPATH=backend/src:backend python -m agency.interfaces.cli.main eval run --mode fake

# Run a single brief
PYTHONPATH=backend/src:backend python -m agency.interfaces.cli.main eval run --mode fake --brief developer

# Inspect generated evaluation report
PYTHONPATH=backend/src:backend python -m agency.interfaces.cli.main eval report --run-id <run-id>
```
Evaluation reports are saved to `runs/evals/<run-id>/report.md` and `results.csv`.

---

## Operational Maintenance

### Purge Orphaned Sandbox Containers & Workspaces
```bash
# Simulation dry-run
PYTHONPATH=backend/src:backend python -m agency.interfaces.cli.main cleanup --dry-run --retention-hours 24

# Active purge
PYTHONPATH=backend/src:backend python -m agency.interfaces.cli.main cleanup --retention-hours 24
```

---

## Security and Documentation

- [Architecture Diagram (Mermaid)](docs/architecture.md)
- [Security Threat Model & Defenses](docs/security.md)
- [Operations Runbook](docs/runbook.md)
- [Demo Script](docs/demo.md)
- [Production-Readiness Assessment](docs/production-readiness.md)
- [Architecture Decision Records (ADRs)](docs/adr/)
