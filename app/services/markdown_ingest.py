from __future__ import annotations

import math
import re
import textwrap
import uuid
from dataclasses import dataclass


HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.*)$")
BOLD_ONLY_PATTERN = re.compile(r"^\*\*(.+?)\*\*$")
SPECIAL_UNIT_TITLE_PATTERN = re.compile(
    r"^(例題|例子|習題|练习|練習|定理|引理|定義|证明|證明|总结|總結|"
    r"example|exercise|problem|theorem|lemma|definition|proof|summary)\b",
    re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"\b[\w'-]+\b")
ENGLISH_STRUCTURAL_TITLE_PATTERN = re.compile(
    r"^(chapter|part|section)\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+|[a-z])(?:\b|[).:-])",
    re.IGNORECASE,
)
REFERENCE_TITLE_PATTERN = re.compile(
    r"^(references|reference|bibliography|works cited|citations)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ParsedUnit:
    title: str
    content_markdown: str
    heading_level: int
    order_index: int
    word_count: int
    estimated_minutes: int
    page_start: int | None = None
    page_end: int | None = None
    content_type: str = "section"


@dataclass(slots=True)
class UnitHint:
    title: str
    heading_level: int
    page_start: int | None = None
    page_end: int | None = None
    content_type: str = "section"


def slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return base or "resource"


def unique_slug(title: str) -> str:
    return f"{slugify(title)}-{uuid.uuid4().hex[:8]}"


def split_markdown_into_units(markdown_text: str, unit_hints: list[UnitHint] | None = None) -> list[ParsedUnit]:
    lines = markdown_text.splitlines()
    segments: list[tuple[str, int, list[str]]] = []
    current_title = "匯入內容"
    current_level = 2
    current_lines: list[str] = []

    for line in lines:
        heading_info = parse_unit_heading(line)
        if heading_info:
            if current_lines:
                segments.append((current_title, current_level, current_lines))
            current_level, current_title = heading_info
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines:
        segments.append((current_title, current_level, current_lines))

    cleaned_segments = [
        (title, level, "\n".join(segment_lines).strip())
        for title, level, segment_lines in segments
        if "\n".join(segment_lines).strip()
    ]
    cleaned_segments = prune_non_study_segments(cleaned_segments)

    if not cleaned_segments:
        cleaned_segments = [("匯入內容", 2, markdown_text.strip())]

    aligned_hints = align_unit_hints(cleaned_segments, unit_hints or [])
    units: list[ParsedUnit] = []
    for index, ((title, level, content), hint) in enumerate(zip(cleaned_segments, aligned_hints), start=1):
        normalized = textwrap.dedent(content).strip()
        word_count = count_words(normalized)
        units.append(
            ParsedUnit(
                title=title,
                content_markdown=normalized,
                heading_level=hint.heading_level if hint else level,
                order_index=index,
                word_count=word_count,
                estimated_minutes=estimate_minutes(word_count),
                page_start=hint.page_start if hint else None,
                page_end=hint.page_end if hint else None,
                content_type=hint.content_type if hint else infer_content_type(title),
            )
        )

    return units


def prune_non_study_segments(
    cleaned_segments: list[tuple[str, int, str]],
) -> list[tuple[str, int, str]]:
    if not cleaned_segments:
        return cleaned_segments

    pruned_segments = list(cleaned_segments)
    if len(pruned_segments) >= 2 and is_front_matter_title_segment(
        pruned_segments[0],
        pruned_segments[1],
    ):
        pruned_segments = pruned_segments[1:]

    if pruned_segments and is_reference_segment(pruned_segments[-1]):
        pruned_segments = pruned_segments[:-1]

    return pruned_segments


def is_front_matter_title_segment(
    current_segment: tuple[str, int, str],
    next_segment: tuple[str, int, str],
) -> bool:
    title, _level, content = current_segment
    next_title, _next_level, _next_content = next_segment
    normalized_title = normalize_title(title)
    normalized_next_title = normalize_title(next_title)

    if not normalized_title or not normalized_next_title:
        return False
    if count_words(content) > 60:
        return False
    if normalized_title == normalized_next_title:
        return False
    if ENGLISH_STRUCTURAL_TITLE_PATTERN.match(normalized_title) or re.match(r"^\d", normalized_title):
        return False
    if not (
        ENGLISH_STRUCTURAL_TITLE_PATTERN.match(normalized_next_title)
        or re.match(r"^\d+(?:\.\d+)*\b", normalized_next_title)
        or normalized_next_title.startswith("introduction")
    ):
        return False
    return True


def is_reference_segment(segment: tuple[str, int, str]) -> bool:
    title, _level, content = segment
    normalized_title = re.sub(r"^\d+(?:\.\d+)*[\s).:-]*", "", normalize_title(title))
    return bool(REFERENCE_TITLE_PATTERN.match(normalized_title)) and count_words(content) <= 400


def parse_unit_heading(line: str) -> tuple[int, str] | None:
    stripped = line.strip()
    if not stripped:
        return None

    heading_match = HEADING_PATTERN.match(stripped)
    if heading_match:
        return len(heading_match.group(1)), heading_match.group(2).strip()

    bold_match = BOLD_ONLY_PATTERN.match(stripped)
    candidate = bold_match.group(1).strip() if bold_match else stripped
    if looks_like_special_unit_title(candidate):
        return infer_heading_level_from_title(candidate), candidate

    return None


def looks_like_special_unit_title(text: str) -> bool:
    normalized = normalize_title(text)
    if not normalized or len(normalized) > 120:
        return False
    if SPECIAL_UNIT_TITLE_PATTERN.match(normalized):
        return True
    if re.match(r"^第[0-9一二三四五六七八九十百千]+[章节篇部]", normalized):
        return True
    if ENGLISH_STRUCTURAL_TITLE_PATTERN.match(normalized):
        return True
    if re.match(r"^\d+(\.\d+){1,3}\b", normalized):
        return True
    return False


def align_unit_hints(
    cleaned_segments: list[tuple[str, int, str]],
    unit_hints: list[UnitHint],
) -> list[UnitHint | None]:
    if not unit_hints:
        return [None] * len(cleaned_segments)

    if len(unit_hints) == len(cleaned_segments):
        return list(unit_hints)

    aligned: list[UnitHint | None] = []
    hint_index = 0
    for title, _level, _content in cleaned_segments:
        normalized_title = normalize_title(title)
        matched_hint: UnitHint | None = None
        while hint_index < len(unit_hints):
            candidate = unit_hints[hint_index]
            hint_index += 1
            if normalize_title(candidate.title) == normalized_title:
                matched_hint = candidate
                break
        aligned.append(matched_hint)
    return aligned


def normalize_title(text: str) -> str:
    compact = re.sub(r"\s+", " ", text.strip())
    compact = compact.strip("*#` ")
    return compact.casefold()


def infer_content_type(title: str) -> str:
    normalized = normalize_title(title)
    if re.match(r"^(例題|例子|example)\b", normalized, re.IGNORECASE):
        return "example"
    if re.match(r"^(練習|练习|習題|exercise|problem)\b", normalized, re.IGNORECASE):
        return "exercise"
    if re.match(r"^(定理|引理|theorem|lemma)\b", normalized, re.IGNORECASE):
        return "theorem"
    if re.match(r"^(定義|definition)\b", normalized, re.IGNORECASE):
        return "definition"
    if re.match(r"^(證明|证明|proof)\b", normalized, re.IGNORECASE):
        return "proof"
    if re.match(r"^(總結|总结|summary)\b", normalized, re.IGNORECASE):
        return "summary"
    return "section"


def infer_heading_level_from_title(title: str) -> int:
    normalized = normalize_title(title)
    if re.match(r"^第[0-9一二三四五六七八九十百千]+章", normalized):
        return 1
    if re.match(r"^(chapter|part)\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+|[a-z])(?:\b|[).:-])", normalized, re.IGNORECASE):
        return 1
    if re.match(r"^\d+\.\d+\.\d+", normalized):
        return 3
    if re.match(r"^第[0-9一二三四五六七八九十百千]+节", normalized):
        return 2
    if re.match(r"^section\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+|[a-z])(?:\b|[).:-])", normalized, re.IGNORECASE):
        return 2
    if re.match(r"^\d+\.\d+", normalized):
        return 2
    if infer_content_type(title) != "section":
        return 3
    return 2


def count_words(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def estimate_minutes(word_count: int) -> int:
    if word_count <= 0:
        return 12
    return max(12, min(45, math.ceil(word_count / 200 * 15)))
