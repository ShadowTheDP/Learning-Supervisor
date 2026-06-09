from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now_utc() -> datetime:
    return datetime.utcnow()


def _status_label(status: str) -> str:
    return {
        "active": "進行中",
        "scheduled": "已排程",
        "completed": "已完成",
        "in_review": "複習中",
    }.get(status, status)


def _source_type_label(source_type: str) -> str:
    return {
        "pdf_file": "PDF 檔案",
    }.get(source_type, source_type.replace("_", " "))


def _content_type_label(content_type: str) -> str:
    return {
        "section": "章節",
        "example": "例題",
        "exercise": "練習",
        "theorem": "定理",
        "definition": "定義",
        "proof": "證明",
        "summary": "總結",
    }.get(content_type, content_type.replace("_", " "))


def _learning_mode_label(learning_mode: str) -> str:
    if learning_mode == "dictation":
        return "需要默寫"
    return "應用學習"


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_daily_capacity_minutes: Mapped[int] = mapped_column(Integer, default=45)
    default_priority: Mapped[int] = mapped_column(Integer, default=2)
    default_learning_mode: Mapped[str] = mapped_column(String(32), default="application")
    review_intervals_csv: Mapped[str] = mapped_column(String(64), default="1,3,7,14")
    low_confidence_followup_days: Mapped[int] = mapped_column(Integer, default=2)
    allow_weekend_scheduling: Mapped[bool] = mapped_column(Boolean, default=True)
    render_math_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    study_material_theme: Mapped[str] = mapped_column(String(32), default="reader")
    dashboard_density: Mapped[str] = mapped_column(String(32), default="balanced")
    motion_level: Mapped[str] = mapped_column(String(32), default="full")
    queue_preview_count_study: Mapped[int] = mapped_column(Integer, default=8)
    queue_preview_count_review: Mapped[int] = mapped_column(Integer, default=6)
    dashboard_hero_title_text: Mapped[str] = mapped_column(String(160), default="今日學習總覽")
    dashboard_hero_title_size_px: Mapped[int] = mapped_column(Integer, default=72)
    dashboard_major_event_content: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dashboard_major_event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32))
    source_path_or_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    stored_markdown_path: Mapped[str] = mapped_column(Text)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(32), default="active")
    learning_mode: Mapped[str] = mapped_column(String(32), default="application")

    study_plan: Mapped["StudyPlan"] = relationship(
        back_populates="resource",
        uselist=False,
        cascade="all, delete-orphan",
    )
    learning_units: Mapped[list["LearningUnit"]] = relationship(
        back_populates="resource",
        cascade="all, delete-orphan",
        order_by="LearningUnit.order_index",
    )

    @property
    def learning_mode_label(self) -> str:
        return _learning_mode_label(self.learning_mode)

    @property
    def status_label(self) -> str:
        return _status_label(self.status)

    @property
    def source_type_label(self) -> str:
        return _source_type_label(self.source_type)


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), unique=True)
    start_date: Mapped[date] = mapped_column(Date)
    deadline: Mapped[date] = mapped_column(Date)
    daily_capacity_minutes: Mapped[int] = mapped_column(Integer)
    review_intervals_csv: Mapped[str] = mapped_column(String(64), default="1,3,7,14")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    resource: Mapped[Resource] = relationship(back_populates="study_plan")


class LearningUnit(Base):
    __tablename__ = "learning_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    order_index: Mapped[int] = mapped_column(Integer)
    heading_level: Mapped[int] = mapped_column(Integer, default=2)
    content_type: Mapped[str] = mapped_column(String(32), default="section")
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    first_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    resource: Mapped[Resource] = relationship(back_populates="learning_units")
    daily_tasks: Mapped[list["DailyTask"]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="DailyTask.due_date",
    )
    review_tasks: Mapped[list["ReviewTask"]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="ReviewTask.due_date",
    )
    check_ins: Mapped[list["CheckIn"]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="CheckIn.completed_at",
    )

    @property
    def status_label(self) -> str:
        return _status_label(self.status)

    @property
    def content_type_label(self) -> str:
        return _content_type_label(self.content_type)

    @property
    def page_range_label(self) -> str:
        if self.page_start is None:
            return ""
        if self.page_end is None or self.page_end <= self.page_start:
            return f"第 {self.page_start} 頁"
        return f"第 {self.page_start}-{self.page_end} 頁"


class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("learning_units.id"), index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    scheduled_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    unit: Mapped[LearningUnit] = relationship(back_populates="daily_tasks")
    check_ins: Mapped[list["CheckIn"]] = relationship(back_populates="daily_task")


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("learning_units.id"), index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    interval_days: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    unit: Mapped[LearningUnit] = relationship(back_populates="review_tasks")
    check_ins: Mapped[list["CheckIn"]] = relationship(back_populates="review_task")


class CheckIn(Base):
    __tablename__ = "check_ins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("learning_units.id"), index=True)
    daily_task_id: Mapped[str | None] = mapped_column(ForeignKey("daily_tasks.id"), nullable=True)
    review_task_id: Mapped[str | None] = mapped_column(ForeignKey("review_tasks.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))
    summary_text: Mapped[str] = mapped_column(Text)
    reflection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer)
    completion_percent: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    unit: Mapped[LearningUnit] = relationship(back_populates="check_ins")
    daily_task: Mapped[DailyTask | None] = relationship(back_populates="check_ins")
    review_task: Mapped[ReviewTask | None] = relationship(back_populates="check_ins")

    @property
    def kind_label(self) -> str:
        return {
            "study": "學習",
            "review": "複習",
        }.get(self.kind, self.kind)
