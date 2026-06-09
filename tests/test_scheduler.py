from datetime import date
import unittest

from app.services.scheduler import SchedulableUnit, build_study_schedule


class SchedulerTests(unittest.TestCase):
    def test_spreads_units_across_available_days(self):
        units = [
            SchedulableUnit(order_index=1, estimated_minutes=30),
            SchedulableUnit(order_index=2, estimated_minutes=25),
            SchedulableUnit(order_index=3, estimated_minutes=15),
        ]

        schedule = build_study_schedule(
            units,
            start_date=date(2026, 5, 28),
            deadline=date(2026, 5, 30),
        )

        self.assertEqual(schedule[0].due_date, date(2026, 5, 28))
        self.assertEqual(schedule[1].due_date, date(2026, 5, 29))
        self.assertEqual(schedule[2].due_date, date(2026, 5, 30))

    def test_groups_multiple_units_when_deadline_window_is_tight(self):
        units = [
            SchedulableUnit(order_index=1, estimated_minutes=30),
            SchedulableUnit(order_index=2, estimated_minutes=25),
            SchedulableUnit(order_index=3, estimated_minutes=15),
            SchedulableUnit(order_index=4, estimated_minutes=20),
            SchedulableUnit(order_index=5, estimated_minutes=10),
        ]

        schedule = build_study_schedule(
            units,
            start_date=date(2026, 5, 28),
            deadline=date(2026, 5, 30),
        )

        self.assertEqual([item.due_date for item in schedule], [
            date(2026, 5, 28),
            date(2026, 5, 28),
            date(2026, 5, 29),
            date(2026, 5, 29),
            date(2026, 5, 30),
        ])

    def test_rejects_invalid_deadline(self):
        with self.assertRaises(ValueError):
            build_study_schedule(
                [SchedulableUnit(order_index=1, estimated_minutes=20)],
                start_date=date(2026, 5, 29),
                deadline=date(2026, 5, 28),
            )

    def test_skips_weekends_when_weekend_scheduling_is_disabled(self):
        units = [
            SchedulableUnit(order_index=1, estimated_minutes=20),
            SchedulableUnit(order_index=2, estimated_minutes=20),
        ]

        schedule = build_study_schedule(
            units,
            start_date=date(2026, 5, 29),
            deadline=date(2026, 6, 2),
            allow_weekend_scheduling=False,
        )

        self.assertEqual(schedule[0].due_date, date(2026, 5, 29))
        self.assertEqual(schedule[1].due_date, date(2026, 6, 1))

    def test_rejects_ranges_without_usable_days_when_weekends_are_disabled(self):
        with self.assertRaises(ValueError):
            build_study_schedule(
                [SchedulableUnit(order_index=1, estimated_minutes=20)],
                start_date=date(2026, 5, 30),
                deadline=date(2026, 5, 31),
                allow_weekend_scheduling=False,
            )


if __name__ == "__main__":
    unittest.main()
