# Evaluation Suite Report — `eval-20261021-092126-3b5dcb`

## 1. Executive Summary

- **Evaluation Run ID**: `eval-20261021-092126-3b5dcb`
- **Timestamp (UTC)**: 2026-10-21T09:21:26.741003+00:00
- **Execution Mode**: `fake`
- **Dataset Hash**: `4d6ce61fedaf2801`
- **Application Revision**: `development`
- **Python Version**: 3.12.14

| Metric | Result | Target Threshold | Status |
|---|---|---|---|
| **Briefs Attempted** | 12 | 12 | PASS |
| **Build Success Rate** | 100.0% (12/12) | 100% | PASS |
| **QA Pass Rate** | 100.0% | 100% | PASS |
| **Average Duration** | 0.00s (median 0.00s) | < 30s | PASS |
| **Total Actual Cost** | $0.0000 USD | N/A (Fake mode: $0.00) | PASS |
| **Total Estimated Cost** | $0.0000 USD | N/A | INFO |
| **Average Copy Quality** | 8.7 / 10.0 | >= 7.0 | PASS |
| **Unavailable Metrics** | 12 | 0 (CI environment) | WARN |

## 2. Per-Brief Evaluation Results

| Brief ID | Category | Build | QA | Copy Score | Perf | A11y | Cost (Act/Est) | Duration | Status |
|---|---|---|---|---|---|---|---|---|---|
| `consultant` | Business | PASS | PASS | 8.8/10 | N/A | N/A | $0.000 / $0.000 | 0.01s | [OK] PASS |
| `creative_agency` | Agency | PASS | PASS | 8.2/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `designer` | Portfolio | PASS | PASS | 9.0/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `developer` | Portfolio | PASS | PASS | 9.0/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `freelancer` | Portfolio | PASS | PASS | 9.0/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `local_services` | Services | PASS | PASS | 8.9/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `musician` | Portfolio | PASS | PASS | 8.5/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `personal_brand` | Personal Brand | PASS | PASS | 7.9/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `photographer` | Portfolio | PASS | PASS | 8.7/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `small_business` | Business | PASS | PASS | 8.6/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `student` | Portfolio | PASS | PASS | 8.9/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |
| `writer` | Portfolio | PASS | PASS | 8.6/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |

## 3. Failed Checks and Anomalies

No failures detected across evaluated briefs. All mandatory quality gates passed.

## 4. Missing or Unavailable Measurements

- `consultant` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `creative_agency` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `designer` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `developer` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `freelancer` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `local_services` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `musician` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `personal_brand` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `photographer` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `small_business` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `student` Lighthouse: Lighthouse CLI binary not found in execution environment.
- `writer` Lighthouse: Lighthouse CLI binary not found in execution environment.

## 5. Investigation and Recommendations

- Ensure Lighthouse CLI and headless Chrome are installed if full web vitals auditing is desired in CI.
- For manual real-LLM runs, verify token budgets are configured via `MAX_EVAL_BUDGET_USD`.
- Regularly update brief fixtures when introducing new Astro template components or layout variants.
