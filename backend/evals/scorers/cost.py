"""Cost and token usage scorer distinguishing actual and estimated costs."""

from evals.schemas import CostScore

# Standard model rate cards per 1,000,000 tokens (USD)
MODEL_RATES = {
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "default": {"input": 1.25, "output": 5.00},
}


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "default",
) -> float:
    """Calculate estimated cost in USD based on standard rate cards."""
    rates = MODEL_RATES.get(model, MODEL_RATES["default"])
    cost = (input_tokens / 1_000_000.0) * rates["input"] + (
        output_tokens / 1_000_000.0
    ) * rates["output"]
    return round(cost, 6)


def score_cost(
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    provider_cost_usd: float | None = None,
    is_fake_mode: bool = False,
    model: str = "default",
    build_successful: bool = True,
) -> CostScore:
    """Evaluate token usage and financial cost, distinguishing actual from estimates."""
    if is_fake_mode:
        # In fake mode, actual cost is strictly 0.0 (no real provider billing)
        return CostScore(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            actual_cost_usd=0.0,
            estimated_cost_usd=0.0,
            cost_per_successful_build=0.0,
        )

    estimated = estimate_cost(input_tokens, output_tokens, model=model)
    actual = provider_cost_usd if provider_cost_usd is not None else None
    cost_for_build = actual if actual is not None else estimated
    cost_per_build = cost_for_build if build_successful else 0.0

    return CostScore(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        actual_cost_usd=actual,
        estimated_cost_usd=estimated,
        cost_per_successful_build=cost_per_build,
    )
