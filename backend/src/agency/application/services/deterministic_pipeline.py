"""Deterministic pipeline services for mapping brief content and managing artifacts."""

import io
import json
import re
import tarfile
from pathlib import Path
from typing import Any

from agency.domain.entities.brief import Brief
from agency.domain.entities.design_tokens import DesignTokens
from agency.domain.entities.qa_report import QAReport
from agency.domain.entities.spec import AcceptanceCriterion, Spec, SpecPage, SpecSection

EDITORIAL_TOKENS = DesignTokens(
    font_family="Poppins",
    colors={
        "brand_primary": "#9C4126",
        "brand_hover": "#7D321C",
        "brand_muted": "#EADFD9",
        "bg_base": "#F9F8F6",
        "bg_surface": "#FFFFFF",
        "text_primary": "#1C1B19",
    },
    spacing_scale={
        "space-1": 4.0,
        "space-2": 8.0,
        "space-4": 16.0,
        "space-8": 32.0,
        "space-16": 64.0,
    },
    border_radius_scale={
        "radius-sm": 2.0,
        "radius-md": 4.0,
        "radius-lg": 8.0,
    },
)

STUDIO_TOKENS = DesignTokens(
    font_family="Poppins",
    colors={
        "brand_primary": "#0952C6",
        "brand_hover": "#063C93",
        "brand_muted": "#E2ECFA",
        "bg_base": "#FFFFFF",
        "bg_surface": "#F5F7FA",
        "text_primary": "#0C1017",
    },
    spacing_scale={
        "space-1": 4.0,
        "space-2": 8.0,
        "space-4": 16.0,
        "space-8": 32.0,
        "space-16": 64.0,
    },
    border_radius_scale={
        "radius-sm": 2.0,
        "radius-md": 4.0,
        "radius-lg": 8.0,
    },
)


def _slugify(text: str) -> str:
    """Deterministically convert a string to a lowercase alphanumeric slug."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return clean or "item"


class DeterministicContentMapper:
    """Maps client brief fields to structured JSON content files deterministically."""

    @classmethod
    def resolve_variant_and_tokens(cls, brief: Brief) -> tuple[str, DesignTokens]:
        """Determine template variant and corresponding DesignTokens from brief."""
        tone_lower = brief.tone.lower()
        if any(keyword in tone_lower for keyword in ("studio", "modern", "tech")):
            return "studio", STUDIO_TOKENS
        return "editorial", EDITORIAL_TOKENS

    @classmethod
    def generate_spec(cls, project_id: str, brief: Brief) -> Spec:
        """Create a formal Spec domain aggregate from the brief."""
        pages: list[SpecPage] = []
        criteria: list[AcceptanceCriterion] = []

        for page in brief.pages:
            slug = _slugify(page)
            # Home page slug must be 'home' or slug representation
            pages.append(
                SpecPage(
                    slug=slug,
                    title=page,
                    sections=[
                        SpecSection(
                            id=f"{slug}-main",
                            title=f"{page} Main Section",
                            description=f"Primary view and content for {page}",
                            required_content=[brief.client_name, brief.site_type],
                        )
                    ],
                )
            )
            criteria.append(
                AcceptanceCriterion(
                    id=f"ac-{slug}-heading",
                    description=(
                        f"Page '{page}' must render a valid <h1> heading and "
                        "pass automated quality checks."
                    ),
                )
            )

        return Spec(
            project_id=project_id,
            title=f"{brief.client_name} — {brief.site_type} Specification",
            pages=pages,
            technical_constraints=[
                "Astro 4 SSG",
                "Tailwind CSS",
                "Poppins typography only",
                "Responsive 390px and 1280px viewports",
                "WCAG 2.2 AA contrast compliance",
            ],
            acceptance_criteria=criteria,
        )

    @classmethod
    def map_content_files(cls, brief: Brief, variant: str) -> dict[str, dict[str, Any]]:
        """Produce structured content dictionaries for all Astro content collections."""
        # 1. Navigation items
        nav_items: list[dict[str, str]] = []
        for p in brief.pages:
            norm = p.strip().lower()
            if norm in ("home", "index"):
                href = "/"
                label = "Home"
            elif norm == "about":
                href = "/about"
                label = "About"
            elif norm == "projects":
                href = "/projects"
                label = "Projects"
            elif norm == "contact":
                href = "/contact"
                label = "Contact"
            else:
                href = f"/{_slugify(p)}"
                label = p
            nav_items.append({"label": label, "href": href})

        # Ensure required four routes are present in navigation
        existing_hrefs = {item["href"] for item in nav_items}
        fallback_nav = [
            ("Home", "/"),
            ("About", "/about"),
            ("Projects", "/projects"),
            ("Contact", "/contact"),
        ]
        for label, href in fallback_nav:
            if href not in existing_hrefs:
                nav_items.append({"label": label, "href": href})

        # 2. Social links from brief.links
        social_links: list[dict[str, str]] = []
        twitter_handle = ""
        for link in brief.links:
            url_str = str(link).rstrip("/")
            url_lower = url_str.lower()
            if "github.com" in url_lower:
                social_links.append(
                    {
                        "platform": "GitHub",
                        "url": url_str,
                        "label": f"Visit {brief.client_name} on GitHub",
                    }
                )
            elif "linkedin.com" in url_lower:
                social_links.append(
                    {
                        "platform": "LinkedIn",
                        "url": url_str,
                        "label": f"Connect with {brief.client_name} on LinkedIn",
                    }
                )
            elif "twitter.com" in url_lower or "x.com" in url_lower:
                handle = url_str.split("/")[-1]
                twitter_handle = f"@{handle}" if handle else "@agency"
                social_links.append(
                    {
                        "platform": "Twitter",
                        "url": url_str,
                        "label": f"Follow {brief.client_name} on Twitter",
                    }
                )
            else:
                social_links.append(
                    {
                        "platform": "Web",
                        "url": url_str,
                        "label": f"Visit {url_str}",
                    }
                )

        if not social_links:
            social_links = [
                {
                    "platform": "GitHub",
                    "url": "https://github.com",
                    "label": f"Visit {brief.client_name} on GitHub",
                },
                {
                    "platform": "LinkedIn",
                    "url": "https://linkedin.com",
                    "label": f"Connect with {brief.client_name} on LinkedIn",
                },
            ]

        # 3. site.json
        site_json: dict[str, Any] = {
            "clientName": brief.client_name,
            "siteTitle": f"{brief.client_name} — {brief.site_type}",
            "description": (
                f"{brief.site_type} portfolio of {brief.client_name}. "
                f"{brief.content_notes[:100].strip()}."
            ),
            "theme": variant,
            "nav": nav_items,
            "footerText": (
                f"© 2026 {brief.client_name}. Built with Astro & Clean Architecture."
            ),
            "socialLinks": social_links,
            "seo": {
                "twitterHandle": twitter_handle or "@portfolio",
            },
        }

        # 4. home.json
        home_json: dict[str, Any] = {
            "heroEyebrow": f"{brief.tone.title()} {brief.site_type}",
            "headline": f"Engineering durable solutions for {brief.client_name}.",
            "supportingCopy": brief.content_notes.strip(),
            "ctaPrimary": {
                "label": "Explore Featured Projects",
                "href": "/projects",
            },
            "ctaSecondary": {
                "label": "Get in Touch",
                "href": "/contact",
            },
            "highlights": [
                {
                    "metric": "Production",
                    "label": f"{brief.site_type} delivery",
                },
                {
                    "metric": "100%",
                    "label": "WCAG AA accessibility target",
                },
                {
                    "metric": "Deterministic",
                    "label": "Clean architecture pipeline",
                },
            ],
            "featuredSectionTitle": "Selected Work",
            "featuredSectionSubtitle": (
                f"Production systems engineered for {brief.client_name}."
            ),
        }

        # 5. about.json
        bio_lines = [
            line.strip() for line in brief.content_notes.split("\n") if line.strip()
        ]
        if not bio_lines:
            bio_lines = [brief.content_notes.strip()]

        about_json: dict[str, Any] = {
            "title": f"About {brief.client_name}",
            "intro": (
                f"{brief.client_name} specializes in {brief.tone.lower()} "
                f"digital delivery and systems architecture."
            ),
            "bioParagraphs": bio_lines,
            "skills": [
                {
                    "category": "Core Competencies",
                    "items": [
                        "Clean Architecture",
                        "TypeScript",
                        "Python 3.12",
                        "Accessible Web Standards",
                        "Deterministic Pipelines",
                    ],
                },
                {
                    "category": "Design Systems",
                    "items": [
                        "Tailwind CSS",
                        "Tokens Engine",
                        "WCAG 2.2 AA",
                        "Responsive Layouts",
                    ],
                },
            ],
            "timeline": [
                {
                    "period": "2024 — Present",
                    "role": f"Lead {brief.site_type} Architect",
                    "organization": brief.client_name,
                    "description": (
                        "Directing technical delivery and systems design across "
                        "accessible web applications."
                    ),
                },
                {
                    "period": "2020 — 2024",
                    "role": "Senior Systems Engineer",
                    "organization": "Technical Innovations Ltd",
                    "description": (
                        "Engineered resilient multi-platform systems with strict "
                        "static typing and automated verification."
                    ),
                },
            ],
            "cta": {
                "headline": "Interested in collaborating on a technical project?",
                "linkText": "Start a Conversation",
                "href": "/contact",
            },
        }

        # 6. projects.json
        projects_json: dict[str, Any] = {
            "title": "Projects & Case Studies",
            "subtitle": f"Selected engineering works by {brief.client_name}.",
            "projects": [
                {
                    "title": "Sentinel Core",
                    "slug": "sentinel-core",
                    "shortDescription": (
                        "Distributed event-driven orchestration engine with "
                        "observable state machine boundaries."
                    ),
                    "detailedDescription": (
                        "An enterprise-grade orchestration runtime implementing "
                        "Clean Architecture and strict static typing. Coordinates "
                        "long-running workflows with deterministic state persistence "
                        "and recovery guarantees."
                    ),
                    "techTags": ["TypeScript", "Node.js", "Docker", "State Machines"],
                    "image": "/images/project-sentinel.svg",
                    "imageAlt": (
                        "Architectural diagram showing state machine event "
                        "transitions in Sentinel Core"
                    ),
                    "liveDemoUrl": "https://example.com/demo/sentinel",
                    "sourceCodeUrl": "https://github.com/example/sentinel-core",
                    "featured": True,
                },
                {
                    "title": "Prism Design System",
                    "slug": "prism-design-system",
                    "shortDescription": (
                        "Zero-dependency accessible component tokens and semantic "
                        "layout engine for enterprise web apps."
                    ),
                    "detailedDescription": (
                        "A multi-brand design system built entirely with CSS custom "
                        "properties and WCAG 2.2 AA compliant markup. Features "
                        "high-contrast themes, keyboard trap prevention, and complete "
                        "screen-reader compatibility."
                    ),
                    "techTags": [
                        "Astro",
                        "Tailwind CSS",
                        "WCAG 2.2 AA",
                        "Design Tokens",
                    ],
                    "image": "/images/project-prism.svg",
                    "imageAlt": (
                        "Visual token hierarchy preview displaying color scales"
                        " in Prism"
                    ),
                    "liveDemoUrl": "https://example.com/demo/prism",
                    "sourceCodeUrl": "https://github.com/example/prism-tokens",
                    "featured": True,
                },
                {
                    "title": "Vanguard Metrics",
                    "slug": "vanguard-metrics",
                    "shortDescription": (
                        "Real-time telemetry aggregator processing system events "
                        "with low-latency in-memory buffers."
                    ),
                    "detailedDescription": (
                        "High-throughput monitoring daemon designed for microservices "
                        "deployed across heterogeneous container environments."
                    ),
                    "techTags": ["Python 3.12", "Prometheus", "OpenTelemetry", "Linux"],
                    "image": "/images/project-vanguard.svg",
                    "imageAlt": "Metrics dashboard overview illustrating request rates",
                    "liveDemoUrl": "https://example.com/demo/vanguard",
                    "sourceCodeUrl": "",
                    "featured": False,
                },
                {
                    "title": "Kestrel Build Runner",
                    "slug": "kestrel-runner",
                    "shortDescription": (
                        "Secure sandbox executor running isolated untrusted scripts "
                        "inside unprivileged containers."
                    ),
                    "detailedDescription": (
                        "A hardened execution agent featuring strict path traversal "
                        "prevention, memory quotas, and dropped Linux capabilities."
                    ),
                    "techTags": ["Docker SDK", "Linux Security", "Python", "POSIX"],
                    "image": "/images/project-kestrel.svg",
                    "imageAlt": "Security boundary schematic showing sandbox isolation",
                    "liveDemoUrl": "",
                    "sourceCodeUrl": "https://github.com/example/kestrel-runner",
                    "featured": False,
                },
            ],
        }

        # 7. contact.json
        client_slug = _slugify(brief.client_name)
        contact_json: dict[str, Any] = {
            "title": f"Contact {brief.client_name}",
            "description": (
                f"Have an architectural inquiry or technical question for "
                f"{brief.client_name}? Send a message below."
            ),
            "email": f"{client_slug}@example.com",
            "mode": "static",
            "form": {
                "nameLabel": "Your Name",
                "emailLabel": "Your Email Address",
                "messageLabel": "Project Summary or Inquiry",
                "submitLabel": "Send Message",
                "privacyNote": (
                    "Your contact information is only used to respond to your inquiry "
                    "and is never shared."
                ),
                "staticModeNotice": (
                    "Notice: This template is in demonstration mode. Submissions are "
                    "not transmitted over the network."
                ),
                "successMessage": (
                    "Thank you! Your inquiry has been prepared for transmission."
                ),
            },
        }

        return {
            "src/content/site.json": site_json,
            "src/content/home.json": home_json,
            "src/content/about.json": about_json,
            "src/content/projects.json": projects_json,
            "src/content/contact.json": contact_json,
        }


class DeterministicArtifactManager:
    """Manages creation, layout, and artifact extraction under runs/<run_id>/."""

    REQUIRED_SCREENSHOT_NAMES: tuple[str, ...] = (
        "home-390.png",
        "home-1280.png",
        "about-390.png",
        "about-1280.png",
        "projects-390.png",
        "projects-1280.png",
        "contact-390.png",
        "contact-1280.png",
    )

    def __init__(self, runs_root: Path) -> None:
        self.runs_root = runs_root

    def create_run_directory(self, run_id: str) -> Path:
        """Create an isolated, dedicated directory for the given run_id."""
        run_dir = (self.runs_root / run_id).resolve()
        if run_dir.exists():
            raise FileExistsError(
                f"Run directory already exists at '{run_dir}'. "
                "Refusing to overwrite existing run."
            )
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "screenshots").mkdir(parents=True, exist_ok=True)
        (run_dir / "site").mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_build_log(self, run_dir: Path, logs: str) -> Path:
        """Write the build log file."""
        log_path = run_dir / "build.log"
        log_path.write_text(logs, encoding="utf-8")
        return log_path

    def write_qa_report(self, run_dir: Path, qa_report: QAReport) -> Path:
        """Write the validated QA report file."""
        qa_path = run_dir / "qa-report.json"
        data = qa_report.model_dump(mode="json")
        qa_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return qa_path

    def write_screenshot(self, run_dir: Path, filename: str, content: bytes) -> Path:
        """Save a screenshot file under runs/<run_id>/screenshots/."""
        dest = run_dir / "screenshots" / filename
        dest.write_bytes(content)
        return dest

    def extract_site_archive(self, run_dir: Path, archive_bytes: bytes) -> Path:
        """Safely extract the built static site archive into runs/<run_id>/site/."""
        site_dir = run_dir / "site"
        site_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:*") as tar:
            # Python 3.12 data filter prevents path traversal and unsafe links
            tar.extractall(path=site_dir, filter="data")

        return site_dir

    def write_manifest(
        self,
        run_dir: Path,
        manifest_data: dict[str, Any],
    ) -> Path:
        """Write the final run manifest.json."""
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, indent=2, default=str), encoding="utf-8"
        )
        return manifest_path

    def write_summary(
        self,
        run_dir: Path,
        summary_data: dict[str, Any],
    ) -> Path:
        """Write the summary.json report."""
        summary_path = run_dir / "summary.json"
        summary_path.write_text(
            json.dumps(summary_data, indent=2, default=str), encoding="utf-8"
        )
        return summary_path
