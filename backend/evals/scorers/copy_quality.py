"""Deterministic rubric for website copy quality evaluation."""

import re
from typing import Any

from agency.domain.entities.brief import Brief
from evals.schemas import CopyQualityRubricScore

PLACEHOLDER_PATTERNS = [
    re.compile(r"\blorem\s+ipsum\b", re.IGNORECASE),
    re.compile(r"\bdolor\s+sit\s+amet\b", re.IGNORECASE),
    re.compile(r"\bplaceholder\b", re.IGNORECASE),
    re.compile(r"\btodo\b", re.IGNORECASE),
    re.compile(r"\btbd\b", re.IGNORECASE),
    re.compile(r"\binsert\s+here\b", re.IGNORECASE),
    re.compile(r"\[(your|insert|client|name|phone|email)[\w\s]*\]", re.IGNORECASE),
    re.compile(r"\bfoo\s+bar\b", re.IGNORECASE),
]

FABRICATED_CREDENTIAL_PATTERNS = [
    re.compile(r"\bnobel\s+prize\b", re.IGNORECASE),
    re.compile(r"\bpulitzer\b", re.IGNORECASE),
    re.compile(r"\bforbes\s+30\s+under\s+30\b", re.IGNORECASE),
    re.compile(r"\boscar-winning\b", re.IGNORECASE),
]

TONE_MARKERS = {
    "editorial": {
        "journal",
        "narrative",
        "essay",
        "inquiry",
        "investigative",
        "critique",
        "profile",
        "thought",
    },
    "minimal": {
        "essential",
        "simple",
        "clarity",
        "focused",
        "refined",
        "clean",
        "structure",
        "space",
    },
    "warm": {
        "welcoming",
        "community",
        "craft",
        "family",
        "gather",
        "organic",
        "neighborhood",
        "handmade",
    },
    "bold": {
        "fearless",
        "disrupt",
        "kinetic",
        "impact",
        "forward",
        "transform",
        "dynamic",
        "visionary",
    },
    "professional": {
        "solution",
        "enterprise",
        "scalable",
        "delivering",
        "results",
        "standards",
        "architecture",
    },
    "authoritative": {
        "advisory",
        "strategic",
        "governance",
        "compliance",
        "insight",
        "executive",
        "framework",
    },
    "inspiring": {
        "potential",
        "purpose",
        "resilience",
        "empower",
        "transformation",
        "flourish",
        "future",
    },
    "trustworthy": {
        "licensed",
        "certified",
        "guarantee",
        "dependable",
        "trusted",
        "safety",
        "honest",
    },
    "vibrant": {
        "soundscape",
        "rhythm",
        "expressive",
        "electric",
        "composition",
        "energy",
        "harmony",
    },
    "modern": {
        "accessible",
        "technology",
        "interface",
        "distributed",
        "platform",
        "open-source",
        "agile",
    },
}


def _extract_text_corpus(pages_content: list[dict[str, Any]] | list[Any]) -> str:
    """Concatenate all textual elements from page models into a string."""
    text_parts: list[str] = []
    for item in pages_content:
        data = (
            item
            if isinstance(item, dict)
            else (item.model_dump() if hasattr(item, "model_dump") else {})
        )
        if "title" in data and data["title"]:
            text_parts.append(str(data["title"]))
        if "headline" in data and data["headline"]:
            text_parts.append(str(data["headline"]))
        if "bio" in data and data["bio"]:
            text_parts.append(str(data["bio"]))
        if "content" in data and data["content"]:
            text_parts.append(str(data["content"]))
        if "sections" in data and isinstance(data["sections"], list):
            for sec in data["sections"]:
                if isinstance(sec, dict):
                    text_parts.append(str(sec.get("heading", "")))
                    text_parts.append(str(sec.get("body", "")))
                    text_parts.append(str(sec.get("content", "")))
        for k, v in data.items():
            if isinstance(v, str) and k not in {"page_slug", "id"}:
                text_parts.append(v)
    return " ".join(text_parts)


def score_copy_quality(
    brief: Brief,
    pages_content: list[dict[str, Any]] | list[Any],
) -> CopyQualityRubricScore:
    """Evaluate synthesized copy against the deterministic 7-dimension rubric."""
    corpus = _extract_text_corpus(pages_content)
    corpus_lower = corpus.lower()

    if not corpus.strip():
        return CopyQualityRubricScore(
            brief_alignment=0.0,
            section_completeness=0.0,
            specificity_and_relevance=0.0,
            readability=0.0,
            tone_consistency=0.0,
            absence_of_unsupported_claims=10.0,
            absence_of_placeholders=10.0,
            overall_score=0.0,
            passed=False,
            detected_placeholders=[],
            details="No generated website copy found to evaluate.",
        )

    # 1. Absence of placeholders (0 - 10)
    detected: list[str] = []
    for pat in PLACEHOLDER_PATTERNS:
        matches = pat.findall(corpus)
        if matches:
            detected.extend(matches)
    placeholder_penalty = min(10.0, len(detected) * 2.5)
    absence_of_placeholders = round(max(0.0, 10.0 - placeholder_penalty), 2)

    # 2. Brief alignment (0 - 10)
    alignment_score = 0.0
    client_tokens = [tok.lower() for tok in brief.client_name.split() if len(tok) > 2]
    matched_client_tokens = sum(1 for tok in client_tokens if tok in corpus_lower)
    if matched_client_tokens > 0:
        alignment_score += (matched_client_tokens / max(1, len(client_tokens))) * 5.0
    else:
        # Check if full name present
        if brief.client_name.lower() in corpus_lower:
            alignment_score += 5.0

    site_type_tokens = [tok.lower() for tok in brief.site_type.split()]
    if any(tok in corpus_lower for tok in site_type_tokens):
        alignment_score += 3.0
    if len(corpus.split()) >= 80:
        alignment_score += 2.0
    brief_alignment = round(min(10.0, alignment_score), 2)

    # 3. Section completeness (0 - 10)
    # Check coverage of requested pages
    page_slugs: set[str] = set()
    for item in pages_content:
        data = (
            item
            if isinstance(item, dict)
            else (item.model_dump() if hasattr(item, "model_dump") else {})
        )
        if "page_slug" in data:
            page_slugs.add(str(data["page_slug"]).lower())
        elif "title" in data:
            page_slugs.add(str(data["title"]).lower())

    covered_pages = 0
    for p in brief.pages:
        norm = p.lower().strip()
        if (
            norm in page_slugs
            or any(norm in s for s in page_slugs)
            or norm in corpus_lower
        ):
            covered_pages += 1
    section_completeness = round(
        min(10.0, (covered_pages / max(1, len(brief.pages))) * 10.0), 2
    )

    # 4. Specificity & relevance (0 - 10)
    # Words in content_notes longer than 4 chars
    note_words = set(re.findall(r"\b[A-Za-z]{5,}\b", brief.content_notes.lower()))
    stop_words = {
        "their",
        "about",
        "which",
        "there",
        "would",
        "these",
        "other",
        "eight",
        "build",
        "years",
    }
    salient_words = note_words - stop_words
    matched_salient = sum(1 for w in salient_words if w in corpus_lower)
    specificity_ratio = (
        (matched_salient / max(1, len(salient_words))) if salient_words else 1.0
    )
    specificity_and_relevance = round(min(10.0, specificity_ratio * 10.0 + 2.0), 2)

    # 5. Readability (0 - 10)
    sentences = [s.strip() for s in re.split(r"[.!?]+", corpus) if s.strip()]
    if sentences:
        avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)
        # Optimal average length: 12 - 24 words
        if 10.0 <= avg_sentence_len <= 26.0:
            readability_val = 9.5
        elif 6.0 <= avg_sentence_len <= 35.0:
            readability_val = 8.0
        else:
            readability_val = 5.5
    else:
        readability_val = 5.0
    readability = round(readability_val, 2)

    # 6. Tone consistency (0 - 10)
    tone_key = brief.tone.lower()
    markers = TONE_MARKERS.get(tone_key, set())
    if markers:
        matched_markers = sum(1 for m in markers if m in corpus_lower)
        tone_score = min(10.0, 6.0 + (matched_markers * 1.5))
    else:
        tone_score = 8.0
    tone_consistency = round(tone_score, 2)

    # 7. Absence of unsupported claims (0 - 10)
    unsupported_detected: list[str] = []
    for pat in FABRICATED_CREDENTIAL_PATTERNS:
        matches = pat.findall(corpus)
        if matches and not pat.search(brief.content_notes):
            unsupported_detected.extend(matches)
    unsupported_penalty = min(10.0, len(unsupported_detected) * 3.5)
    absence_of_unsupported_claims = round(max(0.0, 10.0 - unsupported_penalty), 2)

    # Aggregate overall score
    dims = [
        brief_alignment,
        section_completeness,
        specificity_and_relevance,
        readability,
        tone_consistency,
        absence_of_unsupported_claims,
        absence_of_placeholders,
    ]
    overall = round(sum(dims) / len(dims), 2)
    passed = overall >= 7.0 and absence_of_placeholders >= 9.0

    details = (
        f"Copy quality score: {overall}/10 (passed={passed}). "
        f"Placeholders: {len(detected)}, "
        f"Unsupported claims: {len(unsupported_detected)}."
    )

    return CopyQualityRubricScore(
        brief_alignment=brief_alignment,
        section_completeness=section_completeness,
        specificity_and_relevance=specificity_and_relevance,
        readability=readability,
        tone_consistency=tone_consistency,
        absence_of_unsupported_claims=absence_of_unsupported_claims,
        absence_of_placeholders=absence_of_placeholders,
        overall_score=overall,
        passed=passed,
        detected_placeholders=detected,
        details=details,
    )
