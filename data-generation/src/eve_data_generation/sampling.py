"""Seeded shares, weighted allocation, and the generation clock."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

from eve_data_generation.errors import ConfigError, GenerationError

WINDOW_ERROR = "date range cannot hold the ordered timestamps"


def share_count(population: int, rate: Decimal) -> int:
    """Parents selected for a rate.

    Halves round away from zero. A rate of zero selects nobody and a rate of
    one selects everybody. A rate strictly between them, on a population of
    more than one, selects at least one parent and leaves at least one out.
    """

    if population <= 0 or rate <= 0:
        return 0
    if rate >= 1:
        return population
    chosen = int((Decimal(population) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if chosen < 1:
        chosen = 1
    if population > 1 and chosen > population - 1:
        chosen = population - 1
    return chosen


def choose_share(rng: random.Random, population: int, rate: Decimal) -> list[int]:
    """Seeded indexes of the parents selected by ``share_count``."""

    chosen = share_count(population, rate)
    if chosen == 0:
        return []
    indexes = list(range(population))
    if chosen == population:
        return indexes
    rng.shuffle(indexes)
    return indexes[:chosen]


def allocate(count: int, weights: dict[str, int]) -> dict[str, int]:
    """Largest-remainder allocation of ``count`` items across ``weights``."""

    if count < 0:
        raise ConfigError("allocation count cannot be negative")
    total = sum(weights.values())
    if total <= 0:
        raise ConfigError("mix weights must sum to a positive integer")
    raw = {
        key: (Decimal(count) * Decimal(weight)) / Decimal(total)
        for key, weight in weights.items()
    }
    floors = {
        key: int(raw[key].to_integral_value(rounding=ROUND_FLOOR))
        for key in weights
    }
    remainder = count - sum(floors.values())
    ranked = sorted(
        weights,
        key=lambda key: (-(raw[key] - Decimal(floors[key])), key),
    )
    for key in ranked[:remainder]:
        floors[key] += 1
    if sum(floors.values()) != count:
        raise ConfigError("mix allocation did not cover the population")
    return floors


def assign_labels(rng: random.Random, count: int, weights: dict[str, int]) -> list[str]:
    counts = allocate(count, weights)
    labels: list[str] = []
    for key, size in counts.items():
        labels.extend([key] * size)
    rng.shuffle(labels)
    return labels


def inclusive_dates(start: date, end: date) -> list[date]:
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def window_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min),
        datetime.combine(end, time(23, 59, 59)),
    )


def available_seconds(start: date, end: date) -> int:
    opened, closed = window_bounds(start, end)
    return int((closed - opened).total_seconds()) + 1


class Clock:
    """Issues ordered UTC timestamps inside the configured window."""

    def __init__(self, start: date, end: date) -> None:
        opened, closed = window_bounds(start, end)
        if closed < opened:
            raise GenerationError(WINDOW_ERROR)
        self._next = opened
        self._end = closed

    def take(self) -> datetime:
        if self._next > self._end:
            raise GenerationError(WINDOW_ERROR)
        current = self._next
        self._next = current + timedelta(seconds=1)
        return current
