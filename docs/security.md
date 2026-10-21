# Threat Model and Security Architecture — Agency

This document defines the comprehensive threat model, trust boundaries, attack surfaces, security controls, residual risks, and mitigation strategies for **Agency**.

---

## 1. System Assets and Trust Boundaries

### Critical Assets
1. **Host Environment & Infrastructure**: Docker daemon, host filesystem, server secrets, and private networks.
2. **Provider Credentials**: GitHub tokens, Cloudflare API keys, Gemini/OpenAI API keys, and Langfuse credentials.
3. **Workflow Integrity & Approval Gates**: State machine transitions, human approval decisions, revision history, and deployment authorization.
4. **Client Data & IP**: Client brief contents, brand guidelines, private contact details, and proprietary business logic.
5. **Generated Source Code & Production Deployments**: Web applications, git repositories, preview sites, and live production endpoints.

### Trust Boundaries
- **Untrusted External Boundary**: Client input briefs, reference URLs, revision comments, and external web content fetched during QA.
- **Semi-Trusted Operator Boundary**: Next.js dashboard UI, authenticated operator requests carrying API keys.
- **Model Trust Boundary**: External LLM providers (Gemini, Ollama, OpenAI). Model outputs are treated as untrusted text until validated by strict Pydantic schemas.
- **Isolated Execution Boundary**: Docker sandbox containers where AI-generated web applications are built, bundled, and tested.
- **Trusted Core**: FastAPI REST API, LangGraph state machine, application use cases, and SQLite/PostgreSQL durable persistence.

---

## 2. Threat Scenarios, Controls, and Mitigations

### A. Prompt Injection
- **Threat Scenario**: Malicious instructions embedded in client briefs, reference URLs, or QA logs attempting to bypass human approval, extract server secrets, or instruct builder agents to emit malicious scripts.
- **Risk Level**: **HIGH**
- **Existing Controls**:
  - Strict separation of system prompts from untrusted client content using structured input templating.
  - LLM outputs are validated against immutable, strict Pydantic models (`ProductSpec`, `DesignTokens`, `PageContent`); free-form dicts are forbidden.
  - Human approval gate enforced at the application state machine level (`RunState.AWAITING_APPROVAL`), completely independent of LLM prompts.
  - LLMs cannot trigger deployments or modify workflow authorization state directly.
  - Token budgets and bounded tool calls prevent runaway instruction loops.
- **Verification Method**: Malicious injection test suites in `backend/tests/unit/domain/test_brief.py` and evaluation suites.
- **Residual Risk**: LLMs may generate sub-optimal or off-brand copy despite schema compliance.
- **Follow-up Action**: Regularly update prompt fences and maintain human-in-the-loop review for all revisions.

---

### B. Sandbox Escape & Container Isolation
- **Threat Scenario**: AI-generated code in `package.json` install hooks or Astro build scripts executes arbitrary shell commands, accesses the host filesystem, mounts the Docker socket, or attempts container privilege escalation.
- **Risk Level**: **CRITICAL**
- **Existing Controls**:
  - Unprivileged user execution (`USER 1000:1000` or `USER sandbox`).
  - Container capabilities dropped: `cap_drop=["ALL"]`.
  - Security options: `no-new-privileges:true`.
  - Docker socket (`/var/run/docker.sock`) is **never** mounted into sandbox containers.
  - Read/write mount restricted exclusively to the allocated ephemeral workspace (`/workspace`).
  - Network isolation: `network_mode="none"` during code execution.
  - Strict resource quotas: CPU (`1.0 CPU`), Memory (`512MB`), PIDs (`100`), Command timeout (`60s`), and Output limit (`1MB`).
  - Automatic teardown upon completion, failure, cancellation, and via maintenance cleanup (`CleanupService`).
- **Verification Method**: `DockerSandbox` configuration tests in `backend/tests/unit/infrastructure/` and integration tests.
- **Residual Risk**: Kernel-level container escape 0-days in Linux/Docker runtimes.
- **Follow-up Action**: Keep host Linux kernel and Docker engine patched; consider gVisor/Kata microVM runtimes for multi-tenant SaaS environments.

---

### C. Secret Leakage
- **Threat Scenario**: API keys, deployment tokens, or database credentials leaked in git commits, stdout logs, Langfuse traces, or browser-bundled JavaScript assets.
- **Risk Level**: **CRITICAL**
- **Existing Controls**:
  - Environment-backed configuration via Pydantic `BaseSettings`. No credentials hardcoded in repository.
  - Centralized structured JSON logging with automated redaction (`redact_sensitive_text`) scrubbing Bearer tokens, API keys, passwords, and authorization headers.
  - Langfuse tracing adapter explicitly sanitizes metadata before submission.
  - Next.js dashboard exposes only allowlisted public configuration (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_API_KEY`); backend tokens (GitHub, Cloudflare) never enter the frontend bundle.
  - Automated Gitleaks secret scanning configured in CI (`.gitleaks.toml`).
  - Unit tests verifying secret redaction in `test_structured_logging.py`.
- **Verification Method**: `pytest backend/tests/unit/infrastructure/observability/test_structured_logging.py` and Gitleaks workflow.
- **Residual Risk**: Secrets inadvertently pasted by operators into brief content notes.
- **Follow-up Action**: Run outbound regex filtering on brief content notes before saving.

---

### D. Server-Side Request Forgery (SSRF) and Unsafe URLs
- **Threat Scenario**: Brief links or smoke-test targets point to internal endpoints (`http://169.254.169.254`, `http://localhost:8000`, `http://10.0.0.1`), leaking cloud metadata or accessing internal microservices.
- **Risk Level**: **HIGH**
- **Existing Controls**:
  - Domain URL security validator (`validate_safe_url`) enforced directly on all `Brief.links`.
  - Blocks RFC 1918 private IPv4 addresses (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), CGNAT (`100.64.0.0/10`), loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`, `fe80::/10`), multicast, and unspecified (`0.0.0.0`).
  - Blocks dangerous schemes: only `http` and `https` permitted (`file://`, `gopher://`, `ftp://` rejected).
  - Blocks cloud metadata hostnames (`metadata.google.internal`, `instance-data`) and local domain suffixes (`.local`, `.internal`, `.localhost`).
  - User authentication credentials in URLs (`user:pass@host`) strictly rejected.
  - Optional DNS resolution checks against rebinding.
- **Verification Method**: `pytest backend/tests/unit/domain/test_url_policy.py`.
- **Residual Risk**: Dynamic DNS rebinding if DNS resolution changes between validation and connection.
- **Follow-up Action**: Pin outbound HTTP client connections to pre-validated IP sockets.

---

### E. Resource Exhaustion & Denial of Service (DoS)
- **Threat Scenario**: Malicious clients flood the API with giant brief payloads, initiate unbounded concurrent builds, exhaust disk space with temporary artifacts, or exhaust LLM token budgets.
- **Risk Level**: **HIGH**
- **Existing Controls**:
  - Request body size limit enforced by API middleware (`RequestSizeLimitMiddleware`, default 1MB).
  - Pydantic bounds on all input lengths (e.g. `content_notes` max 10,000 chars, `pages` max 50).
  - Sliding-window rate limiter per API key / IP on creation, read, and write operations.
  - LLM token budgets and cost limits enforced per run (`TokenBudgetTracker`, default $5.00 limit).
  - Finite graph repair attempts: QA repairs capped at 3 cycles before triggering deterministic failure.
  - Ephemeral sandbox workspaces and containers automatically pruned by `CleanupService` based on retention thresholds.
- **Verification Method**: `test_rate_limiter.py`, `test_request_size_limit.py`, and `test_cleanup_service.py`.
- **Residual Risk**: Disk exhaustion if high volumes of concurrent builds occur simultaneously on host.
- **Follow-up Action**: Implement worker concurrency queues (e.g. maximum 3 concurrent container builds).

---

### F. Authorization and Workflow Integrity
- **Threat Scenario**: Unauthorized approval or revision of another client's run, replay attacks, or promoting unapproved/failed revisions to production.
- **Risk Level**: **CRITICAL**
- **Existing Controls**:
  - Strict constant-time API key verification (`hmac.compare_digest`) via `get_api_key`. Production fail-closed guarantee (refuses startup if key unset).
  - Finite state machine (`RunState` transitions) enforced by `Run` domain aggregate. Invalid state transitions raise `InvalidStateTransitionError`.
  - Revisions are cryptographically and monotonically bound: `ApproveRunRequest` and `ReviseRunRequest` require explicit `revision` matching `current_revision`.
  - Idempotency key tracking in `WorkflowRunner` prevents duplicate run submissions or conflicting approvals.
  - Production promotion in `deploy` node requires valid QA passage and prior approval.
- **Verification Method**: `test_approvals.py`, `test_workflow_idempotency.py`, `test_run_state_machine.py`.
- **Residual Risk**: Single shared API key in Phase 10-15 lacks multi-tenant role-based access control (RBAC).
- **Follow-up Action**: Implement JWT/OAuth2 user-level authentication with organization scoping.

---

### G. Supply-Chain and Dependency Security
- **Threat Scenario**: Malicious dependencies in npm (`site-astro`, Next.js dashboard) or PyPI packages, vulnerable container base images, or tampered CI actions.
- **Risk Level**: **MEDIUM**
- **Existing Controls**:
  - Dependency lockfiles (`pnpm-lock.yaml`, pinned dependencies in `pyproject.toml`).
  - Pinned minimal container base images (`node:20.18.0-bookworm-slim`, `python:3.12-slim-bookworm`).
  - Pinned GitHub Actions versions (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`).
  - CI dependency audits (`pnpm audit --audit-level=high` and Python vulnerability checks).
- **Verification Method**: CI workflow checks in `.github/workflows/ci.yml`.
- **Residual Risk**: Zero-day vulnerabilities in indirect transitive dependencies.
- **Follow-up Action**: Configure Dependabot or Renovate with automated PR validation.

---

## 3. Summary Assessment Matrix

| Threat Category | Pre-Mitigation Risk | Primary Control | Verification Evidence | Residual Risk | Status |
|---|---|---|---|---|---|
| **Prompt Injection** | HIGH | Fenced prompts, Pydantic validation, human approval gate | `test_brief.py`, evals | Semantic drift | **MITIGATED** |
| **Sandbox Escape** | CRITICAL | Cap drop ALL, no socket, no-new-privileges, network none | `docker_sandbox.py` tests | Kernel zero-days | **MITIGATED** |
| **Secret Leakage** | CRITICAL | Context log redactor, Gitleaks CI, safe trace metadata | `test_structured_logging.py` | User input secrets | **MITIGATED** |
| **SSRF** | HIGH | `validate_safe_url`, private/loopback/metadata IP blocks | `test_url_policy.py` | DNS rebinding | **MITIGATED** |
| **Resource Exhaustion** | HIGH | Request size limits, rate limiter, token budgets, cleanup | `test_rate_limiter.py`, cleanup | Host disk burst | **MITIGATED** |
| **Workflow Integrity** | CRITICAL | Constant-time auth, domain state machine, revision locks | `test_approvals.py` | Single API key | **MITIGATED** |
| **Supply Chain** | MEDIUM | Lockfiles, pinned container bases, minimal alpine/slim images | CI build checks | Transitive updates | **MONITORED** |
