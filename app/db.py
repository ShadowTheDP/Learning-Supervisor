from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DB_PATH, ensure_runtime_dirs


ensure_runtime_dirs()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def initialize_database() -> None:
    from .models import Base as ModelBase

    ModelBase.metadata.create_all(bind=engine)
    _apply_sqlite_migrations()


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _apply_sqlite_migrations() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        if "resources" in table_names:
            resource_columns = {column["name"] for column in inspector.get_columns("resources")}
            if "learning_mode" not in resource_columns:
                connection.execute(
                    text(
                        "ALTER TABLE resources "
                        "ADD COLUMN learning_mode VARCHAR(32) NOT NULL DEFAULT 'application'"
                    )
                )
        if "learning_units" in table_names:
            learning_unit_columns = {column["name"] for column in inspector.get_columns("learning_units")}
            learning_unit_migrations = (
                (
                    "content_type",
                    "ALTER TABLE learning_units "
                    "ADD COLUMN content_type VARCHAR(32) NOT NULL DEFAULT 'section'",
                ),
                (
                    "page_start",
                    "ALTER TABLE learning_units "
                    "ADD COLUMN page_start INTEGER",
                ),
                (
                    "page_end",
                    "ALTER TABLE learning_units "
                    "ADD COLUMN page_end INTEGER",
                ),
            )
            for column_name, statement in learning_unit_migrations:
                if column_name not in learning_unit_columns:
                    connection.execute(text(statement))
        if "app_settings" in table_names:
            settings_columns = {column["name"] for column in inspector.get_columns("app_settings")}
            column_migrations = (
                (
                    "default_daily_capacity_minutes",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN default_daily_capacity_minutes INTEGER NOT NULL DEFAULT 45",
                ),
                (
                    "default_priority",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN default_priority INTEGER NOT NULL DEFAULT 2",
                ),
                (
                    "default_learning_mode",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN default_learning_mode VARCHAR(32) NOT NULL DEFAULT 'application'",
                ),
                (
                    "review_intervals_csv",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN review_intervals_csv VARCHAR(64) NOT NULL DEFAULT '1,3,7,14'",
                ),
                (
                    "low_confidence_followup_days",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN low_confidence_followup_days INTEGER NOT NULL DEFAULT 2",
                ),
                (
                    "allow_weekend_scheduling",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN allow_weekend_scheduling INTEGER NOT NULL DEFAULT 1",
                ),
                (
                    "render_math_enabled",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN render_math_enabled INTEGER NOT NULL DEFAULT 1",
                ),
                (
                    "study_material_theme",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN study_material_theme VARCHAR(32) NOT NULL DEFAULT 'reader'",
                ),
                (
                    "dashboard_density",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN dashboard_density VARCHAR(32) NOT NULL DEFAULT 'balanced'",
                ),
                (
                    "motion_level",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN motion_level VARCHAR(32) NOT NULL DEFAULT 'full'",
                ),
                (
                    "queue_preview_count_study",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN queue_preview_count_study INTEGER NOT NULL DEFAULT 8",
                ),
                (
                    "queue_preview_count_review",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN queue_preview_count_review INTEGER NOT NULL DEFAULT 6",
                ),
                (
                    "dashboard_hero_title_text",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN dashboard_hero_title_text VARCHAR(160) NOT NULL DEFAULT '今日學習總覽'",
                ),
                (
                    "dashboard_hero_title_size_px",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN dashboard_hero_title_size_px INTEGER NOT NULL DEFAULT 72",
                ),
                (
                    "dashboard_major_event_content",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN dashboard_major_event_content VARCHAR(200)",
                ),
                (
                    "dashboard_major_event_date",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN dashboard_major_event_date DATE",
                ),
                (
                    "updated_at",
                    "ALTER TABLE app_settings "
                    "ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
                ),
            )
            for column_name, statement in column_migrations:
                if column_name not in settings_columns:
                    connection.execute(text(statement))
