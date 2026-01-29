"""
Time-related utility functions for the chat layer.
"""

from datetime import datetime
from typing import Optional

from .chat_layer_constants import TIMEZONE


def get_time_of_day_from_time() -> str:
    """Return a coarse time-of-day bucket in the configured timezone."""
    hour = datetime.now(TIMEZONE).hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def time_of_day_from_meal_type(meal_type: Optional[str]) -> Optional[str]:
    """Map a meal type to a compatible time-of-day bucket (or None if unknown)."""
    if not meal_type:
        return None

    mt = meal_type.lower().strip()
    if mt == "breakfast":
        return "morning"
    if mt == "lunch":
        return "afternoon"
    if mt == "dinner":
        return "evening"
    if mt == "dessert":
        return "evening"
    return None
