# Production-Readiness Assessment — Agency

This report provides an honest, evidence-based assessment of the production readiness of **Agency** following Phase 15.

Every category is evaluated according to strict criteria:
- **PASS**: Verified with concrete test evidence and operational validation.
- **PARTIAL**: Implemented, but with known limitations or incomplete live verification.
- **FAIL**: Unresolved architectural or security deficiency.
- **NOT TESTED**: Insufficient evidence or unexecuted verification in the current environment.

---

## Executive Summary

| Category | Assessment | Primary Evidence / Verification | Key Limitations |
|---|---|---|---|
| **1. Architecture & Maintainability** | **PASS** | Clean architecture; 222 Python files pass mypy strict | Strict inward dependency rule enforced |
| **2. Authentication & Authorization** | **PARTIAL** | Constant-time HMAC API key check | Single global API key; lacks user RBAC |
| **3. Prompt-Injection Resistance** | **PARTIAL** | Pydantic validation; approval gate | Semantic injection cannot be 100% prevented by prompts |
| **4. Sandbox Isolation** | **PASS** | Non-root, `network=none`, `cap_drop=ALL`, limits | Host Docker engine must be kept patched |
| **5. Secret Management** | **PASS** | Automated log/trace scrubbing; Gitleaks scan | Relies on environment variables |
| **6. SSRF Protection** | **PASS** | `validate_safe_url` blocks private/metadata IPs | DNS rebinding protection requires pre-socket pin |
| **7. Resource Exhaustion** | **PASS** | Request size limit, rate limiter, timeouts | Single-host disk burst limits |
| **8. LLM Cost Controls** | **PASS** | `TokenBudgetTracker`, budget cap, $0 fake mode | Cloud provider billing lag |
| **9. Workflow Durability** | **PASS** | SQLite checkpoints, state machine transitions | SQLite concurrency limits under high load |
| **10. Event Streaming** | **PASS** | SSE endpoints with `Last-Event-ID` resume | Client must reconnect over unstable WAN |
| **11. GitHub Publishing** | **PARTIAL** | Verified with `FakeGit`; real API requires token | Live GitHub API rate limits not load tested |
| **12. Cloudflare Deployment** | **PARTIAL** | Verified with `FakeDeploy`; real API requires token | Live Cloudflare propagation latency |
| **13. QA Reliability** | **PASS** | Astro exit 0, mandatory checks never averaged | Lighthouse requires local Chrome in CI |
| **14. Observability** | **PASS** | Self-hosted Langfuse stack, JSON logs, no-op fallback | Langfuse requires periodic vacuuming |
| **15. Automated Evaluations** | **PASS** | 12 validated briefs, runner, Markdown/CSV reports | Real LLM evals require manual trigger |
| **16. Supply-Chain Security** | **PASS** | Pinned lockfiles, slim base images, Gitleaks CI | Transitive updates must be monitored |
| **17. Backup & Restoration** | **PARTIAL** | Documented VACUUM INTO and restore procedure | Live automated point-in-time restore untested |
| **18. Cleanup & Retention** | **PASS** | `CleanupService`, `agency cleanup --dry-run` | Requires external cron or container scheduler |
| **19. CI/CD Pipeline** | **PASS** | Lint, types, tests, builds, compose validation | PRs use fake mode to prevent secret exposure |
| **20. Monitoring & Alerts** | **PARTIAL** | Health/readiness checks; Langfuse metrics | Lacks Prometheus / Grafana alert rules |
| **21. Client Data Privacy** | **PASS** | No tracking; private artifacts storage | Brief content notes stored in plaintext DB |
| **22. Operational Documentation** | **PASS** | Architecture, ADRs (1-9), Runbook, Demo, Security | Must be maintained during future changes |

---

## Detailed Evaluation by Category

### 1. Architecture and Maintainability
- **Status**: **PASS**
- **Evidence**: `.venv/bin/mypy src evals tests` (222 files passed without errors in strict mode); `.venv/bin/ruff check backend` (0 errors).
- **Observed Outcome**: Clean Architecture boundaries strictly preserved (`Domain <- Application <- Infrastructure / Interfaces`).
- **Remaining Limitations**: Application graph state dictionary relies on TypedDict rather than pure immutable classes.
- **Recommended Follow-up**: Continue strict lint and type checks on every PR.

### 2. Authentication and Authorization
- **Status**: **PARTIAL**
- **Evidence**: `backend/tests/api/test_runs.py` and `test_approvals.py` verify 401 Unauthorized when missing API key; constant-time comparison verified.
- **Observed Outcome**: Prevents unauthorized API access and timing attacks.
- **Remaining Limitations**: Single shared API key across all operators. No multi-tenant user authentication, RBAC, or team separation.
- **Recommended Follow-up**: Introduce OAuth2/OIDC or JWT claims with tenant isolation in future multi-user versions.

### 3. Prompt-Injection Resistance
- **Status**: **PARTIAL**
- **Evidence**: `test_brief.py` tests input boundaries; prompt inputs are separated from system instructions.
- **Observed Outcome**: Malicious prompts cannot force deployments because human approval is enforced at the domain state machine level.
- **Remaining Limitations**: Prompt injection is an open AI safety problem; malicious instructions could alter copy or styling.
- **Recommended Follow-up**: Maintain mandatory human approval before production deployments.

### 4. Sandbox Isolation
- **Status**: **PASS**
- **Evidence**: `docker_sandbox.py` enforces `user="1000:1000"`, `cap_drop=["ALL"]`, `security_opt=["no-new-privileges:true"]`, `network_mode="none"`, `mem_limit="512m"`, `nano_cpus=1_000_000_000`. Docker socket is never mounted.
- **Observed Outcome**: Generated code cannot access the host network, host filesystem, or Docker daemon.
- **Remaining Limitations**: Kernel vulnerabilities in the host Linux system.
- **Recommended Follow-up**: Run containers inside microVMs (e.g. Kata or AWS Firecracker) if offering public multi-tenant untrusted execution.

### 5. Secret Management
- **Status**: **PASS**
- **Evidence**: `backend/tests/unit/infrastructure/observability/test_structured_logging.py` verifies Bearer tokens, passwords, and API keys are redacted before logging. Gitleaks scanning configured in `.gitleaks.toml`.
- **Observed Outcome**: Logs and traces do not emit credentials.
- **Remaining Limitations**: Secrets are loaded from environment variables (`.env`).
- **Recommended Follow-up**: Integrate HashiCorp Vault or AWS Secrets Manager for production deployments.

### 6. SSRF Protection
- **Status**: **PASS**
- **Evidence**: `backend/tests/unit/domain/test_url_policy.py` (18 passed tests).
- **Observed Outcome**: Brief links and fetch destinations targeting `127.0.0.1`, `169.254.169.254`, `localhost`, `10.0.0.0/8`, `192.168.0.0/16`, `[::1]`, and non-HTTP schemes are rejected.
- **Remaining Limitations**: Application-level validation does not eliminate time-of-check to time-of-use (TOCTOU) DNS rebinding.
- **Recommended Follow-up**: Enforce IP address pinning at the HTTP client socket level for outbound network requests.

### 7. Resource Exhaustion Protection
- **Status**: **PASS**
- **Evidence**: `RequestSizeLimitMiddleware` rejects payloads > 1MB; `InMemoryRateLimiter` enforces rate caps; `DockerSandbox` enforces PID caps (100) and timeouts (60s).
- **Observed Outcome**: System is protected against oversized request bodies and fork bombs.
- **Remaining Limitations**: Rate limiter is in-memory; across multiple distributed replicas, Redis-backed rate limiting would be needed.
- **Recommended Follow-up**: Connect `InMemoryRateLimiter` to Redis when running multiple API instances behind a load balancer.

### 8. LLM Cost Controls
- **Status**: **PASS**
- **Evidence**: `backend/tests/unit/infrastructure/llm/` tests token budgets; default cap $5.00 per run. Fake mode runs with $0.00.
- **Observed Outcome**: Workflows terminate deterministically when budget is exceeded.
- **Remaining Limitations**: Token pricing is based on static model tables if providers do not return exact billing metadata.
- **Recommended Follow-up**: Regularly update pricing coefficients in `backend/src/agency/infrastructure/llm/pricing.py`.

### 9. Workflow Durability and Recovery
- **Status**: **PASS**
- **Evidence**: `test_workflow_runner_shutdown.py` and `test_workflow_idempotency.py` verify that workflows pause, persist checkpoints, and resume from approval states.
- **Observed Outcome**: State is preserved across API restarts in `checkpoints.sqlite`.
- **Remaining Limitations**: High-throughput concurrent writes to a single SQLite database can experience lock contention.
- **Recommended Follow-up**: Migrate to PostgreSQL checkpointing (`AsyncPostgresSaver`) for enterprise multi-worker scale.

### 10. Event Streaming
- **Status**: **PASS**
- **Evidence**: `backend/tests/api/test_events.py` verifies SSE connection, message serialization, and `Last-Event-ID` resumption.
- **Observed Outcome**: Real-time updates delivered without WebSockets.
- **Remaining Limitations**: In-memory event buffers require persistent event feeds for long disconnect intervals.
- **Recommended Follow-up**: Maintain durable event feed retention window of 7 days.

### 11. GitHub Publishing
- **Status**: **PARTIAL**
- **Evidence**: `GitHubAdapter` implemented and verified via unit tests and `FakeGit`.
- **Observed Outcome**: Successfully structures commits and branches.
- **Remaining Limitations**: Live rate limits and transient network timeouts to `api.github.com` not load tested in sandbox environment.
- **Recommended Follow-up**: Configure exponential backoff retry policies for GitHub API calls.

### 12. Cloudflare Deployment
- **Status**: **PARTIAL**
- **Evidence**: `CloudflarePagesAdapter` implemented and verified via `FakeDeploy`.
- **Observed Outcome**: Builds preview and production deployment payloads.
- **Remaining Limitations**: Live Cloudflare deployment propagation latency and quota limits not tested with real credentials.
- **Recommended Follow-up**: Perform periodic manual staging deployment smoke tests.

### 13. QA Reliability
- **Status**: **PASS**
- **Evidence**: QA service validates Astro exit codes, artifact presence, and routes. Mandatory check failures never average into a passing score.
- **Observed Outcome**: Catches missing pages and broken builds deterministically.
- **Remaining Limitations**: Lighthouse audits require local headless Chromium and are marked unavailable in lightweight environments.
- **Recommended Follow-up**: Containerize Lighthouse runner with pre-installed Chromium in CI.

### 14. Observability
- **Status**: **PASS**
- **Evidence**: Langfuse stack configured via Docker Compose; `TracingPort` handles span parent-child relationships; fails open when Langfuse is offline (`NoOpTracingPort`).
- **Observed Outcome**: Tracing functions seamlessly without blocking core workflow execution.
- **Remaining Limitations**: Self-hosted Langfuse database requires periodic maintenance.
- **Recommended Follow-up**: Configure retention policies in Langfuse settings.

### 15. Automated Evaluations
- **Status**: **PASS**
- **Evidence**: `agency eval run --mode fake` executed across all 12 briefs; 100% build pass, 100% QA pass rate, reports generated in Markdown and CSV.
- **Observed Outcome**: Deterministic, repeatable regression testing.
- **Remaining Limitations**: Real-LLM evaluation requires manual trigger to prevent unexpected API costs.
- **Recommended Follow-up**: Run nightly real-LLM evals on a dedicated budget.

### 16. Dependency & Supply-Chain Security
- **Status**: **PASS**
- **Evidence**: Pinned `pnpm-lock.yaml`, pinned dependencies in `pyproject.toml`, pinned Docker base images.
- **Observed Outcome**: Reproducible builds in Docker and CI.
- **Remaining Limitations**: Third-party upstream library vulnerabilities.
- **Recommended Follow-up**: Enable Dependabot alerts.

### 17. Backup and Restoration
- **Status**: **PARTIAL**
- **Evidence**: SQLite `VACUUM INTO` and artifact archive commands documented and tested manually.
- **Observed Outcome**: Database and artifacts can be safely snapshotted.
- **Remaining Limitations**: Automated scheduled disaster recovery drills not yet running on a cron schedule.
- **Recommended Follow-up**: Schedule automated daily S3/GCS backup sync jobs.

### 18. Cleanup and Retention
- **Status**: **PASS**
- **Evidence**: `CleanupService` unit tests in `test_cleanup_service.py`; CLI command `agency cleanup --dry-run` verified.
- **Observed Outcome**: Safely removes abandoned containers and temporary workspaces while protecting active runs.
- **Remaining Limitations**: Requires external invocation via cron or Kubernetes CronJob.
- **Recommended Follow-up**: Add an optional in-process background maintenance timer.

### 19. CI/CD Quality Gates
- **Status**: **PASS**
- **Evidence**: `.github/workflows/ci.yml` and `.github/workflows/evals.yml` with least-privilege permissions, lint, types, tests, builds, and compose validation.
- **Observed Outcome**: Comprehensive automated verification on every PR.
- **Remaining Limitations**: Cloud provider secrets are not accessible to fork PRs (by design).
- **Recommended Follow-up**: Maintain strict PR isolation.

### 20. Monitoring and Incident Response
- **Status**: **PARTIAL**
- **Evidence**: `/health` and `/ready` endpoints; structured JSON logs with correlation IDs.
- **Observed Outcome**: Basic liveness and readiness monitoring in place.
- **Remaining Limitations**: Lacks Prometheus metrics exporter (`/metrics`) and PagerDuty/Opsgenie integration.
- **Recommended Follow-up**: Add Prometheus middleware and Grafana dashboard alerts.

### 21. Client Data Privacy
- **Status**: **PASS**
- **Evidence**: Local artifact storage enforces access boundaries; logs redact sensitive strings; no analytics telemetry tracked.
- **Observed Outcome**: Client IP and briefs are protected.
- **Remaining Limitations**: Briefs are stored in plaintext in the database.
- **Recommended Follow-up**: Enable disk-level encryption (LUKS / EBS encryption) for database volumes.

### 22. Operational Documentation
- **Status**: **PASS**
- **Evidence**: `docs/architecture.md`, `docs/security.md`, `docs/runbook.md`, `docs/demo.md`, `docs/adr/` (ADR 0001-0009).
- **Observed Outcome**: Detailed, actionable guidance for operators and engineers.
- **Remaining Limitations**: Documentation must be kept in sync as features evolve.
- **Recommended Follow-up**: Require documentation updates in PR review templates.

---

## Conclusion

The **Agency** platform has achieved a strong security and operational foundation. While the core architecture, sandbox isolation, SSRF defenses, and evaluation framework are production-hardened (**PASS**), production deployment at enterprise scale currently carries **PARTIAL** status until multi-user RBAC authentication, live Cloudflare/GitHub credential load testing, and automated off-site backups are enabled.
