"""Smoke test verifying import of the agency package."""

import agency


def test_agency_import() -> None:
    """Verify that the agency root package is importable and exposes __version__."""
    assert agency is not None
    assert agency.__version__ == "0.1.0"
