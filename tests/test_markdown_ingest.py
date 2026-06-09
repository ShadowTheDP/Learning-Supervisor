import unittest

from app.services.markdown_ingest import split_markdown_into_units


class MarkdownIngestTests(unittest.TestCase):
    def test_splits_by_headings_and_estimates_minutes(self):
        markdown_text = """# Week 1

Intro paragraph.

## Bayes

Bayes theorem paragraph with some extra context.

## Expectations

Expected value paragraph.
"""

        units = split_markdown_into_units(markdown_text)

        self.assertEqual(len(units), 3)
        self.assertEqual(units[0].title, "Week 1")
        self.assertEqual(units[1].title, "Bayes")
        self.assertGreaterEqual(units[1].estimated_minutes, 12)

    def test_skips_short_front_matter_title_page_before_numbered_sections(self):
        markdown_text = """## Lemmas In Olympiad Geometry

Navneel Singhal

## 1 Introduction

Intro paragraph.
"""

        units = split_markdown_into_units(markdown_text)

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].title, "1 Introduction")

    def test_skips_terminal_references_section(self):
        markdown_text = """## 1 Introduction

Intro paragraph.

## References

[1] Some source.
[2] Another source.
"""

        units = split_markdown_into_units(markdown_text)

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].title, "1 Introduction")

    def test_keeps_long_chapter_as_single_unit(self):
        paragraph = " ".join(["geometry"] * 900)
        markdown_text = f"""## 5 Radical Axis

{paragraph}
"""

        units = split_markdown_into_units(markdown_text)

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].title, "5 Radical Axis")


if __name__ == "__main__":
    unittest.main()
