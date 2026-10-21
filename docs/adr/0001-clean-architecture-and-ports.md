# ADR 0001: Clean Architecture and Inward Dependency Flow

## Status
Accepted

## Context
The Agency system converts client briefs into production-grade websites through a complex multi-agent pipeline involving LLMs, dockerized build sandboxes, Git operations, and deployment networks. Without strict architectural boundaries, business rules become tightly coupled to specific LLM vendor SDKs, Docker APIs, and cloud hosting providers.

## Decision
We adopted Clean Architecture across the entire Python backend (`src/agency/`):
1. **Domain Layer (`domain/`)**: Completely independent of external frameworks, libraries, databases, or cloud SDKs. Contains immutable entities (`Brief`, `Run`, `ProductSpec`, `DesignTokens`, `PageContent`), state machines, and domain events.
2. **Application Layer (`application/`)**: Encapsulates workflow use cases, multi-agent orchestration, and defines application-owned ports (`SandboxPort`, `GitPort`, `DeployPort`, `RunRepositoryPort`, `EventBusPort`, `TracingPort`).
3. **Infrastructure Layer (`infrastructure/`)**: Implements ports defined by the application layer (Docker, GitHub, Cloudflare Pages, Gemini, Langfuse, SQLite).
4. **Interfaces Layer (`interfaces/`)**: Provides external access via FastAPI REST/SSE endpoints and Typer/argparse CLI.

Dependencies always point strictly inward: `Domain <- Application <- Infrastructure / Interfaces`.

## Consequences
- Domain logic is 100% unit-testable without Docker daemons, networks, or cloud credentials.
- Infrastructure adapters can be swapped or faked during testing and evaluations.
- Prevents framework leaks and ensures long-term maintainability.
