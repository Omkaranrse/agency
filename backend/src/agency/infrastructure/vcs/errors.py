"""VCS-specific exception definitions."""

from agency.application.errors import (
    GitAmbiguityError,
    GitAuthenticationError,
    GitConflictError,
    GitError,
    GitRateLimitError,
    GitValidationError,
)

__all__ = [
    "GitAmbiguityError",
    "GitAuthenticationError",
    "GitConflictError",
    "GitError",
    "GitRateLimitError",
    "GitValidationError",
]
