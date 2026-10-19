"""Visual Design Tokens domain entity."""

import math
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class DesignTokens(BaseModel):
    """Represents an approved visual design system.

    Immutable value object specifying colors, typography, spacing, and radius.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    font_family: str = Field(min_length=1, max_length=100)
    colors: dict[str, str] = Field(min_length=1)
    spacing_scale: dict[str, float] = Field(min_length=1)
    border_radius_scale: dict[str, float] = Field(min_length=1)

    @field_validator("font_family", mode="before")
    @classmethod
    def _strip_font_family(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Font family cannot be empty or whitespace only.")
            return stripped
        return value

    @field_validator("colors")
    @classmethod
    def _validate_colors(cls, colors: dict[str, str]) -> dict[str, str]:
        if not colors:
            raise ValueError("Colors dictionary must contain at least one token.")

        validated: dict[str, str] = {}
        for raw_name, raw_value in colors.items():
            name = raw_name.strip()
            if not name:
                raise ValueError("Color token name cannot be empty.")
            if not isinstance(raw_value, str):
                raise ValueError(f"Color token '{name}' value must be a hex string.")
            hex_val = raw_value.strip()
            if not HEX_COLOR_PATTERN.match(hex_val):
                raise ValueError(
                    f"Invalid hexadecimal color value '{raw_value}' for token '{name}'."
                )
            validated[name] = hex_val
        return validated

    @field_validator("spacing_scale")
    @classmethod
    def _validate_spacing(cls, scale: dict[str, float]) -> dict[str, float]:
        if not scale:
            raise ValueError("Spacing scale must contain at least one step.")

        validated: dict[str, float] = {}
        seen_values: set[float] = set()
        for raw_name, value in scale.items():
            name = raw_name.strip()
            if not name:
                raise ValueError("Spacing step name cannot be empty.")
            if not isinstance(value, int | float):
                raise ValueError(f"Spacing value for '{name}' must be a number.")
            float_val = float(value)
            if math.isnan(float_val) or math.isinf(float_val):
                raise ValueError(f"Spacing value for '{name}' must be finite.")
            if float_val <= 0:
                raise ValueError(
                    f"Spacing value for '{name}' must be positive (> 0), "
                    f"got {float_val}."
                )
            if float_val in seen_values:
                raise ValueError(
                    f"Duplicate spacing scale value {float_val} for step '{name}'."
                )
            seen_values.add(float_val)
            validated[name] = float_val
        return validated

    @field_validator("border_radius_scale")
    @classmethod
    def _validate_border_radius(cls, scale: dict[str, float]) -> dict[str, float]:
        if not scale:
            raise ValueError("Border radius scale must contain at least one step.")

        validated: dict[str, float] = {}
        seen_values: set[float] = set()
        for raw_name, value in scale.items():
            name = raw_name.strip()
            if not name:
                raise ValueError("Border radius step name cannot be empty.")
            if not isinstance(value, int | float):
                raise ValueError(f"Border radius value for '{name}' must be a number.")
            float_val = float(value)
            if math.isnan(float_val) or math.isinf(float_val):
                raise ValueError(f"Border radius value for '{name}' must be finite.")
            if float_val <= 0:
                raise ValueError(
                    f"Border radius value for '{name}' must be positive (> 0), "
                    f"got {float_val}."
                )
            if float_val in seen_values:
                raise ValueError(
                    f"Duplicate border radius scale value {float_val} for "
                    f"step '{name}'."
                )
            seen_values.add(float_val)
            validated[name] = float_val
        return validated
