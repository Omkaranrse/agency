"""Role-based LLM router directing tasks to primary and fallback providers."""

import logging
from typing import TypeVar, cast

from pydantic import BaseModel

from agency.application.ports.llm import LLMPort
from agency.infrastructure.llm.errors import (
    FallbackExhaustedError,
    InvalidRoleError,
    ModelTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
from agency.infrastructure.llm.gemini_adapter import GeminiAdapter
from agency.infrastructure.llm.models import (
    AgentRole,
    GenerationRequest,
    GenerationResult,
)
from agency.infrastructure.llm.ollama_adapter import OllamaAdapter
from agency.infrastructure.llm.settings import LLMSettings
from agency.infrastructure.llm.token_budget import TokenBudgetManager

T = TypeVar("T", bound=BaseModel)
usage_logger = logging.getLogger("agency.infrastructure.llm.usage")


class RoutingLLM(LLMPort):
    """Dynamic LLM router enforcing role-to-model mappings, fallback, and budgets."""

    def __init__(
        self,
        providers: dict[str, LLMPort] | None = None,
        settings: LLMSettings | None = None,
        budget_manager: TokenBudgetManager | None = None,
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self.budget_manager = budget_manager or TokenBudgetManager(
            default_budget=self.settings.default_run_token_budget,
            default_reservation=self.settings.reserved_output_tokens,
        )
        if providers is not None:
            self.providers = providers
        else:
            self.providers = {
                "gemini": GeminiAdapter(settings=self.settings),
                "ollama": OllamaAdapter(settings=self.settings),
            }

    def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        role: str,
        *,
        run_id: str | None = None,
        correlation_id: str | None = None,
        max_output_tokens: int | None = None,
        timeout: float | None = None,
    ) -> T:
        """Route structured generation request to configured provider for role."""
        req = GenerationRequest[T](
            schema_type=schema,
            prompt=prompt,
            role=role,
            run_id=run_id or "default",
            correlation_id=correlation_id,
            max_output_tokens=max_output_tokens,
            timeout=timeout,
        )
        result = self.generate(req)
        return result.data

    def generate(self, request: GenerationRequest[T]) -> GenerationResult[T]:
        """Execute structured generation with bounded fallback."""
        role_str = (
            request.role.value
            if isinstance(request.role, AgentRole)
            else str(request.role)
        )
        if not AgentRole.is_valid_role(role_str):
            raise InvalidRoleError(role_str)

        primary_provider = self.settings.get_primary_provider(role_str)
        fallback_provider = self.settings.get_fallback_provider(role_str)

        if primary_provider not in self.providers:
            raise ProviderUnavailableError(
                primary_provider,
                f"Configured primary provider '{primary_provider}' is not registered.",
            )

        reservation_amount = (
            request.max_output_tokens or self.settings.reserved_output_tokens
        )
        reservation = self.budget_manager.reserve(
            run_id=request.run_id, amount=reservation_amount
        )

        try:
            # 1. Attempt primary provider
            res = cast(
                GenerationResult[T], self.providers[primary_provider].generate(request)
            )
            self.budget_manager.reconcile(
                reservation=reservation,
                actual_usage=res.usage,
                is_repair=res.repair_attempts > 0,
                is_fallback=False,
            )
            return res

        except (
            RateLimitError,
            ProviderUnavailableError,
            ModelTimeoutError,
        ) as primary_exc:
            # Check if fallback is eligible and configured
            can_fallback = (
                fallback_provider is not None
                and fallback_provider != primary_provider
                and fallback_provider in self.providers
            )

            if not can_fallback or fallback_provider is None:
                self.budget_manager.reconcile(
                    reservation=reservation,
                    actual_usage=None,
                    is_fallback=False,
                )
                raise

            fb_name: str = fallback_provider
            # Observable and explicit fallback logging
            fallback_reason = f"{type(primary_exc).__name__}: {primary_exc}"
            if self.settings.log_usage_enabled:
                usage_logger.warning(
                    "Primary provider transient failure; switching to fallback",
                    extra={
                        "run_id": request.run_id,
                        "correlation_id": request.correlation_id,
                        "agent_role": role_str,
                        "primary_provider": primary_provider,
                        "fallback_provider": fb_name,
                        "fallback_reason": fallback_reason,
                    },
                )

            # 2. Attempt fallback provider
            try:
                fallback_adapter = self.providers[fb_name]
                fallback_res = cast(
                    GenerationResult[T], fallback_adapter.generate(request)
                )
                self.budget_manager.reconcile(
                    reservation=reservation,
                    actual_usage=fallback_res.usage,
                    is_repair=fallback_res.repair_attempts > 0,
                    is_fallback=True,
                )
                return GenerationResult[T](
                    data=fallback_res.data,
                    provider=fallback_res.provider,
                    model=fallback_res.model,
                    usage=fallback_res.usage,
                    repair_attempts=fallback_res.repair_attempts,
                    correlation_id=fallback_res.correlation_id,
                    fallback_occurred=True,
                    fallback_reason=fallback_reason,
                )
            except Exception as fallback_exc:
                self.budget_manager.reconcile(
                    reservation=reservation,
                    actual_usage=None,
                    is_fallback=True,
                )
                raise FallbackExhaustedError(
                    primary_provider=primary_provider,
                    fallback_provider=fb_name,
                    message=(
                        f"Primary '{primary_provider}' failed ({primary_exc}); "
                        f"fallback '{fb_name}' failed ({fallback_exc})."
                    ),
                ) from fallback_exc

        except Exception:
            # Non-transient errors (auth, schema, budget) do not trigger fallback
            self.budget_manager.reconcile(
                reservation=reservation,
                actual_usage=None,
                is_fallback=False,
            )
            raise
