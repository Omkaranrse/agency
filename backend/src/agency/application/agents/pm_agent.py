"""PMAgent converting validated Briefs into Specs or clarification questions."""

import re

from agency.application.agents.input_sanitizer import InputSanitizer
from agency.application.agents.models import (
    PMClarificationResult,
    PMOutputSchema,
    PMResult,
    PMSpecResult,
)
from agency.application.agents.prompt_loader import PromptLoader
from agency.application.errors import StructuredOutputError
from agency.application.ports.llm import LLMPort
from agency.domain.entities.brief import Brief

UNSUPPORTED_KEYWORDS = (
    "database",
    "sql",
    "postgres",
    "mysql",
    "mongo",
    "authentication",
    "login",
    "oauth",
    "stripe",
    "payment",
    "paypal",
    "checkout",
    "shopping cart",
    "backend api",
    "django",
    "fastapi",
)


class PMAgent:
    """Product Manager agent for requirement analysis and specification generation."""

    def __init__(
        self,
        llm: LLMPort,
        prompt_loader: PromptLoader | None = None,
        prompt_version: str = "v1",
    ) -> None:
        self.llm = llm
        self.prompt_loader = prompt_loader or PromptLoader()
        self.prompt_version = prompt_version

    def generate_spec(
        self,
        brief: Brief,
        *,
        run_id: str | None = None,
        correlation_id: str | None = None,
    ) -> PMResult:
        """Convert a client brief into a formal Spec or clarification questions."""
        # 1. Deterministic Clarification Checks (before calling LLM)
        deterministic_clarification = self._check_deterministic_clarification(brief)
        if deterministic_clarification is not None:
            return deterministic_clarification

        # 2. Prepare Versioned System Prompt and Untrusted Input
        system_prompt = self.prompt_loader.load_prompt("pm", self.prompt_version)
        brief_payload = InputSanitizer.wrap_untrusted(
            "untrusted_client_brief",
            brief.model_dump(mode="json"),
        )

        prompt_intro = (
            "Analyze the following client brief and generate the technical "
            "specification or determine if further clarification is needed:\n\n"
        )
        full_prompt = f"{system_prompt}\n\n{prompt_intro}{brief_payload}\n"

        # 3. Call LLMPort with Structured Output
        response: PMOutputSchema = self.llm.generate_structured(
            schema=PMOutputSchema,
            prompt=full_prompt,
            role="pm",
            run_id=run_id,
            correlation_id=correlation_id,
        )

        # 4. Handle Clarification vs Spec Output
        if response.needs_clarification or response.clarification_questions:
            questions = response.clarification_questions or [
                "Please clarify the primary objectives and target audience."
            ]
            return PMClarificationResult(
                status="clarification",
                questions=questions,
                missing_fields=response.missing_fields,
                prompt_version=self.prompt_version,
            )

        if response.spec is not None:
            return PMSpecResult(
                status="spec",
                spec=response.spec,
                prompt_version=self.prompt_version,
                assumptions=response.assumptions,
            )

        raise StructuredOutputError(
            schema_name="PMOutputSchema",
            message="LLM returned neither clarification questions nor a valid Spec.",
        )

    def _check_deterministic_clarification(
        self, brief: Brief
    ) -> PMClarificationResult | None:
        """Perform server-side deterministic policy checks on brief completeness."""
        notes_lower = brief.content_notes.lower()
        site_type_lower = brief.site_type.lower()

        # Check for unsupported technical features (auth, database, payments)
        for keyword in UNSUPPORTED_KEYWORDS:
            if keyword in notes_lower or keyword in site_type_lower:
                return PMClarificationResult(
                    status="clarification",
                    questions=[
                        (
                            f"The brief mentions '{keyword}', which requires dynamic "
                            "backend, database, or payment processing. The Astro "
                            "portfolio template is a static site. Can these "
                            "requirements be fulfilled via a static showcase or "
                            "external links instead?"
                        )
                    ],
                    missing_fields=["supported_architecture"],
                    prompt_version=self.prompt_version,
                )

        # Check for meaningless or overly vague purpose
        meaningful_words = [
            w
            for w in re.split(r"\W+", notes_lower)
            if len(w) > 3 and w not in ("website", "page", "site")
        ]
        if len(meaningful_words) < 2 and len(brief.content_notes) < 25:
            return PMClarificationResult(
                status="clarification",
                questions=[
                    (
                        "The brief does not contain sufficient details about your "
                        "background, work, or the primary purpose of your portfolio "
                        "website. Could you provide a summary of your expertise and "
                        "featured projects?"
                    )
                ],
                missing_fields=["content_notes", "purpose"],
                prompt_version=self.prompt_version,
            )

        # Check for conflicting multi-page vs single-page instructions
        if "single page" in site_type_lower or "one page" in site_type_lower:
            if len(brief.pages) > 2:
                page_list = ", ".join(brief.pages)
                return PMClarificationResult(
                    status="clarification",
                    questions=[
                        (
                            f"The brief specifies a '{brief.site_type}', but requests "
                            f"{len(brief.pages)} separate pages ({page_list}). "
                            "Should this be a multi-page site or a single-page layout "
                            "with sections?"
                        )
                    ],
                    missing_fields=["page_structure"],
                    prompt_version=self.prompt_version,
                )

        return None
