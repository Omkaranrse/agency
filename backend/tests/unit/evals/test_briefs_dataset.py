"""Unit tests validating the evaluation dataset briefs against domain models."""

import json
from pathlib import Path

from agency.domain.entities.brief import Brief

BRIEFS_DIR = Path(__file__).parents[3] / "evals" / "briefs"

EXPECTED_BRIEFS = [
    "consultant.json",
    "creative_agency.json",
    "designer.json",
    "developer.json",
    "freelancer.json",
    "local_services.json",
    "musician.json",
    "personal_brand.json",
    "photographer.json",
    "small_business.json",
    "student.json",
    "writer.json",
]


def test_evaluation_dataset_contains_exactly_twelve_briefs() -> None:
    """The dataset contains the required 12 representative website briefs."""
    assert BRIEFS_DIR.is_dir(), f"Briefs directory not found: {BRIEFS_DIR}"

    json_files = sorted([f.name for f in BRIEFS_DIR.glob("*.json")])
    assert json_files == EXPECTED_BRIEFS, f"Dataset files mismatch: {json_files}"
    assert len(json_files) == 12


def test_every_brief_conforms_to_domain_schema() -> None:
    """Every brief file parses and validates strictly against domain Brief entity."""
    for filename in EXPECTED_BRIEFS:
        file_path = BRIEFS_DIR / filename
        raw = json.loads(file_path.read_text(encoding="utf-8"))

        brief = Brief.model_validate(raw)
        assert len(brief.client_name) > 0
        assert len(brief.site_type) > 0
        assert len(brief.tone) > 0
        assert len(brief.content_notes) >= 30
        assert len(brief.pages) >= 4

        # Page names must be unique
        assert len(brief.pages) == len(set(p.lower() for p in brief.pages))

        # Links must be valid URLs
        for link in brief.links:
            assert str(link).startswith("http://") or str(link).startswith("https://")
