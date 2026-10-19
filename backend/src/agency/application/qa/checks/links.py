"""Broken Internal Link QA check."""

import posixpath
import urllib.parse
from html.parser import HTMLParser
from typing import Any

from agency.application.qa.models import (
    CheckResult,
    CheckStatus,
    QAContext,
    SeverityLevel,
)
from agency.application.qa.settings import QASettings

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


class LinkExtractor(HTMLParser):
    """HTML parser to extract href targets and element IDs."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.element_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for attr, val in attrs:
            if attr.lower() == "id" and val:
                self.element_ids.add(val.strip())
            elif tag.lower() == "a" and attr.lower() == "href" and val:
                self.links.append(val.strip())


def _normalize_route(path: str) -> str:
    """Normalize internal routes to a uniform slash-delimited format."""
    parsed = urllib.parse.urlsplit(path)
    clean = posixpath.normpath(parsed.path)
    if not clean.startswith("/"):
        clean = "/" + clean
    return clean


class LinkCheck:
    """Verifies internal links on required pages resolve to valid destinations."""

    NAME = "broken_internal_links"

    def __init__(self, settings: QASettings) -> None:
        self._settings = settings

    def run(self, context: QAContext) -> CheckResult:
        """Scan internal links across all required pages."""
        if not self._settings.enable_link_check:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.SKIPPED,
                passed=True,
                details="Internal link check disabled by configuration.",
            )

        routes = context.routes or self._settings.required_routes
        known_routes = {_normalize_route(r) for r in routes}
        known_routes.add("/")

        # Gather page HTMLs
        pages_html: dict[str, str] = dict(context.rendered_pages_html)

        # If files exist in dist_dir or site_dir, read them
        base_dir = context.dist_dir or context.site_dir
        if base_dir and base_dir.is_dir():
            for r in routes:
                norm = _normalize_route(r).strip("/")
                candidates = [
                    base_dir / norm / "index.html" if norm else base_dir / "index.html",
                    base_dir / f"{norm}.html" if norm else base_dir / "index.html",
                ]
                for cand in candidates:
                    if cand.is_file():
                        pages_html[r] = cand.read_text(
                            encoding="utf-8", errors="replace"
                        )
                        known_routes.add(_normalize_route(r))
                        break

        # If sandbox is available
        if context.sandbox and context.sandbox_id and not pages_html:
            for r in routes:
                norm = _normalize_route(r).strip("/")
                sandbox_candidates = [
                    f"dist/{norm}/index.html" if norm else "dist/index.html",
                    f"dist/{norm}.html" if norm else "dist/index.html",
                ]
                for sb_cand in sandbox_candidates:
                    try:
                        content = context.sandbox.read_file(context.sandbox_id, sb_cand)
                        pages_html[r] = content
                        known_routes.add(_normalize_route(r))
                        break
                    except Exception:
                        continue

        if not pages_html:
            # If no HTML could be discovered to validate
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.ERROR,
                passed=False,
                error_code="HTML_PAGE_UNAVAILABLE",
                severity=SeverityLevel.SERIOUS,
                details="No rendered HTML content was available for link validation.",
            )

        broken_links: list[dict[str, Any]] = []

        # Parse links and IDs for each page
        parsed_pages: dict[str, tuple[list[str], set[str]]] = {}
        for route, html in pages_html.items():
            parser = LinkExtractor()
            try:
                parser.feed(html)
            except Exception:
                pass
            parsed_pages[route] = (parser.links, parser.element_ids)

        for route, (links, page_ids) in parsed_pages.items():
            for raw_href in links:
                if not raw_href or raw_href.startswith(
                    ("mailto:", "tel:", "javascript:")
                ):
                    continue

                parsed = urllib.parse.urlsplit(raw_href)

                # Check if external host
                if parsed.scheme in ("http", "https"):
                    host = (parsed.hostname or "").lower()
                    if host not in LOCAL_HOSTS:
                        # External link — strictly ignored to prevent arbitrary requests
                        continue

                # Fragment-only link: #section
                if raw_href.startswith("#"):
                    fragment = raw_href.lstrip("#")
                    if fragment and fragment not in page_ids:
                        broken_links.append(
                            {
                                "page": route,
                                "target": raw_href,
                                "reason": (
                                    f"Anchor target '#{fragment}' not found on page."
                                ),
                            }
                        )
                    continue

                # Internal path resolution
                target_path = parsed.path
                if not target_path.startswith("/"):
                    # Resolve relative to current page directory
                    current_dir = posixpath.dirname(_normalize_route(route))
                    target_path = posixpath.join(current_dir, target_path)

                normalized_target = _normalize_route(target_path)

                # Check if target route is known
                if normalized_target not in known_routes:
                    # Also check if without trailing slash matches
                    alt = (
                        normalized_target.rstrip("/")
                        if normalized_target.endswith("/")
                        else normalized_target + "/"
                    )
                    if alt not in known_routes:
                        broken_links.append(
                            {
                                "page": route,
                                "target": raw_href,
                                "reason": (
                                    f"Target route '{normalized_target}' does "
                                    f"not exist."
                                ),
                            }
                        )

        if broken_links:
            first = broken_links[0]
            count = len(broken_links)
            diag = (
                f"Broken link on {first['page']} targeting '{first['target']}': "
                f"{first['reason']} ({count} total issue(s))"
            )
            if len(diag) > self._settings.max_diagnostic_length:
                diag = diag[: self._settings.max_diagnostic_length] + "..."

            return CheckResult(
                name=self.NAME,
                status=CheckStatus.FAILED,
                passed=False,
                error_code="BROKEN_INTERNAL_LINK",
                page=first["page"],
                severity=SeverityLevel.SERIOUS,
                details=diag,
                diagnostic_metadata={
                    "broken_link_count": count,
                    "issues": broken_links[: self._settings.max_issues_per_check],
                },
            )

        num_pages = len(pages_html)
        return CheckResult(
            name=self.NAME,
            status=CheckStatus.PASSED,
            passed=True,
            details=(
                f"All internal links verified successfully across {num_pages} page(s)."
            ),
        )
