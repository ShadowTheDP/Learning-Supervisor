from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.models import LearningUnit, Resource
from app.services.pdf_page_viewer import (
    get_available_unit_pdf_page_numbers,
    get_or_create_unit_pdf_preview_page,
    get_or_create_unit_pdf_subset,
    get_original_pdf_path,
    get_unit_pdf_page_numbers,
)
import pypdfium2 as pdfium


class PdfPageViewerTests(unittest.TestCase):
    def test_get_original_pdf_path_prefers_cached_original(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            markdown_path = workspace / "source.md"
            markdown_path.write_text("# Example", encoding="utf-8")
            cached_pdf = workspace / "original.pdf"
            cached_pdf.write_bytes(b"%PDF-1.4\ncached\n")

            resource = Resource(
                stored_markdown_path=str(markdown_path),
                source_path_or_url=str(workspace / "elsewhere.pdf"),
            )

            self.assertEqual(get_original_pdf_path(resource), cached_pdf.resolve())

    def test_get_original_pdf_path_falls_back_to_source_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir) / "resource"
            workspace.mkdir(parents=True, exist_ok=True)
            markdown_path = workspace / "source.md"
            markdown_path.write_text("# Example", encoding="utf-8")
            source_pdf = Path(tmp_dir) / "source.pdf"
            source_pdf.write_bytes(b"%PDF-1.4\nsource\n")

            resource = Resource(
                stored_markdown_path=str(markdown_path),
                source_path_or_url=str(source_pdf),
            )

            self.assertEqual(get_original_pdf_path(resource), source_pdf.resolve())

    def test_get_unit_pdf_page_numbers_handles_ranges(self):
        self.assertEqual(get_unit_pdf_page_numbers(LearningUnit(page_start=7, page_end=7)), [7])
        self.assertEqual(get_unit_pdf_page_numbers(LearningUnit(page_start=8, page_end=11)), [8, 9, 10, 11])
        self.assertEqual(get_unit_pdf_page_numbers(LearningUnit(page_start=None, page_end=None)), [])

    def test_get_available_unit_pdf_page_numbers_clips_to_document_length(self):
        resource = Resource(stored_markdown_path="C:/tmp/source.md")
        unit = LearningUnit(resource=resource, page_start=3, page_end=6)

        with patch("app.services.pdf_page_viewer.get_resource_pdf_page_count", return_value=4):
            self.assertEqual(get_available_unit_pdf_page_numbers(unit), [3, 4])

    def test_get_or_create_unit_pdf_subset_only_contains_unit_pages(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            markdown_path = workspace / "source.md"
            markdown_path.write_text("# Example", encoding="utf-8")
            source_pdf = workspace / "original.pdf"

            document = pdfium.PdfDocument.new()
            try:
                document.new_page(200, 300).close()
                document.new_page(200, 300).close()
                document.new_page(200, 300).close()
                document.save(str(source_pdf))
            finally:
                document.close()

            resource = Resource(
                stored_markdown_path=str(markdown_path),
                source_path_or_url=str(source_pdf),
            )
            unit = LearningUnit(id="unit-1", resource=resource, page_start=2, page_end=3)

            subset_path = get_or_create_unit_pdf_subset(unit)

            self.assertTrue(subset_path.exists())
            with pdfium.PdfDocument(str(subset_path)) as subset_document:
                self.assertEqual(len(subset_document), 2)

    def test_get_or_create_unit_pdf_preview_page_contains_single_page(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            markdown_path = workspace / "source.md"
            markdown_path.write_text("# Example", encoding="utf-8")
            source_pdf = workspace / "original.pdf"

            document = pdfium.PdfDocument.new()
            try:
                document.new_page(200, 300).close()
                document.new_page(200, 300).close()
                document.new_page(200, 300).close()
                document.save(str(source_pdf))
            finally:
                document.close()

            resource = Resource(
                stored_markdown_path=str(markdown_path),
                source_path_or_url=str(source_pdf),
            )
            unit = LearningUnit(id="unit-1", resource=resource, page_start=2, page_end=3)

            preview_path = get_or_create_unit_pdf_preview_page(unit, 2)

            self.assertTrue(preview_path.exists())
            with pdfium.PdfDocument(str(preview_path)) as preview_document:
                self.assertEqual(len(preview_document), 1)


if __name__ == "__main__":
    unittest.main()
