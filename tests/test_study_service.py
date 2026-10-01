from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, DailyTask, LearningUnit, Resource, ReviewTask, StudyPlan
from app.services.study_service import content_has_math, get_daily_task, get_dashboard_summary, review_is_available


class StudyServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        self.session = self.SessionLocal()

    def tearDown(self) -> None:
        self.session.close()

    def test_review_only_unlocks_on_or_after_due_date(self):
        review = ReviewTask(id="review-1", unit_id="unit-1", due_date=date(2026, 5, 30), interval_days=1)

        self.assertFalse(review_is_available(review, today=date(2026, 5, 29)))
        self.assertTrue(review_is_available(review, today=date(2026, 5, 30)))

    def test_detects_math_delimiters_in_markdown(self):
        markdown_text = "Inline math $a^2 + b^2 = c^2$ and block math $$x = y$$"

        self.assertTrue(content_has_math(markdown_text))
        self.assertFalse(content_has_math("Plain prose only."))

    def test_learning_mode_label_matches_mode(self):
        self.assertEqual(Resource(learning_mode="application").learning_mode_label, "應用學習")
        self.assertEqual(Resource(learning_mode="dictation").learning_mode_label, "需要默寫")

    def test_page_range_label_formats_single_page_and_range(self):
        self.assertEqual(LearningUnit(page_start=7, page_end=7).page_range_label, "第 7 頁")
        self.assertEqual(LearningUnit(page_start=8, page_end=11).page_range_label, "第 8-11 頁")

    def test_dashboard_summary_includes_scheduled_pending_tasks(self):
        today = date(2026, 6, 21)
        resource = Resource(
            id="resource-1",
            title="Lemma Notes",
            slug="lemma-notes",
            source_type="pdf_file",
            source_path_or_url="C:/books/lemma.pdf",
            stored_markdown_path="data/resources/lemma/source.md",
            priority=3,
            status="active",
            learning_mode="application",
        )
        resource.study_plan = StudyPlan(
            id="plan-1",
            resource_id=resource.id,
            start_date=today,
            deadline=today + timedelta(days=7),
            daily_capacity_minutes=0,
            review_intervals_csv="1,3,7,14",
        )
        unit = LearningUnit(
            id="unit-1",
            resource_id=resource.id,
            title="1 Introduction",
            order_index=1,
            estimated_minutes=20,
            word_count=120,
            content_markdown="Body",
        )
        unit.daily_tasks.append(
            DailyTask(
                id="task-1",
                due_date=today + timedelta(days=1),
                scheduled_minutes=20,
                status="scheduled",
            )
        )
        resource.learning_units.append(unit)
        self.session.add(resource)
        self.session.commit()

        summary = get_dashboard_summary(self.session, today=today)

        self.assertEqual(summary.pending_count, 1)
        self.assertEqual(len(summary.study_pending), 1)
        self.assertEqual(len(summary.study_due), 0)
        self.assertEqual(summary.study_pending[0].unit.title, "1 Introduction")
        self.assertEqual(summary.active_resource_count, 1)

    def test_get_daily_task_repairs_cached_pdf_page_ranges(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            resource_dir = Path(tmp_dir) / "mont"
            docling_dir = resource_dir / "docling"
            docling_dir.mkdir(parents=True, exist_ok=True)

            markdown_text = """## Chapter 9

## Constructions

Body

## 9.1 Dirichlet's Theorem

More body

## 9.2 Chinese Remainder Theorem

End

## Chapter 10

## Primitive Roots

Next chapter body
"""
            (resource_dir / "source.md").write_text(markdown_text, encoding="utf-8")
            (docling_dir / "outline.json").write_text(
                json.dumps(
                    [
                        {
                            "title": "Chapter 9",
                            "heading_level": 1,
                            "page_start": 237,
                            "page_end": 237,
                            "content_type": "section",
                        },
                        {
                            "title": "Constructions",
                            "heading_level": 2,
                            "page_start": 237,
                            "page_end": 238,
                            "content_type": "section",
                        },
                        {
                            "title": "9.1 Dirichlet's Theorem",
                            "heading_level": 2,
                            "page_start": 238,
                            "page_end": 239,
                            "content_type": "section",
                        },
                        {
                            "title": "9.2 Chinese Remainder Theorem",
                            "heading_level": 2,
                            "page_start": 239,
                            "page_end": 245,
                            "content_type": "section",
                        },
                        {
                            "title": "Chapter 10",
                            "heading_level": 1,
                            "page_start": 247,
                            "page_end": 247,
                            "content_type": "section",
                        },
                        {
                            "title": "Primitive Roots",
                            "heading_level": 2,
                            "page_start": 247,
                            "page_end": 251,
                            "content_type": "section",
                        },
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            resource = Resource(
                id="resource-mont",
                title="MONT",
                slug="mont",
                source_type="pdf_file",
                source_path_or_url=str(resource_dir / "original.pdf"),
                stored_markdown_path=str(resource_dir / "source.md"),
                priority=2,
                status="active",
                learning_mode="application",
            )
            resource.study_plan = StudyPlan(
                id="plan-mont",
                resource_id=resource.id,
                start_date=date(2026, 6, 27),
                deadline=date(2026, 7, 27),
                daily_capacity_minutes=0,
                review_intervals_csv="1,3,7,14",
            )
            first_unit = LearningUnit(
                id="unit-9",
                resource_id=resource.id,
                title="Chapter 9",
                order_index=1,
                heading_level=1,
                estimated_minutes=20,
                word_count=200,
                page_start=237,
                page_end=237,
                content_markdown="Body",
            )
            first_unit.daily_tasks.append(
                DailyTask(
                    id="task-9",
                    due_date=date(2026, 6, 28),
                    scheduled_minutes=20,
                    status="scheduled",
                )
            )
            second_unit = LearningUnit(
                id="unit-10",
                resource_id=resource.id,
                title="Chapter 10",
                order_index=2,
                heading_level=1,
                estimated_minutes=20,
                word_count=120,
                page_start=247,
                page_end=247,
                content_markdown="Next body",
            )
            resource.learning_units.extend([first_unit, second_unit])
            self.session.add(resource)
            self.session.commit()

            task = get_daily_task(self.session, "task-9")

            self.assertIsNotNone(task)
            assert task is not None
            self.assertEqual(task.unit.page_start, 237)
            self.assertEqual(task.unit.page_end, 246)
            self.assertEqual(second_unit.page_end, 251)


if __name__ == "__main__":
    unittest.main()
