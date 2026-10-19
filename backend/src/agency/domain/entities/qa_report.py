"""Quality Assurance Report domain entity."""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class QACheck(BaseModel):
    """An individual quality assurance check result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    passed: bool
    details: str = Field(default="", max_length=10_000)
    status: str = Field(default="passed")
    error_code: str | None = Field(default=None)
    page: str | None = Field(default=None)
    severity: str | None = Field(default=None)
    diagnostic_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("QA check name cannot be empty or whitespace only.")
            return stripped
        return value


class QAReport(BaseModel):
    """Represents automated quality assurance results.

    Calculation policy:
    An overall_passed status of True is only valid if:
    1. The checks list is nonempty (an empty check list is rejected).
    2. Every individual check in the report passed (all(check.passed)).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    checks: list[QACheck] = Field(min_length=1, max_length=100)
    overall_passed: bool = Field(default=False)

    @field_validator("checks")
    @classmethod
    def _validate_checks(cls, checks: list[QACheck]) -> list[QACheck]:
        if not checks:
            raise ValueError(
                "A QA report must contain at least one check; "
                "empty checks cannot verify quality."
            )

        seen_names: set[str] = set()
        for check in checks:
            normalized = check.name.lower()
            if normalized in seen_names:
                raise ValueError(f"Duplicate QA check name detected: '{check.name}'.")
            seen_names.add(normalized)
        return checks

    @model_validator(mode="before")
    @classmethod
    def _derive_or_verify_overall_passed(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_checks = data.get("checks", [])
            if isinstance(raw_checks, list) and raw_checks:
                all_passed = all(
                    bool(
                        c.get("passed")
                        if isinstance(c, dict)
                        else getattr(c, "passed", False)
                    )
                    for c in raw_checks
                )
                provided = data.get("overall_passed")
                if provided is True and not all_passed:
                    raise ValueError(
                        "Cannot mark QAReport as overall_passed=True when "
                        "one or more checks failed."
                    )
                if "overall_passed" not in data:
                    data["overall_passed"] = all_passed
        return data

    @model_validator(mode="after")
    def _enforce_overall_passed_invariant(self) -> Self:
        all_passed = bool(self.checks and all(c.passed for c in self.checks))
        if self.overall_passed and not all_passed:
            raise ValueError(
                "Cannot mark QAReport as overall_passed=True when "
                "one or more checks failed."
            )
        return self
