# ADR 0009: Production Hardening and Operational Security Controls

## Status
Accepted

## Context
Deploying multi-agent AI systems into production environments introduces critical operational vectors: orphaned containers, SSRF from user-supplied URLs, denial-of-service via oversized payloads, secret leakage in logs, and uncoordinated shutdowns.

## Decision
In Phase 15, we enacted comprehensive hardening measures:
1. **SSRF Defense Policy**: Enforced `validate_safe_url` blocking private IP ranges, loopback (`127.0.0.1`, `::1`), link-local metadata (`169.254.169.254`), and dangerous schemes on all client links.
2. **Operational Health & Readiness**:
   - `/health` indicates process liveness without leaking internals.
   - `/ready` verifies required persistence and workflow runner readiness, returning 503 if unavailable while treating optional telemetry as non-blocking.
3. **Graceful Workflow Draining**: `WorkflowRunner.shutdown()` signals cancellation to active pipelines, stops accepting new work, and drains background tasks within a bounded deadline.
4. **Maintenance Cleanup Service**: `agency cleanup` purges orphaned sandbox containers labeled `agency.managed=true` and temporary workspace directories while strictly protecting active runs. Supports `--dry-run`.
5. **Multi-Stage Non-Root Containers**: Backend runs as `agency:agency` (UID 1001), dashboard runs as `nextjs:nodejs` (UID 1001), and full stack orchestrates via validated `docker-compose.yml`.
6. **Automated Secret Scanning**: Gitleaks integrated into CI with explicit allowlists for test fixtures.

## Consequences
- Protects internal cloud metadata and host networks from SSRF.
- Prevents resource leaks and abandoned containers.
- Guarantees clean shutdowns and safe container lifecycles.
