from __future__ import annotations

import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from markdown import markdown
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..config import RESOURCES_DIR
from ..models import CheckIn, DailyTask, LearningUnit, Resource, ReviewTask, StudyPlan
from .markdown_ingest import UnitHint, split_markdown_into_units, unique_slug
from .pdf_ingest import load_pdf_source, write_pdf_artifacts
from .scheduler import SchedulableUnit, build_study_schedule


LEARNING_MODES = {"application", "dictation"}
MATH_PATTERN = re.compile(r"(\$\$.*?\$\$|\$[^$\n]+\$|\\\(.+?\\\)|\\\[.+?\\\])", re.DOTALL)


@dataclass(slots=True)
class DashboardSummary:
    today: date
    study_due: list[DailyTask]
    review_due: list[ReviewTask]
    resources: list[Resource]
    due_today_count: int
    overdue_count: int
    completed_today_count: int
    active_resource_count: int


def normalize_local_source_path(source_path: str) -> str:
    normalized = source_path.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        normalized = normalized[1:-1].strip()
    return normalized


def validate_resource_plan_inputs(
    *,
    title: str,
    description: str,
    source_path: str,
    priority: int,
    learning_mode: str,
) -> tuple[str, str, str]:
    normalized_title = title.strip()
    normalized_description = description.strip()
    normalized_source_path = normalize_local_source_path(source_path)

    if not normalized_title:
        raise ValueError("標題不能為空。")
    if priority not in {1, 2, 3}:
        raise ValueError("優先級只能是 1、2 或 3。")
    if learning_mode not in LEARNING_MODES:
        raise ValueError("學習模式只能是應用學習或需要默寫。")
    if not normalized_source_path:
        raise ValueError("請提供本地檔案路徑。")

    return normalized_title, normalized_description, normalized_source_path


def persist_resource_plan(
    session: Session,
    *,
    title: str,
    description: str,
    source_reference: str,
    deadline: date,
    priority: int,
    learning_mode: str,
    review_intervals_csv: str,
    allow_weekend_scheduling: bool,
    markdown_text: str,
    unit_hints: list[UnitHint],
    resource_dir: Path,
) -> Resource:
    resource_id = str(uuid.uuid4())
    slug = resource_dir.name
    units = split_markdown_into_units(markdown_text, unit_hints=unit_hints)

    start_date = date.today()
    scheduled_units = build_study_schedule(
        [
            SchedulableUnit(
                order_index=unit.order_index,
                estimated_minutes=unit.estimated_minutes,
            )
            for unit in units
        ],
        start_date=start_date,
        deadline=deadline,
        allow_weekend_scheduling=allow_weekend_scheduling,
    )

    markdown_path = resource_dir / "source.md"
    markdown_path.write_text(markdown_text, encoding="utf-8")

    resource = Resource(
        id=resource_id,
        title=title,
        slug=slug,
        source_type="pdf_file",
        source_path_or_url=source_reference,
        stored_markdown_path=str(markdown_path),
        description=description or None,
        priority=priority,
        learning_mode=learning_mode,
    )
    resource.study_plan = StudyPlan(
        id=str(uuid.uuid4()),
        resource_id=resource.id,
        start_date=start_date,
        deadline=deadline,
        daily_capacity_minutes=0,
        review_intervals_csv=review_intervals_csv,
    )

    unit_map: dict[int, LearningUnit] = {}
    for parsed in units:
        unit = LearningUnit(
            id=str(uuid.uuid4()),
            resource_id=resource.id,
            title=parsed.title,
            order_index=parsed.order_index,
            heading_level=parsed.heading_level,
            content_type=parsed.content_type,
            estimated_minutes=parsed.estimated_minutes,
            word_count=parsed.word_count,
            page_start=parsed.page_start,
            page_end=parsed.page_end,
            content_markdown=parsed.content_markdown,
        )
        resource.learning_units.append(unit)
        unit_map[parsed.order_index] = unit

    for scheduled in scheduled_units:
        unit_map[scheduled.order_index].daily_tasks.append(
            DailyTask(
                id=str(uuid.uuid4()),
                due_date=scheduled.due_date,
                scheduled_minutes=scheduled.scheduled_minutes,
            )
        )

    session.add(resource)
    session.commit()
    session.refresh(resource)
    return resource


def create_resource_plan(
    session: Session,
    *,
    title: str,
    description: str,
    source_path: str,
    deadline: date,
    priority: int,
    learning_mode: str,
    review_intervals_csv: str,
    allow_weekend_scheduling: bool,
) -> Resource:
    title, description, source_path = validate_resource_plan_inputs(
        title=title,
        description=description,
        source_path=source_path,
        priority=priority,
        learning_mode=learning_mode,
    )

    slug = unique_slug(title)
    resource_dir = RESOURCES_DIR / slug
    resource_dir.mkdir(parents=True, exist_ok=True)

    try:
        markdown_text, source_reference, unit_hints = load_pdf_source(
            source_path,
            artifact_dir=resource_dir,
        )
        return persist_resource_plan(
            session,
            title=title,
            description=description,
            source_reference=source_reference,
            deadline=deadline,
            priority=priority,
            learning_mode=learning_mode,
            review_intervals_csv=review_intervals_csv,
            allow_weekend_scheduling=allow_weekend_scheduling,
            markdown_text=markdown_text,
            unit_hints=unit_hints,
            resource_dir=resource_dir,
        )
    except Exception:
        shutil.rmtree(resource_dir, ignore_errors=True)
        raise


def create_resource_plan_from_pdf_structure(
    session: Session,
    *,
    title: str,
    description: str,
    source_path: str,
    deadline: date,
    priority: int,
    learning_mode: str,
    review_intervals_csv: str,
    allow_weekend_scheduling: bool,
    markdown_text: str,
    unit_hints: list[UnitHint],
) -> Resource:
    title, description, source_path = validate_resource_plan_inputs(
        title=title,
        description=description,
        source_path=source_path,
        priority=priority,
        learning_mode=learning_mode,
    )

    slug = unique_slug(title)
    resource_dir = RESOURCES_DIR / slug
    resource_dir.mkdir(parents=True, exist_ok=True)

    try:
        pdf_path = Path(source_path).expanduser()
        if pdf_path.exists() and pdf_path.suffix.lower() == ".pdf":
            write_pdf_artifacts(pdf_path, markdown_text, unit_hints, artifact_dir=resource_dir)

        return persist_resource_plan(
            session,
            title=title,
            description=description,
            source_reference=source_path,
            deadline=deadline,
            priority=priority,
            learning_mode=learning_mode,
            review_intervals_csv=review_intervals_csv,
            allow_weekend_scheduling=allow_weekend_scheduling,
            markdown_text=markdown_text,
            unit_hints=unit_hints,
            resource_dir=resource_dir,
        )
    except Exception:
        shutil.rmtree(resource_dir, ignore_errors=True)
        raise


def get_dashboard_summary(session: Session, today: date | None = None) -> DashboardSummary:
    today = today or date.today()
    resource_query = (
        select(Resource)
        .options(
            joinedload(Resource.study_plan),
            joinedload(Resource.learning_units).joinedload(LearningUnit.daily_tasks),
            joinedload(Resource.learning_units).joinedload(LearningUnit.review_tasks),
        )
        .order_by(Resource.priority.desc(), Resource.imported_at.desc())
    )
    resources = list(session.scalars(resource_query).unique())

    study_due: list[DailyTask] = []
    review_due: list[ReviewTask] = []
    overdue_count = 0
    completed_today_count = 0

    for resource in resources:
        for unit in resource.learning_units:
            for task in unit.daily_tasks:
                if task.completed_at and task.completed_at.date() == today:
                    completed_today_count += 1
                if task.status != "completed" and task.due_date <= today:
                    study_due.append(task)
                    if task.due_date < today:
                        overdue_count += 1

            for review in unit.review_tasks:
                if review.completed_at and review.completed_at.date() == today:
                    completed_today_count += 1
                if review.status != "completed" and review.due_date <= today:
                    review_due.append(review)
                    if review.due_date < today:
                        overdue_count += 1

    study_due.sort(key=lambda task: (task.due_date, task.unit.resource.priority * -1, task.unit.order_index))
    review_due.sort(key=lambda review: (review.due_date, review.unit.resource.priority * -1, review.unit.order_index))

    return DashboardSummary(
        today=today,
        study_due=study_due,
        review_due=review_due,
        resources=resources,
        due_today_count=len([task for task in study_due if task.due_date == today])
        + len([review for review in review_due if review.due_date == today]),
        overdue_count=overdue_count,
        completed_today_count=completed_today_count,
        active_resource_count=len(resources),
    )


def get_resource(session: Session, resource_id: str) -> Resource | None:
    query = (
        select(Resource)
        .where(Resource.id == resource_id)
        .options(
            joinedload(Resource.study_plan),
            joinedload(Resource.learning_units).joinedload(LearningUnit.daily_tasks),
            joinedload(Resource.learning_units).joinedload(LearningUnit.review_tasks),
            joinedload(Resource.learning_units).joinedload(LearningUnit.check_ins),
        )
    )
    return session.scalars(query).unique().first()


def get_daily_task(session: Session, task_id: str) -> DailyTask | None:
    query = (
        select(DailyTask)
        .where(DailyTask.id == task_id)
        .options(
            joinedload(DailyTask.unit).joinedload(LearningUnit.resource).joinedload(Resource.study_plan),
            joinedload(DailyTask.unit).joinedload(LearningUnit.check_ins),
        )
    )
    return session.scalars(query).unique().first()


def get_review_task(session: Session, review_id: str) -> ReviewTask | None:
    query = (
        select(ReviewTask)
        .where(ReviewTask.id == review_id)
        .options(
            joinedload(ReviewTask.unit).joinedload(LearningUnit.resource).joinedload(Resource.study_plan),
            joinedload(ReviewTask.unit).joinedload(LearningUnit.check_ins),
        )
    )
    return session.scalars(query).unique().first()


def review_is_available(review: ReviewTask, today: date | None = None) -> bool:
    return review.due_date <= (today or date.today())


def complete_daily_task(
    session: Session,
    *,
    task_id: str,
    summary_text: str,
    reflection_note: str,
    confidence_score: int,
    completion_percent: int,
) -> DailyTask:
    task = get_daily_task(session, task_id)
    if task is None:
        raise ValueError("找不到這個學習任務。")
    if task.status == "completed":
        return task
    if not summary_text.strip():
        raise ValueError("要完成任務，必須填寫一段簡短總結。")

    completed_at = datetime.utcnow()
    task.status = "completed"
    task.completed_at = completed_at
    task.unit.status = "completed"

    if task.unit.first_completed_at is None:
        task.unit.first_completed_at = completed_at
        plan = task.unit.resource.study_plan
        intervals = [int(item) for item in plan.review_intervals_csv.split(",") if item]
        for interval_days in intervals:
            task.unit.review_tasks.append(
                ReviewTask(
                    id=str(uuid.uuid4()),
                    due_date=completed_at.date() + timedelta(days=interval_days),
                    interval_days=interval_days,
                )
            )

    task.unit.check_ins.append(
        CheckIn(
            id=str(uuid.uuid4()),
            unit_id=task.unit.id,
            daily_task_id=task.id,
            kind="study",
            summary_text=summary_text.strip(),
            reflection_note=reflection_note.strip() or None,
            confidence_score=confidence_score,
            completion_percent=completion_percent,
            completed_at=completed_at,
        )
    )

    _refresh_resource_status(task.unit.resource)
    session.commit()
    session.refresh(task)
    return task


def complete_review_task(
    session: Session,
    *,
    review_id: str,
    summary_text: str,
    reflection_note: str,
    confidence_score: int,
    low_confidence_followup_days: int,
) -> ReviewTask:
    review = get_review_task(session, review_id)
    if review is None:
        raise ValueError("找不到這個複習任務。")
    if not review_is_available(review):
        raise ValueError("這個複習任務還沒有解鎖。")
    if review.status == "completed":
        return review
    if not summary_text.strip():
        raise ValueError("要完成複習，必須填寫一段簡短回憶總結。")
    if low_confidence_followup_days <= 0:
        raise ValueError("低信心追蹤複習天數必須大於 0。")

    completed_at = datetime.utcnow()
    review.status = "completed"
    review.completed_at = completed_at
    review.unit.check_ins.append(
        CheckIn(
            id=str(uuid.uuid4()),
            unit_id=review.unit.id,
            review_task_id=review.id,
            kind="review",
            summary_text=summary_text.strip(),
            reflection_note=reflection_note.strip() or None,
            confidence_score=confidence_score,
            completion_percent=100,
            completed_at=completed_at,
        )
    )

    if confidence_score <= 2:
        existing_due_dates = {task.due_date for task in review.unit.review_tasks if task.status != "completed"}
        follow_up_date = completed_at.date() + timedelta(days=low_confidence_followup_days)
        if follow_up_date not in existing_due_dates:
            review.unit.review_tasks.append(
                ReviewTask(
                    id=str(uuid.uuid4()),
                    due_date=follow_up_date,
                    interval_days=low_confidence_followup_days,
                )
            )

    session.commit()
    session.refresh(review)
    return review


def render_markdown(markdown_text: str) -> str:
    return markdown(markdown_text, extensions=["extra", "sane_lists"])


def content_has_math(markdown_text: str) -> bool:
    return bool(MATH_PATTERN.search(markdown_text))


def _refresh_resource_status(resource: Resource) -> None:
    daily_tasks = [task for unit in resource.learning_units for task in unit.daily_tasks]
    if daily_tasks and all(task.status == "completed" for task in daily_tasks):
        resource.status = "in_review"
