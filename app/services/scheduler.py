from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(slots=True)
class SchedulableUnit:
    order_index: int
    estimated_minutes: int


@dataclass(slots=True)
class ScheduledUnit:
    order_index: int
    due_date: date
    scheduled_minutes: int


def build_study_schedule(
    units: list[SchedulableUnit],
    start_date: date,
    deadline: date,
    allow_weekend_scheduling: bool = True,
) -> list[ScheduledUnit]:
    if deadline < start_date:
        raise ValueError("Deadline cannot be earlier than the start date.")
    if not units:
        return []

    total_days = (deadline - start_date).days + 1
    schedule_days = [
        start_date + timedelta(days=offset)
        for offset in range(total_days)
        if allow_weekend_scheduling or (start_date + timedelta(days=offset)).weekday() < 5
    ]
    if not schedule_days:
        raise ValueError("There are no usable study days in the selected date range.")

    scheduled: list[ScheduledUnit] = []
    current_day_index = 0
    remaining_units = len(units)
    units_remaining_today = math.ceil(remaining_units / len(schedule_days))

    for unit in units:
        scheduled.append(
            ScheduledUnit(
                order_index=unit.order_index,
                due_date=schedule_days[current_day_index],
                scheduled_minutes=max(1, unit.estimated_minutes),
            )
        )

        remaining_units -= 1
        units_remaining_today -= 1

        if remaining_units <= 0:
            continue

        remaining_days = len(schedule_days) - current_day_index
        if units_remaining_today <= 0 and remaining_days > 1:
            current_day_index += 1
            remaining_days = len(schedule_days) - current_day_index
            units_remaining_today = math.ceil(remaining_units / remaining_days)

    return scheduled
