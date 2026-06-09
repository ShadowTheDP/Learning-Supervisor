from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import RESOURCES_DIR  # noqa: E402
from app.db import SessionLocal, initialize_database  # noqa: E402
from app.models import DailyTask, Resource  # noqa: E402
from app.services.settings_service import get_app_settings  # noqa: E402
from app.services.pdf_ingest import deserialize_unit_hints  # noqa: E402
from app.services.study_service import (  # noqa: E402
    create_resource_plan,
    create_resource_plan_from_pdf_structure,
)


@dataclass(slots=True)
class DayPlan:
    due_date: date
    tasks: list[DailyTask]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a local PDF into Learning-Supervisor and auto-generate study tasks.",
    )
    parser.add_argument("source", help="Path to the local PDF file.")
    parser.add_argument(
        "--docling-markdown",
        help="Optional path to an existing Docling Markdown export. Use together with --docling-outline.",
    )
    parser.add_argument(
        "--docling-outline",
        help="Optional path to an existing Docling outline JSON file. Use together with --docling-markdown.",
    )
    parser.add_argument(
        "--title",
        help="Resource title. Defaults to the PDF filename without extension.",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Optional resource description.",
    )
    parser.add_argument(
        "--deadline",
        help="Target deadline in YYYY-MM-DD format. Overrides --days-until-deadline.",
    )
    parser.add_argument(
        "--days-until-deadline",
        type=int,
        default=14,
        help="If --deadline is omitted, schedule work this many days from today. Default: 14",
    )
    parser.add_argument(
        "--priority",
        type=int,
        choices=(1, 2, 3),
        help="Priority level. Defaults to the app setting.",
    )
    parser.add_argument(
        "--learning-mode",
        choices=("application", "dictation"),
        help="Learning mode. Defaults to the app setting.",
    )
    parser.add_argument(
        "--review-intervals",
        help="Comma-separated review intervals in days. Defaults to the app setting.",
    )
    parser.add_argument(
        "--allow-weekends",
        dest="allow_weekends",
        action="store_true",
        help="Allow scheduling on weekends.",
    )
    parser.add_argument(
        "--no-weekends",
        dest="allow_weekends",
        action="store_false",
        help="Do not schedule tasks on weekends.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not replace older resources that use the same source PDF path.",
    )
    parser.set_defaults(allow_weekends=None)
    return parser.parse_args()


def resolve_deadline(args: argparse.Namespace) -> date:
    if args.deadline:
        return date.fromisoformat(args.deadline)
    if args.days_until_deadline <= 0:
        raise ValueError("`--days-until-deadline` must be greater than 0.")
    return date.today() + timedelta(days=args.days_until_deadline)


def replace_existing_resources(session, source_path: str) -> int:
    existing_resources = session.query(Resource).filter(Resource.source_path_or_url == source_path).all()
    removed_count = len(existing_resources)
    slugs = [resource.slug for resource in existing_resources]

    for resource in existing_resources:
        session.delete(resource)
    if existing_resources:
        session.commit()

    for slug in slugs:
        shutil.rmtree(RESOURCES_DIR / slug, ignore_errors=True)

    return removed_count


def load_existing_docling_structure(args: argparse.Namespace) -> tuple[str, list] | None:
    if not args.docling_markdown and not args.docling_outline:
        return None
    if not args.docling_markdown or not args.docling_outline:
        raise ValueError("`--docling-markdown` and `--docling-outline` must be provided together.")

    markdown_path = Path(args.docling_markdown).expanduser().resolve()
    outline_path = Path(args.docling_outline).expanduser().resolve()

    markdown_text = markdown_path.read_text(encoding="utf-8")
    raw_outline = json.loads(outline_path.read_text(encoding="utf-8"))
    return markdown_text, deserialize_unit_hints(raw_outline)


def build_day_plans(resource: Resource) -> list[DayPlan]:
    buckets: dict[date, list[DailyTask]] = defaultdict(list)
    for unit in resource.learning_units:
        for task in unit.daily_tasks:
            buckets[task.due_date].append(task)

    return [
        DayPlan(
            due_date=due_date,
            tasks=sorted(
                tasks,
                key=lambda task: (task.unit.order_index, task.unit.title.casefold()),
            ),
        )
        for due_date, tasks in sorted(buckets.items())
    ]


def main() -> int:
    args = parse_args()
    initialize_database()

    pdf_path = Path(args.source).expanduser().resolve()
    title = args.title.strip() if args.title else pdf_path.stem
    deadline = resolve_deadline(args)
    parsed_structure = load_existing_docling_structure(args)

    session = SessionLocal()
    try:
        app_settings = get_app_settings(session)
        priority = args.priority if args.priority is not None else app_settings.default_priority
        learning_mode = args.learning_mode or app_settings.default_learning_mode
        review_intervals_csv = args.review_intervals or app_settings.review_intervals_csv
        allow_weekends = (
            args.allow_weekends
            if args.allow_weekends is not None
            else app_settings.allow_weekend_scheduling
        )

        removed_count = 0
        if not args.keep_existing:
            removed_count = replace_existing_resources(session, str(pdf_path))

        if parsed_structure is None:
            resource = create_resource_plan(
                session,
                title=title,
                description=args.description,
                source_path=str(pdf_path),
                deadline=deadline,
                priority=priority,
                learning_mode=learning_mode,
                review_intervals_csv=review_intervals_csv,
                allow_weekend_scheduling=allow_weekends,
            )
        else:
            markdown_text, unit_hints = parsed_structure
            resource = create_resource_plan_from_pdf_structure(
                session,
                title=title,
                description=args.description,
                source_path=str(pdf_path),
                deadline=deadline,
                priority=priority,
                learning_mode=learning_mode,
                review_intervals_csv=review_intervals_csv,
                allow_weekend_scheduling=allow_weekends,
                markdown_text=markdown_text,
                unit_hints=unit_hints,
            )

        print(f"Imported resource: {resource.title}")
        print(f"Resource ID:       {resource.id}")
        print(f"Resource slug:     {resource.slug}")
        print(f"Source PDF:        {pdf_path}")
        print(f"Deadline:          {deadline.isoformat()}")
        print(f"Learning mode:     {learning_mode}")
        print(f"Review intervals:  {review_intervals_csv}")
        print(f"Weekend schedule:  {'yes' if allow_weekends else 'no'}")
        print(f"Units created:     {len(resource.learning_units)}")
        print(f"Markdown path:     {resource.stored_markdown_path}")
        if parsed_structure is not None:
            print("Planning source:   existing Docling structure")
        else:
            print("Planning source:   direct PDF import")
        if removed_count:
            print(f"Replaced older resources using the same PDF path: {removed_count}")

        print("")
        print("Study tasks by day:")
        for day_plan in build_day_plans(resource):
            total_minutes = sum(task.scheduled_minutes for task in day_plan.tasks)
            print(f"- {day_plan.due_date.isoformat()} | total {total_minutes}m")
            for task in day_plan.tasks:
                unit = task.unit
                page_label = ""
                if unit.page_start is not None:
                    page_label = (
                        f" | pages {unit.page_start}-{unit.page_end}"
                        if unit.page_end and unit.page_end > unit.page_start
                        else f" | page {unit.page_start}"
                    )
                print(
                    f"  {unit.order_index:02d}. {unit.title} "
                    f"({task.scheduled_minutes}m, {unit.word_count} words{page_label})"
                )

        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
