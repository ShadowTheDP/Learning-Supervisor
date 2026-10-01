from __future__ import annotations

import math
import re
import textwrap
import uuid
from collections import defaultdict
from dataclasses import dataclass


HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.*)$")
BOLD_ONLY_PATTERN = re.compile(r"^\*\*(.+?)\*\*$")
ENGLISH_PART_TITLE_PATTERN = re.compile(
    r"^part\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+|[a-z])(?:\b|[).:-])",
    re.IGNORECASE,
)
ENGLISH_CHAPTER_TITLE_PATTERN = re.compile(
    r"^chapter\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+|[a-z])(?:\b|[).:-])",
    re.IGNORECASE,
)
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


def clone_unit_hint(hint: UnitHint) -> UnitHint:
    return UnitHint(
        title=hint.title,
        heading_level=hint.heading_level,
        page_start=hint.page_start,
        page_end=hint.page_end,
        content_type=hint.content_type,
    )


def clone_unit_hints(unit_hints: list[UnitHint]) -> list[UnitHint]:
    return [clone_unit_hint(hint) for hint in unit_hints]


def unit_hint_page_extent(hint: UnitHint) -> int | None:
    if hint.page_end is not None:
        return hint.page_end
    return hint.page_start


def slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return base or "resource"


def unique_slug(title: str) -> str:
    return f"{slugify(title)}-{uuid.uuid4().hex[:8]}"


def split_markdown_into_units(markdown_text: str, unit_hints: list[UnitHint] | None = None) -> list[ParsedUnit]:
    lines = markdown_text.splitlines()
    selected_hints = select_primary_unit_hints(unit_hints or [])
    active_hints = unit_hints or []
    cleaned_segments: list[tuple[str, int, str]] = []
    if len(selected_hints) >= 2:
        candidate_segments = split_markdown_by_selected_hints(lines, selected_hints)
        if len(candidate_segments) == len(selected_hints):
            cleaned_segments = candidate_segments
            active_hints = selected_hints
    if not cleaned_segments:
        cleaned_segments = collect_markdown_segments(lines)
    cleaned_segments = prune_non_study_segments(cleaned_segments)

    if not cleaned_segments:
        cleaned_segments = [("匯入內容", 2, markdown_text.strip())]

    aligned_hints = align_unit_hints(cleaned_segments, active_hints)
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
    explicit_heading = parse_explicit_unit_heading(line)
    if explicit_heading:
        return explicit_heading

    stripped = line.strip()
    if not stripped:
        return None

    if looks_like_structural_unit_title(stripped):
        return infer_heading_level_from_title(stripped), stripped

    return None


def extract_explicit_heading_text(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None

    heading_match = HEADING_PATTERN.match(stripped)
    if heading_match:
        return heading_match.group(2).strip()

    bold_match = BOLD_ONLY_PATTERN.match(stripped)
    if bold_match:
        return bold_match.group(1).strip()

    return None


def parse_explicit_unit_heading(line: str) -> tuple[int, str] | None:
    explicit_title = extract_explicit_heading_text(line)
    if not explicit_title:
        return None

    stripped = line.strip()
    heading_match = HEADING_PATTERN.match(stripped)
    if heading_match:
        return len(heading_match.group(1)), explicit_title

    if not looks_like_structural_unit_title(explicit_title):
        return None

    return infer_heading_level_from_title(explicit_title), explicit_title


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


def looks_like_structural_unit_title(text: str) -> bool:
    normalized = normalize_title(text)
    if not normalized or len(normalized) > 120:
        return False
    if ENGLISH_PART_TITLE_PATTERN.match(normalized):
        return True
    if ENGLISH_CHAPTER_TITLE_PATTERN.match(normalized):
        return True
    if re.match(r"^第[0-9一二三四五六七八九十百千]+[章节篇部]", normalized):
        return True
    if ENGLISH_STRUCTURAL_TITLE_PATTERN.match(normalized):
        return True
    if re.match(r"^\d+(\.\d+){1,3}\b", normalized):
        return True
    return False


def collect_markdown_segments(lines: list[str]) -> list[tuple[str, int, str]]:
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

    return [
        (title, level, "\n".join(segment_lines).strip())
        for title, level, segment_lines in segments
        if "\n".join(segment_lines).strip()
    ]


def split_markdown_by_selected_hints(
    lines: list[str],
    unit_hints: list[UnitHint],
) -> list[tuple[str, int, str]]:
    if not unit_hints:
        return []

    hints_by_title: dict[str, list[UnitHint]] = defaultdict(list)
    for hint in unit_hints:
        hints_by_title[normalize_title(hint.title)].append(hint)
    current_hint: UnitHint | None = None
    current_lines: list[str] = []
    segments: list[tuple[str, int, str]] = []

    for line in lines:
        explicit_title = extract_explicit_heading_text(line)
        if explicit_title:
            matching_hints = hints_by_title.get(normalize_title(explicit_title), [])
            matched_hint = matching_hints.pop(0) if matching_hints else None
            if matched_hint is not None:
                if current_hint is not None:
                    content = "\n".join(current_lines).strip()
                    if content:
                        segments.append((current_hint.title, current_hint.heading_level, content))
                current_hint = matched_hint
                current_lines = []
                continue
        if current_hint is not None:
            current_lines.append(line)

    if current_hint is not None:
        content = "\n".join(current_lines).strip()
        if content:
            segments.append((current_hint.title, current_hint.heading_level, content))

    return segments


def select_primary_unit_hints(unit_hints: list[UnitHint]) -> list[UnitHint]:
    if not unit_hints:
        return []

    deduped_hints = deduplicate_unit_hints(unit_hints)
    chapter_hints = [hint for hint in deduped_hints if is_chapter_like_hint(hint)]
    if len(chapter_hints) >= 2:
        return expand_selected_hint_ranges(chapter_hints, deduped_hints)

    structural_hints = [
        hint
        for hint in deduped_hints
        if hint.content_type == "section" and not is_reference_segment((hint.title, hint.heading_level, ""))
    ]
    if len(structural_hints) >= 3:
        top_level = min(hint.heading_level for hint in structural_hints)
        top_level_hints = [hint for hint in structural_hints if hint.heading_level == top_level]
        if len(top_level_hints) >= 2:
            return expand_selected_hint_ranges(top_level_hints, deduped_hints)

    return clone_unit_hints(deduped_hints)


def deduplicate_unit_hints(unit_hints: list[UnitHint]) -> list[UnitHint]:
    deduped: list[UnitHint] = []
    for hint in unit_hints:
        if deduped and normalize_title(deduped[-1].title) == normalize_title(hint.title):
            continue
        deduped.append(hint)
    return deduped


def match_hint_positions(source_hints: list[UnitHint], selected_hints: list[UnitHint]) -> list[int | None]:
    positions: list[int | None] = []
    search_start = 0
    for selected_hint in selected_hints:
        matched_position: int | None = None
        normalized_title = normalize_title(selected_hint.title)
        for position in range(search_start, len(source_hints)):
            candidate = source_hints[position]
            if candidate.heading_level != selected_hint.heading_level:
                continue
            if normalize_title(candidate.title) != normalized_title:
                continue
            matched_position = position
            search_start = position + 1
            break
        positions.append(matched_position)
    return positions


def expand_selected_hint_ranges(
    selected_hints: list[UnitHint],
    all_hints: list[UnitHint],
) -> list[UnitHint]:
    if not selected_hints:
        return []

    hint_positions = match_hint_positions(all_hints, selected_hints)
    expanded_hints: list[UnitHint] = []

    for index, selected_hint in enumerate(selected_hints):
        current_position = hint_positions[index]
        expanded_hint = clone_unit_hint(selected_hint)
        if current_position is None:
            expanded_hints.append(expanded_hint)
            continue

        next_position = len(all_hints)
        for candidate_position in hint_positions[index + 1 :]:
            if candidate_position is not None:
                next_position = candidate_position
                break

        covered_hints = all_hints[current_position:next_position]
        start_candidates = [
            hint.page_start for hint in covered_hints if hint.page_start is not None
        ]
        end_candidates = [
            extent
            for hint in covered_hints
            if (extent := unit_hint_page_extent(hint)) is not None
        ]

        if start_candidates:
            expanded_hint.page_start = min(start_candidates)
        if end_candidates:
            expanded_hint.page_end = max(end_candidates)
            if expanded_hint.page_start is not None and expanded_hint.page_end < expanded_hint.page_start:
                expanded_hint.page_end = expanded_hint.page_start
        if next_position < len(all_hints):
            next_hint_start = all_hints[next_position].page_start
            if next_hint_start is not None:
                inferred_end = next_hint_start - 1
                if expanded_hint.page_start is not None and inferred_end >= expanded_hint.page_start:
                    if expanded_hint.page_end is None or inferred_end > expanded_hint.page_end:
                        expanded_hint.page_end = inferred_end

        expanded_hints.append(expanded_hint)

    return expanded_hints


def is_chapter_like_hint(hint: UnitHint) -> bool:
    if hint.content_type != "section":
        return False
    normalized_title = normalize_title(hint.title)
    return bool(
        ENGLISH_CHAPTER_TITLE_PATTERN.match(normalized_title)
        or re.match(r"^第[0-9一二三四五六七八九十百千]+章", normalized_title)
    )


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
