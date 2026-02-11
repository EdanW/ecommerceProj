"""
Unsure / undecided handling for the chat layer.
"""

from typing import Dict, Any, List

from .chat_layer_constants import UNSURE_PHRASES


def is_unsure_response(message: str) -> bool:
    """Check if the message matches any known unsure/undecided phrase."""
    message_lower = message.lower().strip()
    return any(phrase in message_lower for phrase in UNSURE_PHRASES)


def build_unsure_craving_data(
    excluded_foods: List[str] = None,
    excluded_categories: List[str] = None,
) -> Dict[str, Any]:
    """Build empty craving_data, preserving any prior exclusions. The model decides the rest."""
    return {
        "foods": [],
        "categories": [],
        "excluded_foods": excluded_foods or [],
        "excluded_categories": excluded_categories or [],
        "meal_type": None,
        "intensity": "medium",
    }
