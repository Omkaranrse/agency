# Evaluation Suite Report — `eval-20261021-093605-9fe603`

## 1. Executive Summary

- **Evaluation Run ID**: `eval-20261021-093605-9fe603`
- **Timestamp (UTC)**: 2026-10-21T09:36:05.580569+00:00
- **Execution Mode**: `fake`
- **Dataset Hash**: `4d6ce61fedaf2801`
- **Application Revision**: `development`
- **Python Version**: 3.12.14

| Metric | Result | Target Threshold | Status |
|---|---|---|---|
| **Briefs Attempted** | 1 | 12 | PARTIAL |
| **Build Success Rate** | 100.0% (1/1) | 100% | PASS |
| **QA Pass Rate** | 100.0% | 100% | PASS |
| **Average Duration** | 0.00s (median 0.00s) | < 30s | PASS |
| **Total Actual Cost** | $0.0000 USD | N/A (Fake mode: $0.00) | PASS |
| **Total Estimated Cost** | $0.0000 USD | N/A | INFO |
| **Average Copy Quality** | 9.0 / 10.0 | >= 7.0 | PASS |
| **Unavailable Metrics** | 1 | 0 (CI environment) | WARN |

## 2. Per-Brief Evaluation Results

| Brief ID | Category | Build | QA | Copy Score | Perf | A11y | Cost (Act/Est) | Duration | Status |
|---|---|---|---|---|---|---|---|---|---|
| `developer` | Portfolio | PASS | PASS | 9.0/10 | N/A | N/A | $0.000 / $0.000 | 0.00s | [OK] PASS |

## 3. Failed Checks and Anomalies

No failures detected across evaluated briefs. All mandatory quality gates passed.

## 4. Missing or Unavailable Measurements

- `developer` Lighthouse: Lighthouse CLI binary not found in environment.

## 5. Investigation and Recommendations

- Ensure Lighthouse CLI and headless Chrome are installed if full web vitals auditing is desired in CI.
- For manual real-LLM runs, verify token budgets are configured via `MAX_EVAL_BUDGET_USD`.
- Regularly update brief fixtures when introducing new Astro template components or layout variants.
