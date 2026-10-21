# Operations Runbook — Agency

This runbook provides step-by-step procedures for operating, diagnosing, recovering, and maintaining **Agency** across development and production environments.

---

## 1. System Operations Lifecycle

### A. Starting the Complete Local Stack
```bash
# 1. Ensure configuration is present
cp .env.example .env

# 2. Launch complete full-stack Docker Compose (Backend, Dashboard, Langfuse Stack)
docker compose up -d

# 3. Verify container status
docker compose ps

# 4. Check API health and readiness
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready

# 5. Access services
# Dashboard: http://localhost:3000
# API Docs:  http://localhost:8000/docs
# Langfuse:  http://localhost:3001
```

### B. Stopping and Restarting
```bash
# Graceful shutdown (sends SIGTERM, drains workflow runs, and saves checkpoints)
docker compose stop

# Teardown containers and networks
docker compose down

# Full reset including persistent volumes (destructive)
docker compose down -v
```

---

## 2. Health, Readiness, and Diagnostics

### A. Health Check (`GET /health`)
- **Purpose**: Verifies that the FastAPI process is alive and receiving traffic.
- **Expected Response**: `200 OK`
  ```json
  {"status": "ok", "timestamp": "2026-10-21T10:00:00Z", "components": {}}
  ```
- **Triage**: If unresponsive or returning 5xx, inspect container logs: `docker compose logs backend`.

### B. Readiness Check (`GET /ready`)
- **Purpose**: Verifies that required persistence and workflow supervisors are ready to accept new runs.
- **Expected Response**: `200 OK`
  ```json
  {
    "status": "ready",
    "timestamp": "2026-10-21T10:00:00Z",
    "components": {
      "persistence": "ok",
      "workflow_runner": "ready",
      "telemetry": "optional_available"
    }
  }
  ```
- **Degraded Status**: Returns `503 Service Unavailable` if persistence is unreachable or the runner is shutting down. Telemetry (Langfuse) offline does NOT fail readiness.

---

## 3. Investigating Run Failures and Checkpoints

### A. Inspecting a Run via API & CLI
```bash
# Get run summary via API
curl -H "X-API-Key: agency-secret-key-12345" http://localhost:8000/api/v1/runs/<run-id>

# Inspect structured log output for run ID
docker compose logs backend | grep '"run_id":"<run-id>"' | jq .
```

### B. Inspecting Durable LangGraph Checkpoints
Workflow state is persisted into SQLite checkpoints at every node boundary.
```bash
# Open SQLite checkpoints database
sqlite3 data/checkpoints.sqlite

# Query saved checkpoints for a run
sqlite> SELECT thread_id, checkpoint_id, checkpoint FROM checkpoints WHERE thread_id = '<run-id>';

# Check write events
sqlite> SELECT * FROM writes WHERE thread_id = '<run-id>';
```

---

## 4. Maintenance and Stale Sandbox Cleanup

Orphaned Docker sandboxes or stale temporary workspace folders can be purged via the CLI:

```bash
# 1. Run simulation check (dry-run mode)
PYTHONPATH=backend/src:backend python -m agency.interfaces.cli.main cleanup --dry-run --retention-hours 24

# 2. Execute active cleanup
PYTHONPATH=backend/src:backend python -m agency.interfaces.cli.main cleanup --retention-hours 24
```

### Cleanup Guarantees:
- Only containers with label `agency.managed=true` are evaluated.
- Active runs (in states `BUILDING`, `TESTING`, `AWAITING_APPROVAL`) are strictly protected.
- Reclaims disk space while preserving completed client deliverables in `artifacts/`.

---

## 5. Backup, Restoration, and Data Retention

### A. Data Requiring Backup
1. **LangGraph Checkpoints**: `data/checkpoints.sqlite` (contains all workflow states).
2. **Client Artifacts**: `artifacts/` (contains generated bundles, specs, and reports).
3. **Langfuse Database**: PostgreSQL volume `agency_langfuse_postgres_data`.

### B. Backup Procedure
```bash
# 1. Create timestamped backup archive
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p backups/${BACKUP_DATE}

# 2. Safely backup SQLite database using VACUUM INTO
sqlite3 data/checkpoints.sqlite "VACUUM INTO 'backups/${BACKUP_DATE}/checkpoints.sqlite';"

# 3. Archive artifact storage
tar -czf backups/${BACKUP_DATE}/artifacts.tar.gz artifacts/
```

### C. Restoration Procedure
```bash
# 1. Stop backend service
docker compose stop backend

# 2. Restore SQLite checkpoints database
cp backups/${BACKUP_DATE}/checkpoints.sqlite data/checkpoints.sqlite

# 3. Restore artifacts
tar -xzf backups/${BACKUP_DATE}/artifacts.tar.gz -C ./

# 4. Restart backend
docker compose start backend

# 5. Verify readiness
curl -f http://localhost:8000/ready
```

---

## 6. Credential Rotation and Incident Response

### Compromised API Key or Provider Token
1. **Revoke Old Token**:
   - For GitHub: Revoke the Personal Access Token in GitHub Settings -> Developer Settings -> Personal access tokens.
   - For Cloudflare: Delete the API token in Cloudflare Dashboard -> User Profile -> API Tokens.
   - For Gemini: Rotate the API Key in Google AI Studio.
2. **Update Environment**:
   - Update `.env` with new credentials.
   - Restart affected containers: `docker compose restart backend`.
3. **Verify Git History**:
   - Confirm no secrets entered Git history:
     ```bash
     gitleaks detect --source . --config .gitleaks.toml
     ```

---

## 7. Outage Mitigation and Fallbacks

### A. LLM Provider Outage
- **Symptom**: Model calls timeout or return HTTP 429/500 errors.
- **Action**:
  - Switch provider via router configuration: fallback from `gemini` to local `ollama` or `openai`.
  - In evaluation mode: execute suite using `--mode fake` with zero provider dependency.

### B. GitHub / Cloudflare Outage
- **Symptom**: `github_publish` or `cloudflare_preview` fails.
- **Action**:
  - Check status at `https://www.githubstatus.com` and `https://www.cloudflarestatus.com`.
  - Workflow pauses at failed stage; once service is restored, re-trigger execution or submit approval.
  - In dev/eval environments: switch to `FakeGit` and `FakeDeploy` adapters.
