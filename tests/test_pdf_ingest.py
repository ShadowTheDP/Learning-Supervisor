from types import SimpleNamespace
import unittest

from app.services.markdown_ingest import UnitHint, split_markdown_into_units
from app.services.pdf_ingest import extract_docling_unit_hints


class FakeDocument:
    def __init__(self, items):
        self._items = items

    def iterate_items(self):
        return self._items


class PdfIngestTests(unittest.TestCase):
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
                text="Example 1",
                label=SimpleNamespace(value="DocItemLabel.SECTION_HEADER"),
                prov=[SimpleNamespace(page_no=4)],
            ),
            SimpleNamespace(
                text="Plain body text",
                label=SimpleNamespace(value="DocItemLabel.PARAGRAPH"),
                prov=[SimpleNamespace(page_no=6)],
            ),
        ]

        hints = extract_docling_unit_hints(FakeDocument(items))

        self.assertEqual(len(hints), 3)
        self.assertEqual(hints[0].title, "Chapter 1 Linear Algebra")
        self.assertEqual(hints[0].page_start, 1)
        self.assertEqual(hints[0].page_end, 2)
        self.assertEqual(hints[1].title, "1.1 Vectors")
        self.assertEqual(hints[1].page_start, 2)
        self.assertEqual(hints[1].page_end, 2)
        self.assertEqual(hints[2].content_type, "example")
        self.assertEqual(hints[2].page_start, 4)
        self.assertEqual(hints[2].page_end, 6)

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


if __name__ == "__main__":
    unittest.main()
