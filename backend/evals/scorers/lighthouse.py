"""Lighthouse audit scorer with explicit unavailable handling."""

import json
import shutil
import subprocess
from pathlib import Path

from evals.schemas import LighthouseScore


def score_lighthouse(
    site_url: str | None = None,
    html_path: Path | None = None,
    build_succeeded: bool = True,
) -> LighthouseScore:
    """Measure actual Lighthouse scores for a locally served site.

    If Lighthouse is unavailable in the environment or the build failed,
    explicitly marks the metric as unavailable without fabricating scores.
    """
    if not build_succeeded:
        return LighthouseScore(
            available=False,
            reason_unavailable="Build failed; cannot audit unbuilt website.",
        )

    if not site_url and not html_path:
        return LighthouseScore(
            available=False,
            reason_unavailable="No preview URL or HTML path provided for audit.",
        )

    lighthouse_bin = shutil.which("lighthouse")
    if not lighthouse_bin:
        return LighthouseScore(
            available=False,
            reason_unavailable="Lighthouse CLI binary not found in environment.",
        )

    target = site_url or str(html_path)
    try:
        cmd = [
            lighthouse_bin,
            target,
            "--output=json",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
            "--quiet",
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode != 0:
            return LighthouseScore(
                available=False,
                reason_unavailable=(
                    f"Lighthouse execution exited with code "
                    f"{proc.returncode}: {proc.stderr[:100]}"
                ),
            )

        data = json.loads(proc.stdout)
        categories = data.get("categories", {})

        def _get_cat(cat_name: str) -> float | None:
            if cat_name in categories and "score" in categories[cat_name]:
                val = categories[cat_name]["score"]
                return float(val) if val is not None else None
            return None

        return LighthouseScore(
            available=True,
            performance=_get_cat("performance"),
            accessibility=_get_cat("accessibility"),
            best_practices=_get_cat("best-practices"),
            seo=_get_cat("seo"),
        )
    except subprocess.TimeoutExpired:
        return LighthouseScore(
            available=False,
            reason_unavailable="Lighthouse audit timed out after 60 seconds.",
        )
    except Exception as exc:
        return LighthouseScore(
            available=False,
            reason_unavailable=f"Lighthouse execution error: {exc}",
        )
