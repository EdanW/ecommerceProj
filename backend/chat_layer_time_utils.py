"""
Time-related utility functions for the chat layer.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from .chat_layer_constants import TIMEZONE


class TimeOfDay(str, Enum):
    """Coarse time-of-day buckets used by the chat layer."""

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


def get_time_of_day_from_time() -> TimeOfDay:
    """Return a coarse time-of-day bucket in the configured timezone."""
    hour = datetime.now(TIMEZONE).hour
    if 5 <= hour < 12:
        return TimeOfDay.MORNING
    if 12 <= hour < 17:
        return TimeOfDay.AFTERNOON
    if 17 <= hour < 21:
        return TimeOfDay.EVENING
    return TimeOfDay.NIGHT


def time_of_day_from_meal_type(meal_type: Optional[str]) -> Optional[TimeOfDay]:
    """Map a meal type to a compatible time-of-day bucket (or None if unknown)."""
    if not meal_type:
        return None

    mt = meal_type.lower().strip()
    if mt == "breakfast":
        return TimeOfDay.MORNING
    if mt == "lunch":
        return TimeOfDay.AFTERNOON
    if mt == "dinner":
        return TimeOfDay.EVENING
    if mt == "dessert":
        return TimeOfDay.EVENING
    return None
