"""Unit tests for FileEditPolicy server-side security and schema checks."""

import json

import pytest

from agency.application.agents.file_edit_policy import (
    EditLimitExceededError,
    FileEditPolicy,
    ForbiddenFileEditError,
    InvalidFileContentError,
)
from agency.application.agents.models import (
    BuilderContext,
    BuilderRawEdit,
    EditCategory,
)
from agency.domain.entities.design_tokens import DesignTokens
from agency.domain.entities.qa_report import QACheck, QAReport
from agency.domain.entities.spec import AcceptanceCriterion, Spec, SpecPage, SpecSection


def _create_mock_context(
    allow_component_escalation: bool = False,
    qa_passed: bool = True,
) -> BuilderContext:
    spec = Spec(
        project_id="test-proj",
        title="Test Portfolio",
        pages=[
            SpecPage(
                slug="home",
                title="Home",
                sections=[
                    SpecSection(
                        id="hero",
                        title="Hero",
                        description="Hero section",
                    )
                ],
            )
        ],
        technical_constraints=["Astro 4", "Tailwind CSS"],
        acceptance_criteria=[
            AcceptanceCriterion(id="ac-1", description="Hero renders properly")
        ],
    )
    tokens = DesignTokens(
        font_family="Poppins",
        colors={
            "brand_primary": "#9C4126",
            "bg_base": "#FFFFFF",
            "text_primary": "#111111",
        },
        spacing_scale={"space-1": 4.0},
        border_radius_scale={"radius-sm": 2.0},
    )
    qa_report = QAReport(
        checks=[
            QACheck(
                name="contrast_check",
                passed=qa_passed,
                details="Contrast check" if qa_passed else "Low contrast",
            )
        ]
    )
    return BuilderContext(
        spec=spec,
        tokens=tokens,
        pages=[],
        qa_report=qa_report,
        allow_component_escalation=allow_component_escalation,
    )


def test_file_edit_policy_valid_content_edit() -> None:
    """Valid edit to site.json is approved with CONTENT category."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    valid_site_json = json.dumps(
        {
            "clientName": "Alice",
            "siteTitle": "Alice — Portfolio",
            "nav": [{"label": "Home", "href": "/"}],
        }
    )

    raw_edits = [
        BuilderRawEdit(
            path="src/content/site.json",
            content=valid_site_json,
            reason="Update client title",
        )
    ]

    proposals = policy.validate_edits(raw_edits, context)
    assert len(proposals) == 1
    assert proposals[0].path == "src/content/site.json"
    assert proposals[0].category == EditCategory.CONTENT


def test_file_edit_policy_rejects_absolute_path() -> None:
    """Absolute paths are rejected by policy."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    raw_edits = [
        BuilderRawEdit(
            path="/etc/passwd",
            content="root:x:0:0::/root:/bin/bash",
            reason="Malicious edit",
        )
    ]
    with pytest.raises(ForbiddenFileEditError, match="Absolute file path"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_traversal() -> None:
    """Path traversal sequences (..) are rejected."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    raw_edits = [
        BuilderRawEdit(
            path="src/content/../../.env",
            content="SECRET=leak",
            reason="Escape directory",
        )
    ]
    with pytest.raises(ForbiddenFileEditError, match="Path traversal"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_backslashes() -> None:
    """Windows backslash path separators are rejected."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    raw_edits = [
        BuilderRawEdit(
            path="src\\content\\site.json",
            content="{}",
            reason="Backslash path",
        )
    ]
    with pytest.raises(ForbiddenFileEditError, match="Invalid or escaped path"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_unauthorized_target() -> None:
    """Editing files outside the allowlist (e.g., package.json) is rejected."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    raw_edits = [
        BuilderRawEdit(
            path="package.json",
            content='{"name": "malicious"}',
            reason="Install package",
        )
    ]
    with pytest.raises(
        ForbiddenFileEditError, match="not in the allowed modification list"
    ):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_duplicate_paths() -> None:
    """Multiple proposals editing the same file in one batch are rejected."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    valid_json = json.dumps(
        {
            "clientName": "Alice",
            "siteTitle": "Alice",
            "nav": [],
        }
    )
    raw_edits = [
        BuilderRawEdit(
            path="src/content/site.json", content=valid_json, reason="Edit 1"
        ),
        BuilderRawEdit(
            path="src/content/site.json", content=valid_json, reason="Edit 2"
        ),
    ]
    with pytest.raises(ForbiddenFileEditError, match="Duplicate edit path"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_excessive_edits() -> None:
    """Proposals exceeding max_edits limit are rejected."""
    policy = FileEditPolicy(max_edits=2)
    context = _create_mock_context()

    raw_edits = [
        BuilderRawEdit(
            path=f"src/content/file_{i}.json", content="{}", reason=f"Edit {i}"
        )
        for i in range(5)
    ]
    with pytest.raises(EditLimitExceededError, match="exceeding limit"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_oversized_file() -> None:
    """Files exceeding size limit are rejected."""
    policy = FileEditPolicy(max_file_size_bytes=100)
    context = _create_mock_context()

    raw_edits = [
        BuilderRawEdit(
            path="src/content/site.json",
            content="A" * 500,
            reason="Oversized",
        )
    ]
    with pytest.raises(EditLimitExceededError, match="exceeds limit"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_invalid_json() -> None:
    """JSON files with invalid syntax raise InvalidFileContentError."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    raw_edits = [
        BuilderRawEdit(
            path="src/content/site.json",
            content="{ invalid_json ... }",
            reason="Syntax error",
        )
    ]
    with pytest.raises(InvalidFileContentError, match="Invalid JSON syntax"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_missing_required_keys_in_site_json() -> None:
    """Missing required keys in site.json raises InvalidFileContentError."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    incomplete_json = json.dumps({"clientName": "Bob"})  # missing siteTitle and nav
    raw_edits = [
        BuilderRawEdit(
            path="src/content/site.json",
            content=incomplete_json,
            reason="Incomplete",
        )
    ]
    with pytest.raises(InvalidFileContentError, match="Missing required field"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_duplicate_project_slugs() -> None:
    """Duplicate project slugs in projects.json raise InvalidFileContentError."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    duplicate_projects = json.dumps(
        {
            "projects": [
                {"slug": "project-one", "title": "One"},
                {"slug": "project-one", "title": "Duplicate One"},
            ]
        }
    )
    raw_edits = [
        BuilderRawEdit(
            path="src/content/projects.json",
            content=duplicate_projects,
            reason="Duplicate slugs",
        )
    ]
    with pytest.raises(InvalidFileContentError, match="Duplicate project slug"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_rejects_script_injection_in_css() -> None:
    """Malicious scripts embedded in tokens.css are rejected."""
    policy = FileEditPolicy()
    context = _create_mock_context()

    bad_css = ":root { --color: red; } </style><script>alert('pwned')</script>"
    raw_edits = [
        BuilderRawEdit(
            path="src/styles/tokens.css",
            content=bad_css,
            reason="Inject script",
        )
    ]
    with pytest.raises(InvalidFileContentError, match="Malicious script injection"):
        policy.validate_edits(raw_edits, context)


def test_file_edit_policy_component_escalation_rules() -> None:
    """Component edits require both server escalation authorization and QA failure."""
    policy = FileEditPolicy()

    # Case 1: allow_component_escalation=False -> Prohibited
    ctx_no_esc = _create_mock_context(allow_component_escalation=False, qa_passed=False)
    raw = [
        BuilderRawEdit(
            path="src/components/Header.astro",
            content="--- --- <header>Custom</header>",
            reason="Fix layout",
            qa_issue_addressed="contrast_check",
        )
    ]
    with pytest.raises(
        ForbiddenFileEditError, match="prohibited without explicit escalation"
    ):
        policy.validate_edits(raw, ctx_no_esc)

    # Case 2: allow_component_escalation=True, but QA passed -> Prohibited (no defect)
    ctx_qa_passed = _create_mock_context(
        allow_component_escalation=True, qa_passed=True
    )
    with pytest.raises(
        ForbiddenFileEditError, match="not justified because all QA checks passed"
    ):
        policy.validate_edits(raw, ctx_qa_passed)

    # Case 3: allow_component_escalation=True AND QA failed -> Permitted!
    ctx_allowed = _create_mock_context(allow_component_escalation=True, qa_passed=False)
    proposals = policy.validate_edits(raw, ctx_allowed)
    assert len(proposals) == 1
    assert proposals[0].category == EditCategory.COMPONENT_ESCALATION
    assert proposals[0].path == "src/components/Header.astro"
