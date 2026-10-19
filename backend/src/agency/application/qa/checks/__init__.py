"""QA checks package."""

from agency.application.qa.checks.accessibility import AccessibilityCheck
from agency.application.qa.checks.build import BuildCheck
from agency.application.qa.checks.console import ConsoleCheck
from agency.application.qa.checks.html_validation import HtmlValidationCheck
from agency.application.qa.checks.lighthouse import LighthouseCheck
from agency.application.qa.checks.links import LinkCheck

__all__ = [
    "AccessibilityCheck",
    "BuildCheck",
    "ConsoleCheck",
    "HtmlValidationCheck",
    "LighthouseCheck",
    "LinkCheck",
]
