"""HTML structural validation QA check."""

from html.parser import HTMLParser
from typing import Any

from agency.application.qa.models import (
    CheckResult,
    CheckStatus,
    QAContext,
    SeverityLevel,
)
from agency.application.qa.settings import QASettings


class HtmlStructureParser(HTMLParser):
    """Deterministic parser validating core HTML5 document structure."""

    def __init__(self) -> None:
        super().__init__()
        self.html_lang: str | None = None
        self.has_html_tag = False
        self.in_title = False
        self.title_text: list[str] = []
        self.h1_count = 0
        self.ids_seen: set[str] = set()
        self.duplicate_ids: list[str] = []
        self.syntax_errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if t == "html":
            self.has_html_tag = True
            self.html_lang = attr_dict.get("lang", "").strip() or None
        elif t == "title":
            self.in_title = True
        elif t == "h1":
            self.h1_count += 1

        if "id" in attr_dict:
            elem_id = attr_dict["id"].strip()
            if elem_id:
                if elem_id in self.ids_seen:
                    self.duplicate_ids.append(elem_id)
                self.ids_seen.add(elem_id)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_text.append(data)


class HtmlValidationCheck:
    """Validates structural semantics and integrity of rendered HTML pages."""

    NAME = "html_validation"

    def __init__(self, settings: QASettings) -> None:
        self._settings = settings

    def run(self, context: QAContext) -> CheckResult:
        """Execute deterministic HTML5 structural validation."""
        if not (
            self._settings.enable_html_validation and self._settings.enable_html_check
        ):
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.SKIPPED,
                passed=True,
                details="HTML validation check disabled by configuration.",
            )

        routes = context.routes or self._settings.required_routes
        pages_html: dict[str, str] = dict(context.rendered_pages_html)

        base_dir = context.dist_dir or context.site_dir
        if base_dir and base_dir.is_dir():
            for r in routes:
                norm = r.strip("/")
                candidates = [
                    base_dir / norm / "index.html" if norm else base_dir / "index.html",
                    base_dir / f"{norm}.html" if norm else base_dir / "index.html",
                ]
                for cand in candidates:
                    if cand.is_file():
                        pages_html[r] = cand.read_text(
                            encoding="utf-8", errors="replace"
                        )
                        break

        if context.sandbox and context.sandbox_id and not pages_html:
            for r in routes:
                norm = r.strip("/")
                sandbox_candidates = [
                    f"dist/{norm}/index.html" if norm else "dist/index.html",
                    f"dist/{norm}.html" if norm else "dist/index.html",
                ]
                for sb_cand in sandbox_candidates:
                    try:
                        content = context.sandbox.read_file(context.sandbox_id, sb_cand)
                        pages_html[r] = content
                        break
                    except Exception:
                        continue

        if not pages_html:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.ERROR,
                passed=False,
                error_code="HTML_CONTENT_UNAVAILABLE",
                severity=SeverityLevel.SERIOUS,
                details="No rendered HTML content available for structural validation.",
            )

        issues: list[dict[str, Any]] = []

        for route, html in pages_html.items():
            parser = HtmlStructureParser()
            try:
                parser.feed(html)
            except Exception as exc:
                issues.append(
                    {
                        "page": route,
                        "error_code": "HTML_SYNTAX_ERROR",
                        "message": f"Malformed HTML syntax: {exc}",
                    }
                )
                continue

            # 1. Missing lang attribute
            if not parser.html_lang:
                issues.append(
                    {
                        "page": route,
                        "error_code": "HTML_MISSING_LANG",
                        "message": (
                            "Missing or empty 'lang' attribute on <html> element."
                        ),
                    }
                )

            # 2. Missing or empty <title>
            full_title = "".join(parser.title_text).strip()
            if not full_title:
                issues.append(
                    {
                        "page": route,
                        "error_code": "HTML_MISSING_TITLE",
                        "message": "Document is missing a non-empty <title> element.",
                    }
                )

            # 3. Duplicate IDs
            if parser.duplicate_ids:
                dup_str = ", ".join(parser.duplicate_ids[:5])
                issues.append(
                    {
                        "page": route,
                        "error_code": "HTML_DUPLICATE_ID",
                        "message": f"Duplicate element ID(s) detected: {dup_str}",
                    }
                )

            # 4. Heading check (must have at least one <h1>)
            if parser.h1_count == 0:
                issues.append(
                    {
                        "page": route,
                        "error_code": "HTML_MISSING_H1",
                        "message": "Page contains zero <h1> top-level headings.",
                    }
                )

        if issues:
            first = issues[0]
            count = len(issues)
            diag = (
                f"HTML structural defect on {first['page']}: {first['message']} "
                f"({count} total issue(s))"
            )
            if len(diag) > self._settings.max_diagnostic_length:
                diag = diag[: self._settings.max_diagnostic_length] + "..."

            return CheckResult(
                name=self.NAME,
                status=CheckStatus.FAILED,
                passed=False,
                error_code=first["error_code"],
                page=first["page"],
                severity=SeverityLevel.SERIOUS,
                details=diag,
                diagnostic_metadata={
                    "total_issues": count,
                    "issues": issues[: self._settings.max_issues_per_check],
                },
            )

        num_pages = len(pages_html)
        return CheckResult(
            name=self.NAME,
            status=CheckStatus.PASSED,
            passed=True,
            details=f"HTML5 structural validation passed across {num_pages} page(s).",
        )
