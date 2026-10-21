"""Deterministic, versioned prompt loader for application agents."""

import os
from pathlib import Path

from agency.application.errors import ApplicationError


class PromptNotFoundError(ApplicationError):
    """Raised when an expected versioned prompt template is missing."""

    def __init__(self, agent_name: str, version: str, path: Path) -> None:
        self.agent_name = agent_name
        self.version = version
        self.path = path
        super().__init__(
            f"Prompt file for agent '{agent_name}' (version '{version}') "
            f"not found at '{path}'."
        )


class PromptLoader:
    """Loads and caches versioned system prompt markdown documents."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        if base_dir is not None:
            self.base_dir = Path(base_dir).resolve()
        elif "AGENCY_PROMPTS_DIR" in os.environ:
            self.base_dir = Path(os.environ["AGENCY_PROMPTS_DIR"]).resolve()
        else:
            # Look up from prompt_loader.py -> repo root
            candidate = Path(__file__).resolve().parents[5] / "agents" / "prompts"
            if candidate.is_dir():
                self.base_dir = candidate
            else:
                self.base_dir = Path.cwd() / "agents" / "prompts"

        self._cache: dict[tuple[str, str], str] = {}

    def load_prompt(self, agent_name: str, version: str = "v1") -> str:
        """Load the system prompt markdown file for a specific agent and version."""
        cache_key = (agent_name.strip().lower(), version.strip().lower())
        if cache_key in self._cache:
            return self._cache[cache_key]

        target_file = self.base_dir / cache_key[1] / f"{cache_key[0]}_system.md"
        if not target_file.is_file():
            raise PromptNotFoundError(
                agent_name=agent_name,
                version=version,
                path=target_file,
            )

        content = target_file.read_text(encoding="utf-8").strip()
        self._cache[cache_key] = content
        return content
