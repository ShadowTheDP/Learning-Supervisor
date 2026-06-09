import unittest

from app.services.settings_service import normalize_review_intervals_csv


class SettingsServiceTests(unittest.TestCase):
    def test_normalizes_review_intervals_to_sorted_unique_values(self):
        normalized = normalize_review_intervals_csv("7, 1, 3, 3, 14")

        self.assertEqual(normalized, "1,3,7,14")

    def test_rejects_non_numeric_review_intervals(self):
        with self.assertRaises(ValueError):
            normalize_review_intervals_csv("1,three,7")

    def test_rejects_empty_review_interval_input(self):
        with self.assertRaises(ValueError):
            normalize_review_intervals_csv(" , ")


if __name__ == "__main__":
    unittest.main()
