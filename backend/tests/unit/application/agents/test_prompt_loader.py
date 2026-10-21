"""Unit tests for versioned PromptLoader."""

from pathlib import Path

import pytest

from agency.application.agents.prompt_loader import (
    PromptLoader,
    PromptNotFoundError,
)


def test_prompt_loader_loads_v1_prompts() -> None:
    """PromptLoader successfully resolves and loads v1 system prompts."""
    loader = PromptLoader()

    pm_prompt = loader.load_prompt("pm", version="v1")
    assert "PM Agent System Prompt" in pm_prompt
    assert len(pm_prompt) > 100

    designer_prompt = loader.load_prompt("designer", version="v1")
    assert "Designer Agent System Prompt" in designer_prompt
    assert "Poppins" in designer_prompt

    builder_prompt = loader.load_prompt("builder", version="v1")
    assert "Builder Agent System Prompt" in builder_prompt
    assert "Strict Target Allowlist" in builder_prompt


def test_prompt_loader_caching() -> None:
    """PromptLoader returns cached prompt content on subsequent calls."""
    loader = PromptLoader()
    first = loader.load_prompt("pm", version="v1")
    second = loader.load_prompt("pm", version="v1")
    assert first is second


def test_prompt_loader_missing_version_raises_error() -> None:
    """Requesting an unreleased prompt version raises PromptNotFoundError."""
    loader = PromptLoader()
    with pytest.raises(PromptNotFoundError) as exc_info:
        loader.load_prompt("pm", version="v999")

    assert exc_info.value.agent_name == "pm"
    assert exc_info.value.version == "v999"


def test_prompt_loader_missing_agent_raises_error() -> None:
    """Requesting a prompt for an unknown agent raises PromptNotFoundError."""
    loader = PromptLoader()
    with pytest.raises(PromptNotFoundError):
        loader.load_prompt("nonexistent_agent", version="v1")


def test_prompt_loader_custom_base_dir(tmp_path: Path) -> None:
    """PromptLoader honors explicitly injected prompt directory."""
    v2_dir = tmp_path / "v2"
    v2_dir.mkdir(parents=True)
    custom_prompt_file = v2_dir / "tester_system.md"
    custom_prompt_file.write_text("Custom Tester Prompt", encoding="utf-8")

    loader = PromptLoader(base_dir=tmp_path)
    loaded = loader.load_prompt("tester", version="v2")
    assert loaded == "Custom Tester Prompt"
