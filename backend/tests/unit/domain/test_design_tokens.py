"""Unit tests for DesignTokens value object."""

import math

import pytest
from pydantic import ValidationError

from agency.domain.entities.design_tokens import DesignTokens


def mutate_attr(obj: object, name: str, value: object) -> None:
    """Helper to attempt dynamic mutation on frozen objects."""
    setattr(obj, name, value)


def test_valid_design_tokens() -> None:
    """Test valid DesignTokens creation."""
    tokens = DesignTokens(
        font_family="Poppins",
        colors={
            "primary": "#3B82F6",
            "background": "#FFFFFF",
            "text": "#111827",
        },
        spacing_scale={
            "xs": 4.0,
            "sm": 8.0,
            "md": 16.0,
            "lg": 24.0,
        },
        border_radius_scale={
            "none": 0.001,
            "sm": 2.0,
            "md": 4.0,
            "lg": 8.0,
        },
    )
    assert tokens.font_family == "Poppins"
    assert tokens.colors["primary"] == "#3B82F6"
    assert tokens.spacing_scale["md"] == 16.0
    assert tokens.border_radius_scale["lg"] == 8.0


@pytest.mark.parametrize(
    "invalid_hex",
    ["red", "#12", "#12345", "#GGGGGG", "rgb(0,0,0)", ""],
)
def test_invalid_hex_colors_rejected(invalid_hex: str) -> None:
    """Test that invalid hex color formats are rejected."""
    with pytest.raises(ValidationError):
        DesignTokens(
            font_family="Poppins",
            colors={"primary": invalid_hex},
            spacing_scale={"sm": 4.0},
            border_radius_scale={"sm": 2.0},
        )


@pytest.mark.parametrize("invalid_spacing", [-4.0, 0.0, math.nan, math.inf])
def test_invalid_spacing_scale_rejected(invalid_spacing: float) -> None:
    """Test that non-positive or non-finite spacing values are rejected."""
    with pytest.raises(ValidationError):
        DesignTokens(
            font_family="Poppins",
            colors={"primary": "#FFFFFF"},
            spacing_scale={"sm": invalid_spacing},
            border_radius_scale={"sm": 2.0},
        )


@pytest.mark.parametrize("invalid_radius", [-2.0, 0.0, math.nan, math.inf])
def test_invalid_border_radius_scale_rejected(invalid_radius: float) -> None:
    """Test that non-positive or non-finite radius values are rejected."""
    with pytest.raises(ValidationError):
        DesignTokens(
            font_family="Poppins",
            colors={"primary": "#FFFFFF"},
            spacing_scale={"sm": 4.0},
            border_radius_scale={"sm": invalid_radius},
        )


def test_duplicate_scale_values_rejected() -> None:
    """Test that duplicate values in scale steps are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        DesignTokens(
            font_family="Poppins",
            colors={"primary": "#FFFFFF"},
            spacing_scale={"sm": 4.0, "md": 4.0},
            border_radius_scale={"sm": 2.0},
        )
    assert "Duplicate spacing scale value" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        DesignTokens(
            font_family="Poppins",
            colors={"primary": "#FFFFFF"},
            spacing_scale={"sm": 4.0},
            border_radius_scale={"sm": 2.0, "md": 2.0},
        )
    assert "Duplicate border radius scale value" in str(exc_info.value)


def test_design_tokens_immutable() -> None:
    """Test that DesignTokens cannot be modified after instantiation."""
    tokens = DesignTokens(
        font_family="Poppins",
        colors={"primary": "#FFFFFF"},
        spacing_scale={"sm": 4.0},
        border_radius_scale={"sm": 2.0},
    )
    with pytest.raises(ValidationError):
        mutate_attr(tokens, "font_family", "Inter")
