from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..config import REVIEW_INTERVALS_DAYS
from ..models import AppSettings


LEARNING_MODE_OPTIONS = {"application", "dictation"}
STUDY_MATERIAL_THEME_OPTIONS = {"reader", "frost"}
DASHBOARD_DENSITY_OPTIONS = {"immersive", "balanced", "compact"}
MOTION_LEVEL_OPTIONS = {"full", "soft", "minimal"}
LEARNING_MODE_LABELS = {
    "application": "應用學習",
    "dictation": "默寫學習",
}
STUDY_MATERIAL_THEME_LABELS = {
    "reader": "閱讀紙頁",
    "frost": "霧面玻璃",
}
DASHBOARD_DENSITY_LABELS = {
    "immersive": "沉浸",
    "balanced": "平衡",
    "compact": "緊湊",
}
MOTION_LEVEL_LABELS = {
    "full": "完整",
    "soft": "柔和",
    "minimal": "極簡",
}


def get_app_settings(session: Session) -> AppSettings:
    settings = session.get(AppSettings, 1)
    if settings is not None:
        return settings

    settings = AppSettings(
        id=1,
        review_intervals_csv=",".join(str(value) for value in REVIEW_INTERVALS_DAYS),
    )
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def normalize_optional_date(raw_value: str, *, field_name: str) -> date | None:
    normalized = raw_value.strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name}必須是有效日期。") from exc


def normalize_review_intervals_csv(raw_value: str) -> str:
    values: list[int] = []
    for chunk in raw_value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.isdigit():
            raise ValueError("複習間隔必須是以逗號分隔的整數。")
        interval_days = int(chunk)
        if interval_days <= 0 or interval_days > 365:
            raise ValueError("複習間隔必須介於 1 到 365 天之間。")
        values.append(interval_days)

    if not values:
        raise ValueError("至少要填入一個複習間隔。")

    unique_values = sorted(set(values))
    return ",".join(str(value) for value in unique_values)


def update_app_settings(
    session: Session,
    *,
    default_priority: int,
    default_learning_mode: str,
    review_intervals_csv: str,
    low_confidence_followup_days: int,
    allow_weekend_scheduling: bool,
    render_math_enabled: bool,
    study_material_theme: str,
    dashboard_density: str,
    motion_level: str,
    queue_preview_count_study: int,
    queue_preview_count_review: int,
    dashboard_hero_title_text: str,
    dashboard_hero_title_size_px: int,
    dashboard_major_event_content: str,
    dashboard_major_event_date: str,
) -> AppSettings:
    settings = get_app_settings(session)
    normalized_hero_title = dashboard_hero_title_text.strip()
    normalized_major_event_content = dashboard_major_event_content.strip()
    normalized_major_event_date = normalize_optional_date(
        dashboard_major_event_date,
        field_name="重大事件日期",
    )

    settings.default_priority = _validate_allowed_int(
        default_priority,
        allowed_values={1, 2, 3},
        field_name="預設優先級",
    )
    settings.default_learning_mode = _validate_allowed_text(
        default_learning_mode,
        allowed_values=LEARNING_MODE_OPTIONS,
        field_name="預設學習模式",
        display_values=LEARNING_MODE_LABELS,
    )
    settings.review_intervals_csv = normalize_review_intervals_csv(review_intervals_csv)
    settings.low_confidence_followup_days = _validate_int_range(
        low_confidence_followup_days,
        minimum=1,
        maximum=30,
        field_name="低信心追加複習天數",
    )
    settings.allow_weekend_scheduling = bool(allow_weekend_scheduling)
    settings.render_math_enabled = bool(render_math_enabled)
    settings.study_material_theme = _validate_allowed_text(
        study_material_theme,
        allowed_values=STUDY_MATERIAL_THEME_OPTIONS,
        field_name="學習材料主題",
        display_values=STUDY_MATERIAL_THEME_LABELS,
    )
    settings.dashboard_density = _validate_allowed_text(
        dashboard_density,
        allowed_values=DASHBOARD_DENSITY_OPTIONS,
        field_name="儀表板密度",
        display_values=DASHBOARD_DENSITY_LABELS,
    )
    settings.motion_level = _validate_allowed_text(
        motion_level,
        allowed_values=MOTION_LEVEL_OPTIONS,
        field_name="動效強度",
        display_values=MOTION_LEVEL_LABELS,
    )
    settings.queue_preview_count_study = _validate_int_range(
        queue_preview_count_study,
        minimum=1,
        maximum=24,
        field_name="學習隊列預覽數量",
    )
    settings.queue_preview_count_review = _validate_int_range(
        queue_preview_count_review,
        minimum=1,
        maximum=24,
        field_name="複習隊列預覽數量",
    )
    settings.dashboard_hero_title_text = _validate_text_length(
        normalized_hero_title,
        minimum=1,
        maximum=160,
        field_name="儀表板大標題內容",
    )
    settings.dashboard_hero_title_size_px = _validate_int_range(
        dashboard_hero_title_size_px,
        minimum=1,
        maximum=120,
        field_name="儀表板大標題字體大小",
    )

    if bool(normalized_major_event_content) != bool(normalized_major_event_date):
        raise ValueError("重大事件內容與日期必須同時填寫，或兩者都留空。")

    if normalized_major_event_content:
        settings.dashboard_major_event_content = _validate_text_length(
            normalized_major_event_content,
            minimum=1,
            maximum=200,
            field_name="重大事件內容",
        )
        settings.dashboard_major_event_date = normalized_major_event_date
    else:
        settings.dashboard_major_event_content = None
        settings.dashboard_major_event_date = None

    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def _validate_int_range(value: int, *, minimum: int, maximum: int, field_name: str) -> int:
    if value < minimum or value > maximum:
        raise ValueError(f"{field_name}必須介於 {minimum} 到 {maximum} 之間。")
    return value


def _validate_allowed_int(value: int, *, allowed_values: set[int], field_name: str) -> int:
    if value not in allowed_values:
        allowed = "、".join(str(item) for item in sorted(allowed_values))
        raise ValueError(f"{field_name}只能是以下值之一：{allowed}。")
    return value


def _validate_allowed_text(
    value: str,
    *,
    allowed_values: set[str],
    field_name: str,
    display_values: dict[str, str] | None = None,
) -> str:
    normalized = value.strip().lower()
    if normalized not in allowed_values:
        if display_values:
            allowed = "、".join(display_values[key] for key in sorted(allowed_values))
        else:
            allowed = "、".join(sorted(allowed_values))
        raise ValueError(f"{field_name}只能是以下值之一：{allowed}。")
    return normalized


def _validate_text_length(value: str, *, minimum: int, maximum: int, field_name: str) -> str:
    length = len(value)
    if length < minimum or length > maximum:
        raise ValueError(f"{field_name}長度必須介於 {minimum} 到 {maximum} 個字元之間。")
    return value
