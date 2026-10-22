"""Validated settings for LLM providers, model routing, and token budgets."""

import os
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from agency.infrastructure.llm.models import AgentRole

ALLOWED_PROVIDERS = {"gemini", "ollama", "fake", "groq"}


def _load_env_file() -> None:
    """Load key-value pairs from .env file into os.environ if not present."""
    env_paths = [
        Path(".env"),
        Path("../.env"),
        Path(__file__).resolve().parents[5] / ".env",
    ]
    for env_path in env_paths:
        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
                break
            except Exception:
                pass


_load_env_file()


def _default_fallback_provider_by_role() -> dict[str, str | None]:
    return {
        AgentRole.PM.value: "ollama",
        AgentRole.DESIGNER.value: "ollama",
        AgentRole.BUILDER.value: "ollama",
        AgentRole.REVIEWER.value: "ollama",
        AgentRole.SUMMARIZER.value: "ollama",
    }


class LLMSettings(BaseModel):
    """Configuration governing model selection, fallback, retries, and token budgets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Provider credentials & endpoints
    gemini_api_key: SecretStr | None = Field(default=None)
    groq_api_key: SecretStr | None = Field(default=None)
    ollama_base_url: str = Field(default="http://localhost:11434")

    # Gemini model mappings per agent role
    gemini_model_pm: str = Field(default="gemini-1.5-pro")
    gemini_model_designer: str = Field(default="gemini-1.5-pro")
    gemini_model_builder: str = Field(default="gemini-1.5-pro")
    gemini_model_reviewer: str = Field(default="gemini-1.5-flash")
    gemini_model_summarizer: str = Field(default="gemini-1.5-flash")

    # Groq model mappings per agent role
    groq_model_pm: str = Field(default="llama-3.3-70b-versatile")
    groq_model_designer: str = Field(default="llama-3.3-70b-versatile")
    groq_model_builder: str = Field(default="llama-3.3-70b-versatile")
    groq_model_reviewer: str = Field(default="llama-3.1-8b-instant")
    groq_model_summarizer: str = Field(default="llama-3.1-8b-instant")

    # Ollama model mappings per agent role
    ollama_model_pm: str = Field(default="llama3.2")
    ollama_model_designer: str = Field(default="llama3.2")
    ollama_model_builder: str = Field(default="qwen2.5-coder")
    ollama_model_reviewer: str = Field(default="llama3.2")
    ollama_model_summarizer: str = Field(default="llama3.2")

    # Provider routing per agent role
    primary_provider_by_role: dict[str, str] = Field(
        default_factory=lambda: {
            AgentRole.PM.value: "gemini",
            AgentRole.DESIGNER.value: "gemini",
            AgentRole.BUILDER.value: "gemini",
            AgentRole.REVIEWER.value: "gemini",
            AgentRole.SUMMARIZER.value: "gemini",
        }
    )
    fallback_provider_by_role: dict[str, str | None] = Field(
        default_factory=_default_fallback_provider_by_role
    )

    # Timeouts and generation bounds
    request_timeout_seconds: float = Field(default=60.0, gt=0.0, le=600.0)
    max_output_tokens: int = Field(default=4096, gt=0, le=32_768)

    # Retry and repair bounds
    max_repair_retries: int = Field(
        default=2, ge=0, le=2, description="Max schema repair retries (capped at 2)."
    )
    max_transient_retries: int = Field(default=3, ge=0, le=10)
    initial_backoff_seconds: float = Field(default=1.0, gt=0.0, le=60.0)
    max_backoff_seconds: float = Field(default=30.0, gt=0.0, le=300.0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    overall_retry_deadline_seconds: float = Field(default=120.0, gt=0.0, le=600.0)

    # Token budget defaults
    default_run_token_budget: int = Field(default=200_000, gt=0)
    reserved_output_tokens: int = Field(default=2_000, gt=0)

    # Logging
    log_usage_enabled: bool = Field(default=True)

    @classmethod
    def from_env(cls, **overrides: object) -> "LLMSettings":
        """Instantiate settings reading credentials and options from environment."""
        env_gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        env_groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        env_ollama_url = os.environ.get("OLLAMA_BASE_URL", "").strip()
        primary_provider = os.environ.get("PRIMARY_LLM_PROVIDER", "").strip().lower()

        kwargs: dict[str, object] = {}
        if env_gemini_key:
            kwargs["gemini_api_key"] = SecretStr(env_gemini_key)
        if env_groq_key:
            kwargs["groq_api_key"] = SecretStr(env_groq_key)
        if env_ollama_url:
            kwargs["ollama_base_url"] = env_ollama_url

        if primary_provider == "groq" or (env_groq_key and not env_gemini_key):
            kwargs["primary_provider_by_role"] = {
                role.value: "groq" for role in AgentRole
            }

        kwargs.update(overrides)
        return cls(**kwargs)  # type: ignore[arg-type]

    @model_validator(mode="after")
    def _validate_routing_providers(self) -> Self:
        """Validate that all routing mappings use recognized providers."""
        for role, provider in self.primary_provider_by_role.items():
            if provider not in ALLOWED_PROVIDERS:
                raise ValueError(
                    f"Invalid primary provider '{provider}' for role '{role}'. "
                    f"Allowed providers: {', '.join(sorted(ALLOWED_PROVIDERS))}."
                )
        for role, fb_provider in self.fallback_provider_by_role.items():
            if fb_provider is not None and fb_provider not in ALLOWED_PROVIDERS:
                raise ValueError(
                    f"Invalid fallback provider '{fb_provider}' for role '{role}'. "
                    f"Allowed providers: {', '.join(sorted(ALLOWED_PROVIDERS))}."
                )
        return self

    def get_primary_provider(self, role: str) -> str:
        """Retrieve the configured primary provider for a role."""
        return self.primary_provider_by_role.get(role, "gemini")

    def get_fallback_provider(self, role: str) -> str | None:
        """Retrieve the configured fallback provider for a role."""
        return self.fallback_provider_by_role.get(role)

    def get_gemini_model(self, role: str) -> str:
        """Retrieve the Gemini model name designated for a role."""
        match role:
            case AgentRole.PM.value:
                return self.gemini_model_pm
            case AgentRole.DESIGNER.value:
                return self.gemini_model_designer
            case AgentRole.BUILDER.value:
                return self.gemini_model_builder
            case AgentRole.REVIEWER.value:
                return self.gemini_model_reviewer
            case AgentRole.SUMMARIZER.value:
                return self.gemini_model_summarizer
            case _:
                return self.gemini_model_pm

    def get_ollama_model(self, role: str) -> str:
        """Retrieve the Ollama model name designated for a role."""
        match role:
            case AgentRole.PM.value:
                return self.ollama_model_pm
            case AgentRole.DESIGNER.value:
                return self.ollama_model_designer
            case AgentRole.BUILDER.value:
                return self.ollama_model_builder
            case AgentRole.REVIEWER.value:
                return self.ollama_model_reviewer
            case AgentRole.SUMMARIZER.value:
                return self.ollama_model_summarizer
            case _:
                return self.ollama_model_pm

    def get_groq_model(self, role: str) -> str:
        """Retrieve the Groq model name designated for a role."""
        match role:
            case AgentRole.PM.value:
                return self.groq_model_pm
            case AgentRole.DESIGNER.value:
                return self.groq_model_designer
            case AgentRole.BUILDER.value:
                return self.groq_model_builder
            case AgentRole.REVIEWER.value:
                return self.groq_model_reviewer
            case AgentRole.SUMMARIZER.value:
                return self.groq_model_summarizer
            case _:
                return self.groq_model_pm
