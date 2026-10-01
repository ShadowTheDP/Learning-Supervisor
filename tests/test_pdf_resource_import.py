from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.services.markdown_ingest import UnitHint
from app.services.study_service import create_resource_plan, create_resource_plan_from_pdf_structure


class PdfResourceImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.resources_dir = self.temp_path / "resources"

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        self.session = self.SessionLocal()

    def tearDown(self) -> None:
        self.session.close()
        self.temp_dir.cleanup()

    def test_create_resource_plan_from_pdf_keeps_page_hints_and_artifacts(self) -> None:
        pdf_path = self.temp_path / "lecture 1.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n% fake smoke pdf\n")

        markdown_text = """# Chapter 1

Intro paragraph.

## Example 1

Worked example.
"""
        unit_hints = [
            UnitHint(title="Chapter 1", heading_level=1, page_start=1, page_end=2, content_type="section"),
            UnitHint(title="Example 1", heading_level=2, page_start=3, page_end=4, content_type="example"),
        ]

        captured_progress_callback = None

        def fake_load_pdf_source(source_path: str, *, artifact_dir: Path | None = None, progress_callback=None):
            nonlocal captured_progress_callback
            self.assertEqual(source_path, str(pdf_path))
            self.assertIsNotNone(artifact_dir)
            captured_progress_callback = progress_callback
            assert artifact_dir is not None
            artifact_dir.mkdir(parents=True, exist_ok=True)
            (artifact_dir / "original.pdf").write_bytes(pdf_path.read_bytes())
            docling_dir = artifact_dir / "docling"
            docling_dir.mkdir(parents=True, exist_ok=True)
            (docling_dir / "source.md").write_text(markdown_text, encoding="utf-8")
            return markdown_text, str(pdf_path), unit_hints

        with (
            patch("app.services.study_service.RESOURCES_DIR", self.resources_dir),
            patch("app.services.study_service.load_pdf_source", side_effect=fake_load_pdf_source),
        ):
            resource = create_resource_plan(
                self.session,
                title="Linear Algebra Notes",
                description="Import from local PDF.",
                source_path=f'"{pdf_path}"',
                deadline=date.today() + timedelta(days=7),
                priority=2,
                learning_mode="application",
                review_intervals_csv="1,3,7,14",
                allow_weekend_scheduling=True,
            )

        self.assertEqual(resource.source_type, "pdf_file")
        self.assertEqual(resource.source_path_or_url, str(pdf_path))
        self.assertEqual(len(resource.learning_units), 2)
        self.assertEqual(resource.learning_units[0].title, "Chapter 1")
        self.assertEqual(resource.learning_units[0].page_start, 1)
        self.assertEqual(resource.learning_units[0].page_end, 2)
        self.assertEqual(resource.learning_units[1].content_type, "example")
        self.assertEqual(resource.learning_units[1].page_start, 3)
        self.assertEqual(resource.learning_units[1].page_end, 4)
        self.assertIsNone(captured_progress_callback)

        all_tasks = [task for unit in resource.learning_units for task in unit.daily_tasks]
        self.assertEqual(len(all_tasks), 2)

        resource_dir = self.resources_dir / resource.slug
        self.assertTrue((resource_dir / "source.md").exists())
        self.assertTrue((resource_dir / "original.pdf").exists())
        self.assertTrue((resource_dir / "docling" / "source.md").exists())

    def test_failed_pdf_ingest_cleans_up_partial_resource_directory(self) -> None:
        pdf_path = self.temp_path / "broken.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n% broken\n")
        created_artifact_dir: Path | None = None

        def failing_load_pdf_source(source_path: str, *, artifact_dir: Path | None = None, progress_callback=None):
            nonlocal created_artifact_dir
            self.assertEqual(source_path, str(pdf_path))
            self.assertIsNotNone(artifact_dir)
            assert artifact_dir is not None
            created_artifact_dir = artifact_dir
            artifact_dir.mkdir(parents=True, exist_ok=True)
            (artifact_dir / "partial.txt").write_text("partial", encoding="utf-8")
            raise ValueError("conversion failed")

        with (
            patch("app.services.study_service.RESOURCES_DIR", self.resources_dir),
            patch("app.services.study_service.load_pdf_source", side_effect=failing_load_pdf_source),
        ):
            with self.assertRaisesRegex(ValueError, "conversion failed"):
                create_resource_plan(
                    self.session,
                    title="Broken Import",
                    description="Should clean up after failure.",
                    source_path=f'"{pdf_path}"',
                    deadline=date.today() + timedelta(days=7),
                    priority=2,
                    learning_mode="application",
                    review_intervals_csv="1,3,7,14",
                    allow_weekend_scheduling=True,
                )

        self.assertIsNotNone(created_artifact_dir)
        assert created_artifact_dir is not None
        self.assertFalse(created_artifact_dir.exists())
        if self.resources_dir.exists():
            self.assertEqual(list(self.resources_dir.iterdir()), [])

    def test_create_resource_plan_from_existing_pdf_structure_generates_tasks(self) -> None:
        pdf_path = self.temp_path / "lemma-notes.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n% imported from existing structure\n")

        markdown_text = """## 1 Introduction

Intro paragraph.

## 2 Main Lemmas

Core geometry results with more content.

## References

[1] Ignored reference.
"""
        unit_hints = [
            UnitHint(title="1 Introduction", heading_level=2, page_start=1, page_end=1, content_type="section"),
            UnitHint(title="2 Main Lemmas", heading_level=2, page_start=2, page_end=3, content_type="section"),
            UnitHint(title="References", heading_level=2, page_start=4, page_end=4, content_type="section"),
        ]

        with patch("app.services.study_service.RESOURCES_DIR", self.resources_dir):
            resource = create_resource_plan_from_pdf_structure(
                self.session,
                title="Lemma Notes",
                description="Imported from cached Docling structure.",
                source_path=str(pdf_path),
                deadline=date.today() + timedelta(days=7),
                priority=2,
                learning_mode="application",
                review_intervals_csv="1,3,7,14",
                allow_weekend_scheduling=True,
                markdown_text=markdown_text,
                unit_hints=unit_hints,
            )

        self.assertEqual(resource.source_type, "pdf_file")
        self.assertEqual(resource.source_path_or_url, str(pdf_path))
        self.assertEqual(len(resource.learning_units), 2)
        self.assertEqual(resource.learning_units[0].title, "1 Introduction")
        self.assertEqual(resource.learning_units[1].title, "2 Main Lemmas")
        self.assertTrue(all(unit.daily_tasks for unit in resource.learning_units))

        resource_dir = self.resources_dir / resource.slug
        self.assertTrue((resource_dir / "source.md").exists())
        self.assertTrue((resource_dir / "original.pdf").exists())
        self.assertTrue((resource_dir / "docling" / "outline.json").exists())

    def test_create_resource_plan_from_existing_pdf_structure_expands_chapter_range(self) -> None:
        pdf_path = self.temp_path / "mont.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n% chapter range smoke\n")

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
        unit_hints = [
            UnitHint(title="Chapter 9", heading_level=1, page_start=237, page_end=237, content_type="section"),
            UnitHint(title="Constructions", heading_level=2, page_start=237, page_end=238, content_type="section"),
            UnitHint(
                title="9.1 Dirichlet's Theorem",
                heading_level=2,
                page_start=238,
                page_end=239,
                content_type="section",
            ),
            UnitHint(
                title="9.2 Chinese Remainder Theorem",
                heading_level=2,
                page_start=239,
                page_end=245,
                content_type="section",
            ),
            UnitHint(title="Chapter 10", heading_level=1, page_start=247, page_end=247, content_type="section"),
            UnitHint(title="Primitive Roots", heading_level=2, page_start=247, page_end=251, content_type="section"),
        ]

        with patch("app.services.study_service.RESOURCES_DIR", self.resources_dir):
            resource = create_resource_plan_from_pdf_structure(
                self.session,
                title="MONT Chapter Range",
                description="Imported from cached Docling structure.",
                source_path=str(pdf_path),
                deadline=date.today() + timedelta(days=7),
                priority=2,
                learning_mode="application",
                review_intervals_csv="1,3,7,14",
                allow_weekend_scheduling=True,
                markdown_text=markdown_text,
                unit_hints=unit_hints,
            )

        self.assertEqual(len(resource.learning_units), 2)
        self.assertEqual(resource.learning_units[0].title, "Chapter 9")
        self.assertEqual(resource.learning_units[0].page_start, 237)
        self.assertEqual(resource.learning_units[0].page_end, 246)
        self.assertEqual(resource.learning_units[1].title, "Chapter 10")
        self.assertEqual(resource.learning_units[1].page_start, 247)
        self.assertEqual(resource.learning_units[1].page_end, 251)

    def test_create_resource_plan_passes_progress_callback_to_pdf_ingest(self) -> None:
        pdf_path = self.temp_path / "progress.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n% progress smoke pdf\n")

        markdown_text = "# Chapter 1\n\nBody"
        unit_hints = [
            UnitHint(title="Chapter 1", heading_level=1, page_start=1, page_end=1, content_type="section"),
        ]
        captured_progress_callback = None

        def fake_load_pdf_source(source_path: str, *, artifact_dir: Path | None = None, progress_callback=None):
            nonlocal captured_progress_callback
            captured_progress_callback = progress_callback
            assert artifact_dir is not None
            artifact_dir.mkdir(parents=True, exist_ok=True)
            (artifact_dir / "original.pdf").write_bytes(pdf_path.read_bytes())
            docling_dir = artifact_dir / "docling"
            docling_dir.mkdir(parents=True, exist_ok=True)
            (docling_dir / "source.md").write_text(markdown_text, encoding="utf-8")
            return markdown_text, str(pdf_path), unit_hints

        def fake_progress(done: int, total: int, phase: str) -> None:
            self.assertIsInstance(done, int)
            self.assertIsInstance(total, int)
            self.assertIsInstance(phase, str)

        with (
            patch("app.services.study_service.RESOURCES_DIR", self.resources_dir),
            patch("app.services.study_service.load_pdf_source", side_effect=fake_load_pdf_source),
        ):
            create_resource_plan(
                self.session,
                title="Progress Notes",
                description="Import with progress callback.",
                source_path=str(pdf_path),
                deadline=date.today() + timedelta(days=7),
                priority=2,
                learning_mode="application",
                review_intervals_csv="1,3,7,14",
                allow_weekend_scheduling=True,
                progress_callback=fake_progress,
            )

        self.assertIs(captured_progress_callback, fake_progress)


if __name__ == "__main__":
    unittest.main()
