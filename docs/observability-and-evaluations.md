# Observability, Distributed Tracing, and Evaluation Framework Guide

This document establishes operational procedures, architectural guidelines, and runbooks for the **Agency** distributed tracing, structured logging, and automated evaluation framework.

---

## 1. Overview and Architecture

Agency incorporates comprehensive observability without compromising Clean Architecture principles:
- **Distributed Tracing**: Standardized via the `TracingPort` abstraction (`agency.application.ports.tracing`). Workflow runs map 1:1 to root traces in Langfuse, with fine-grained child spans tracking each LangGraph node and agent operation.
- **Structured JSON Logging**: Standard library Python logging with `JSONFormatter` providing UTC ISO timestamps, trace/run/request correlation via `contextvars`, and automated sensitive credential redaction.
- **Evaluation Framework**: A version-controlled dataset of 12 client briefs (`backend/evals/briefs/`) scored across build reliability, QA compliance, Lighthouse web vitals, cost, duration, and a deterministic 7-dimension copy quality rubric.

---

## 2. Configuration & Environment Variables

All settings are configured through environment variables. Zero credentials are required for local development or CI execution.

| Variable | Description | Default | Environment |
|---|---|---|---|
| `LANGFUSE_ENABLED` | Enables or disables trace dispatch to Langfuse | `false` | All |
| `LANGFUSE_HOST` | URL endpoint for self-hosted or cloud Langfuse | `http://localhost:3000` | Local / Prod |
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public API key | `None` | Local / Prod |
| `LANGFUSE_SECRET_KEY` | Langfuse project secret API key | `None` | Local / Prod |
| `LOG_LEVEL` | Minimum logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | All |
| `MAX_EVAL_BUDGET_USD` | Hard budget cap in USD for manual real-LLM evaluation suites | `5.00` | Real Eval |

---

## 3. Self-Hosted Langfuse Deployment (Docker Compose)

The repository provides a self-hosted Langfuse v2 topology under `docker/compose/docker-compose.langfuse.yml` containing:
- `langfuse-server`: Main API and web dashboard.
- `langfuse-worker`: Background asynchronous ingestion and processing.
- `langfuse-db`: Dedicated PostgreSQL 16 database with persistent storage.
- `langfuse-redis`: Redis 7 caching and queue broker.

### Local Startup & Health Check

```bash
# 1. Start the observability stack in background
docker compose -f docker/compose/docker-compose.langfuse.yml up -d

# 2. Check service status and healthchecks
docker compose -f docker/compose/docker-compose.langfuse.yml ps

# 3. View live server logs
docker compose -f docker/compose/docker-compose.langfuse.yml logs -f langfuse-server
```

Once running, access the Langfuse UI at [http://localhost:3000](http://localhost:3000):
1. Create an initial local admin user.
2. Create a project named `agency`.
3. In Project Settings -> API Keys, generate a keypair.
4. Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in your `.env`.
5. Set `LANGFUSE_ENABLED=true`.

### Locating Traces by Run ID

Every Agency workflow execution automatically assigns its domain `run_id` as the top-level trace identifier:
- To inspect a run, navigate to **Traces** in the Langfuse dashboard and search directly for the `run_id` (e.g., `run-20261021-092126-3b5dcb`).
- Every stage (`node.intake`, `node.pm_spec`, `node.designer`, `node.build`, `node.qa`, etc.) is represented as an explicit child span with start time, duration, and error status.

### Shutdown & Data Backup

```bash
# Stop containers while preserving data volumes
docker compose -f docker/compose/docker-compose.langfuse.yml down

# Complete teardown including persistent volumes (CAUTION: deletes all stored traces)
docker compose -f docker/compose/docker-compose.langfuse.yml down -v
```

---

## 4. Structured JSON Logging and Secret Redaction

Structured logging ensures all output is machine-parseable JSON formatted to standard output:

```json
{
  "timestamp": "2026-10-21T09:21:26.741003+00:00",
  "level": "INFO",
  "logger": "agency.application.graph.nodes",
  "message": "Node 'pm_spec' executed successfully",
  "environment": "development",
  "run_id": "run-4d22cf",
  "trace_id": "run-4d22cf",
  "span_id": "span-8f20b3",
  "node_name": "pm_spec",
  "request_id": "req-9b341f"
}
```

### Sensitive Data Protection Rules

The logging framework automatically strips or redacts:
- HTTP `Authorization: Bearer <token>` headers -> `Bearer [REDACTED]`.
- API keys, secrets, passwords, and tokens matching key-value pairs or query strings.
- PEM formatted private key blocks (e.g., RSA, EC, or OpenSSH keys).
- Full LLM prompts and raw client briefs at `INFO` level.

---

## 5. Automated Evaluation Framework

The evaluation framework verifies agent synthesis and website generation without external network calls or paid credentials.

### Evaluation Dataset

The dataset in `backend/evals/briefs/` covers 12 diverse client archetypes:
1. `developer.json`: Staff distributed systems engineer portfolio.
2. `designer.json`: Product and design systems lead portfolio.
3. `photographer.json`: Architectural and documentary photographer.
4. `student.json`: Computer science undergraduate portfolio.
5. `writer.json`: Investigative essayist portfolio.
6. `musician.json`: Contemporary cellist and ambient composer.
7. `freelancer.json`: Full-stack cloud engineering consultant.
8. `small_business.json`: Artisanal sourdough bakery and espresso bar.
9. `consultant.json`: Supply chain and automation management advisory.
10. `personal_brand.json`: Cognitive neuroscientist and keynote author.
11. `creative_agency.json`: 3D motion design and experiential studio.
12. `local_services.json`: Residential & commercial HVAC mechanical contractor.

### Running Evaluations via CLI

```bash
# 1. Run deterministic FakeLLM evaluation across all 12 briefs (CI Default)
agency eval run --mode fake

# 2. Run deterministic evaluation on a single brief
agency eval run --mode fake --brief developer

# 3. View the generated Markdown report for a specific evaluation run
agency eval report --run-id <evaluation-run-id>

# 4. Run real LLM evaluations with budget limit (Manual operator run)
export GEMINI_API_KEY="your-api-key"
agency eval run --mode real --max-budget 2.50
```

---

## 6. Metric Definitions & Pass Thresholds

| Metric | Evaluation Method | Pass Criteria |
|---|---|---|
| **Build Success** | Subprocess exit code == 0 AND required artifacts (`index.html`, requested page routes) verified on disk. | 100% success rate |
| **QA Pass Rate** | Mandatory automated checks (Astro build, tokens, content integrity). Mandatory failures are never averaged into a passing result. | 100% pass rate |
| **Lighthouse Scores** | Actual headless Chrome Lighthouse audit for performance, accessibility, best practices, and SEO. If Lighthouse is not installed, it is explicitly reported as unavailable rather than fabricating scores. | Available scores >= 0.85 |
| **Copy Quality Rubric** | Deterministic 7-dimension scoring (Brief alignment, section completeness, specificity, readability, tone consistency, absence of unsupported claims, absence of placeholders). | Overall score >= 7.0/10.0 and absence of placeholders >= 9.0/10.0 |
| **Cost Accounting** | Distinguishes actual provider reported cost from standard rate card estimates. In fake mode, actual cost is strictly $0.00. | Real mode within `MAX_EVAL_BUDGET_USD` |
| **Duration Tracking** | Wall-clock start/end timestamps tracked alongside monotonic clock elapsed time. | Average pipeline execution < 30s |

---

## 7. Report Artifacts

Every completed evaluation run writes structured reports to `runs/evals/<eval_run_id>/`:
- `report.md`: High-level summary table, per-brief breakdown, failed check details, unavailable metric explanations, and actionable recommendations.
- `results.csv`: Flat, RFC 4180-compliant table with 20 columns suitable for historical analysis and CI dashboarding.
