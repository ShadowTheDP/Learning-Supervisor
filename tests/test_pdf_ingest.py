import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import DOCLING_PDF_OCR_ENABLED
from app.services.markdown_ingest import UnitHint, split_markdown_into_units
from app.services.pdf_ingest import (
    apply_low_memory_docling_profile,
    convert_pdf_with_docling_fallback,
    ensure_complete_pdf_conversion,
    extract_docling_unit_hints,
    should_use_low_memory_docling,
)


class FakeDocument:
    def __init__(self, items):
        self._items = items

    def iterate_items(self):
        return self._items


class PdfIngestTests(unittest.TestCase):
    def test_local_pdf_ocr_defaults_to_disabled(self):
        self.assertFalse(DOCLING_PDF_OCR_ENABLED)

    def test_extract_docling_unit_hints_builds_page_ranges(self):
        items = [
            SimpleNamespace(
                text="Chapter 1 Linear Algebra",
                label=SimpleNamespace(value="DocItemLabel.TITLE"),
                prov=[SimpleNamespace(page_no=1)],
            ),
            SimpleNamespace(
                text="This paragraph belongs to the first chapter.",
                label=SimpleNamespace(value="DocItemLabel.PARAGRAPH"),
                prov=[SimpleNamespace(page_no=2)],
            ),
            SimpleNamespace(
                text="1.1 Vectors",
                label=SimpleNamespace(value="DocItemLabel.SECTION_HEADER"),
                prov=[SimpleNamespace(page_no=2)],
            ),
            SimpleNamespace(
                text="Definition 1.1.1. A vector space is closed under addition.",
                label=SimpleNamespace(value="DocItemLabel.PARAGRAPH"),
                prov=[SimpleNamespace(page_no=3)],
            ),
            SimpleNamespace(
                text="Example 1",
                label=SimpleNamespace(value="DocItemLabel.SECTION_HEADER"),
                prov=[SimpleNamespace(page_no=4)],
            ),
            {
                "text": "1.2 Inner Products",
                "label": {"value": "DocItemLabel.SECTION_HEADER"},
                "prov": [{"page_no": 5}],
            },
            SimpleNamespace(
                text="Plain body text",
                label=SimpleNamespace(value="DocItemLabel.PARAGRAPH"),
                prov=[SimpleNamespace(page_no=6)],
            ),
        ]

        hints = extract_docling_unit_hints(FakeDocument(items))

        self.assertEqual(len(hints), 4)
        self.assertEqual(hints[0].title, "Chapter 1 Linear Algebra")
        self.assertEqual(hints[0].page_start, 1)
        self.assertEqual(hints[0].page_end, 6)
        self.assertEqual(hints[1].title, "1.1 Vectors")
        self.assertEqual(hints[1].page_start, 2)
        self.assertEqual(hints[1].page_end, 4)
        self.assertEqual(hints[2].content_type, "example")
        self.assertEqual(hints[2].page_start, 4)
        self.assertEqual(hints[2].page_end, 4)
        self.assertEqual(hints[3].title, "1.2 Inner Products")
        self.assertEqual(hints[3].page_start, 5)
        self.assertEqual(hints[3].page_end, 6)

    def test_markdown_units_keep_pdf_page_hints(self):
        markdown_text = """# Chapter 1 Linear Algebra

Section body.

## Example 1

Worked example.
"""

        hints = [
            UnitHint(title="Chapter 1 Linear Algebra", heading_level=1, page_start=1, page_end=3, content_type="section"),
            UnitHint(title="Example 1", heading_level=2, page_start=4, page_end=5, content_type="example"),
        ]

        units = split_markdown_into_units(markdown_text, unit_hints=hints)

        self.assertEqual(units[0].page_start, 1)
        self.assertEqual(units[0].page_end, 3)
        self.assertEqual(units[1].page_start, 4)
        self.assertEqual(units[1].page_end, 5)
        self.assertEqual(units[1].content_type, "example")

    def test_plain_section_sentence_is_not_treated_as_heading(self):
        markdown_text = """# Chapter 1 Linear Algebra

Section body.
Continuation line.
"""

        units = split_markdown_into_units(markdown_text)

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].title, "Chapter 1 Linear Algebra")
        self.assertIn("Section body.", units[0].content_markdown)
        self.assertIn("Continuation line.", units[0].content_markdown)

    def test_markdown_units_use_repeated_chapter_hints_as_primary_boundaries(self):
        markdown_text = """## Chapter 1

## Divisibility

Definition 1.1.1. A number n is divisible by m.

## 1.1 Multiplication Tables

Worked examples.

## Chapter 2

## Modular Arithmetic

Problem 2.1.1. Compute the remainder.
"""

        hints = [
            UnitHint(title="Chapter 1", heading_level=1, page_start=10, page_end=20, content_type="section"),
            UnitHint(title="Divisibility", heading_level=2, page_start=10, page_end=10, content_type="section"),
            UnitHint(
                title="Definition 1.1.1. A number n is divisible by m.",
                heading_level=3,
                page_start=11,
                page_end=11,
                content_type="definition",
            ),
            UnitHint(title="Chapter 2", heading_level=1, page_start=21, page_end=30, content_type="section"),
            UnitHint(title="Modular Arithmetic", heading_level=2, page_start=21, page_end=21, content_type="section"),
        ]

        units = split_markdown_into_units(markdown_text, unit_hints=hints)

        self.assertEqual([unit.title for unit in units], ["Chapter 1", "Chapter 2"])
        self.assertIn("## Divisibility", units[0].content_markdown)
        self.assertIn("Definition 1.1.1.", units[0].content_markdown)
        self.assertEqual(units[0].page_start, 10)
        self.assertEqual(units[0].page_end, 20)
        self.assertEqual(units[1].page_start, 21)
        self.assertEqual(units[1].page_end, 30)

    def test_markdown_units_expand_chapter_range_from_descendant_hints(self):
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

        hints = [
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

        units = split_markdown_into_units(markdown_text, unit_hints=hints)

        self.assertEqual([unit.title for unit in units], ["Chapter 9", "Chapter 10"])
        self.assertEqual(units[0].page_start, 237)
        self.assertEqual(units[0].page_end, 246)
        self.assertEqual(units[1].page_start, 247)
        self.assertEqual(units[1].page_end, 251)

    def test_partial_docling_conversion_is_rejected(self):
        conversion_result = SimpleNamespace(
            status="partial_success",
            input=SimpleNamespace(page_count=317),
            pages=[object()] * 25,
            errors=[
                SimpleNamespace(error_message="Page 26: std::bad_alloc"),
                SimpleNamespace(error_message="Page 27: std::bad_alloc"),
            ],
        )

        with self.assertRaisesRegex(ValueError, "部分 PDF 解析"):
            ensure_complete_pdf_conversion(conversion_result)


    def test_apply_low_memory_docling_profile_reduces_queue_and_batches(self):
        pipeline_options = SimpleNamespace(
            queue_max_size=100,
            ocr_batch_size=4,
            layout_batch_size=4,
            table_batch_size=4,
            batch_polling_interval_seconds=0.5,
        )

        profiled = apply_low_memory_docling_profile(pipeline_options)

        self.assertIs(profiled, pipeline_options)
        self.assertEqual(profiled.queue_max_size, 2)
        self.assertEqual(profiled.ocr_batch_size, 1)
        self.assertEqual(profiled.layout_batch_size, 1)
        self.assertEqual(profiled.table_batch_size, 1)
        self.assertEqual(profiled.batch_polling_interval_seconds, 0.05)

    def test_should_use_low_memory_docling_for_large_pdf(self):
        self.assertTrue(should_use_low_memory_docling(page_count=120))
        self.assertTrue(
            should_use_low_memory_docling(
                page_count=10,
                file_size_bytes=12 * 1024 * 1024,
            )
        )
        self.assertFalse(should_use_low_memory_docling(page_count=24, file_size_bytes=1024))

    def test_convert_pdf_with_docling_fallback_retries_with_low_memory(self):
        partial_result = SimpleNamespace(status="partial_success")
        success_result = SimpleNamespace(status="success")

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_file:
            pdf_path = Path(tmp_file.name)
            with (
                patch("app.services.pdf_ingest.get_pdf_page_count_for_docling", return_value=24),
                patch(
                    "app.services.pdf_ingest.convert_pdf_with_docling_local",
                    side_effect=[partial_result, success_result],
                ) as convert_mock,
            ):
                result = convert_pdf_with_docling_fallback(pdf_path)

        self.assertIs(result, success_result)
        self.assertEqual(convert_mock.call_count, 2)
        self.assertFalse(convert_mock.call_args_list[0].kwargs["low_memory"])
        self.assertTrue(convert_mock.call_args_list[1].kwargs["low_memory"])

    def test_convert_pdf_with_docling_fallback_prefers_low_memory_for_large_pdf(self):
        success_result = SimpleNamespace(status="success")

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_file:
            pdf_path = Path(tmp_file.name)
            with (
                patch("app.services.pdf_ingest.get_pdf_page_count_for_docling", return_value=317),
                patch(
                    "app.services.pdf_ingest.convert_pdf_with_docling_local",
                    return_value=success_result,
                ) as convert_mock,
            ):
                result = convert_pdf_with_docling_fallback(pdf_path)

        self.assertIs(result, success_result)
        self.assertEqual(convert_mock.call_count, 1)
        self.assertTrue(convert_mock.call_args.kwargs["low_memory"])


if __name__ == "__main__":
    unittest.main()
