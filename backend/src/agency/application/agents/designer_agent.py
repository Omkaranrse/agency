"""DesignerAgent converting Specs into DesignTokens and client-specific PageContent."""

import re

from agency.application.agents.input_sanitizer import InputSanitizer
from agency.application.agents.models import DesignerOutputSchema, DesignerResult
from agency.application.agents.prompt_loader import PromptLoader
from agency.application.errors import ApplicationError
from agency.application.ports.llm import LLMPort
from agency.domain.entities.design_tokens import DesignTokens
from agency.domain.entities.page_content import PageContent
from agency.domain.entities.spec import Spec

FORBIDDEN_PLACEHOLDER_PATTERNS = [
    re.compile(r"\blorem\s+ipsum\b", re.IGNORECASE),
    re.compile(r"\bdolor\s+sit\s+amet\b", re.IGNORECASE),
    re.compile(r"\[insert\b", re.IGNORECASE),
    re.compile(r"\btodo:\s*", re.IGNORECASE),
    re.compile(r"\bplaceholder\s+(text|content|copy)\b", re.IGNORECASE),
]


class DesignerValidationError(ApplicationError):
    """Raised when generated design tokens or page content violate constraints."""


class DesignerAgent:
    """Visual design and content synthesis agent."""

    def __init__(
        self,
        llm: LLMPort,
        prompt_loader: PromptLoader | None = None,
        prompt_version: str = "v1",
    ) -> None:
        self.llm = llm
        self.prompt_loader = prompt_loader or PromptLoader()
        self.prompt_version = prompt_version

    def create_design(
        self,
        spec: Spec,
        *,
        run_id: str | None = None,
        correlation_id: str | None = None,
    ) -> DesignerResult:
        """Convert a functional Spec into design tokens and structured page content."""
        # 1. Prepare Versioned System Prompt and Untrusted Spec
        system_prompt = self.prompt_loader.load_prompt("designer", self.prompt_version)
        spec_payload = InputSanitizer.wrap_untrusted(
            "untrusted_spec",
            spec.model_dump(mode="json"),
        )

        instructions = (
            "Generate design tokens and authentic page content for the "
            "following specification:\n\n"
        )
        full_prompt = f"{system_prompt}\n\n{instructions}{spec_payload}\n"

        # 2. Call LLMPort with Structured Output
        response: DesignerOutputSchema = self.llm.generate_structured(
            schema=DesignerOutputSchema,
            prompt=full_prompt,
            role="designer",
            run_id=run_id,
            correlation_id=correlation_id,
        )

        # 3. Server-Side Strict Validation of Design Tokens
        tokens = self._validate_and_build_tokens(response)

        # 4. Server-Side Strict Validation of Page Content
        self._validate_page_content(response.pages, spec)

        return DesignerResult(
            tokens=tokens,
            pages=response.pages,
            theme=response.theme,
            prompt_version=self.prompt_version,
            assumptions=response.assumptions,
        )

    def _validate_and_build_tokens(
        self, response: DesignerOutputSchema
    ) -> DesignTokens:
        """Enforce font restrictions, color requirements, and token scales."""
        # Font family must be Poppins (enforced by project rules)
        font_family = response.font_family.strip()
        if "poppins" not in font_family.lower():
            raise DesignerValidationError(
                f"Font family '{font_family}' is disallowed. "
                "The project requires 'Poppins' as the primary font."
            )

        # Validate core colors
        for required_role in ("brand_primary", "bg_base", "text_primary"):
            if required_role not in response.colors:
                raise DesignerValidationError(
                    f"Design tokens missing mandatory color role '{required_role}'."
                )

        try:
            return DesignTokens(
                font_family="Poppins",
                colors=response.colors,
                spacing_scale=response.spacing_scale,
                border_radius_scale=response.border_radius_scale,
            )
        except Exception as exc:
            raise DesignerValidationError(
                f"Failed to instantiate DesignTokens domain entity: {exc}"
            ) from exc

    def _validate_page_content(self, pages: list[PageContent], spec: Spec) -> None:
        """Validate content completeness, slug correspondence, and placeholders."""
        if not pages:
            raise DesignerValidationError("No page content was generated.")

        generated_slugs = {p.page_slug for p in pages}
        spec_slugs = {p.slug for p in spec.pages}

        # Check that all spec pages are provided
        missing_slugs = spec_slugs - generated_slugs
        if missing_slugs:
            raise DesignerValidationError(
                f"Missing content for required spec pages: {sorted(missing_slugs)}."
            )

        # Check for placeholder copy or lorem ipsum
        for page in pages:
            for section in page.sections:
                copy_text = section.copy_text
                headline = section.headline or ""

                for pattern in FORBIDDEN_PLACEHOLDER_PATTERNS:
                    if pattern.search(copy_text) or pattern.search(headline):
                        raise DesignerValidationError(
                            f"Forbidden placeholder or filler text detected in page "
                            f"'{page.page_slug}' (section '{section.section_id}'): "
                            f"{pattern.pattern}"
                        )
