from datetime import date
import unittest

from app.models import LearningUnit, Resource, ReviewTask
from app.services.study_service import content_has_math, review_is_available


class StudyServiceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
