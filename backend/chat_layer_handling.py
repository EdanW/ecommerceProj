"""
Chat layer for the Gestational Diabetes Craving Assistant (Nouri).

Parses a user's free-text craving into a structured JSON payload for the
recommendation model, with negation-aware extraction and short follow-ups
when required fields are missing.

Language: English
"""

# =============================================================================
## STANDARD LIBRARY IMPORTS ##
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .ds_service.utils.chat_layer_ds_utils import _analyze_glucose_trend
from .ds_service.predict.predict import predict

# =============================================================================
## LOCAL IMPORTS ##
# =============================================================================

from .chat_layer_constants import PENDING_TTL_SECONDS, FOOD_CONTEXT_KEYWORDS
from .chat_layer_time_utils import (
    get_time_of_day_from_time,
    time_of_day_from_meal_type,
)
from .chat_layer_nlp import nlp
from .chat_layer_extractors import (
    human_list,
    extract_foods_with_negation_spacy,
    extract_categories_with_negation_spacy,
    extract_meal_type_spacy,
    extract_intensity_spacy,
    parse_meal_type_answer,
)
from .chat_layer_unsure import is_unsure_response, build_unsure_craving_data
from .chat_layer_food_database import FOOD_DATABASE

# =============================================================================
## LOGGING ##
# =============================================================================

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)

# =============================================================================
## ENGINE ##
# =============================================================================


class AIEngine:
    """Stateful extractor that converts user messages into a JSON payload for the model."""

    def __init__(self):
        """Initialize in-memory follow-up state keyed by user_id."""
        self.pending_extractions: Dict[str, Dict[str, Any]] = {}
        logger.info("AI Engine initialized (SpaCy-based NLP)")

    @staticmethod
    def _is_food_related(message: str) -> bool:
        """Check if the message has any food-related context."""
        message_lower = message.lower()
        # Check for food-context keywords (hungry, craving, eat, etc.)
        if any(kw in message_lower.split() for kw in FOOD_CONTEXT_KEYWORDS):
            return True
        # Check if any known food name appears in the message
        if any(food in message_lower for food in FOOD_DATABASE):
            return True
        return False

    def _cleanup_expired_pending(self):
        """Drop pending follow-up states older than the configured TTL."""
        now = datetime.now()
        expired_users = [
            user_id
            for user_id, data in self.pending_extractions.items()
            if (now - data.get("created_at", now))
            > timedelta(seconds=PENDING_TTL_SECONDS)
        ]
        for user_id in expired_users:
            del self.pending_extractions[user_id]
            logger.info("Cleared expired pending extraction for user")

    def extract_to_json(
        self,
        user_message: str,
        glucose_level: int,
        glucose_history: List[dict],
        pregnancy_week: int,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Parse a user message into a structured payload.

        If required information is missing, returns a follow-up question and stores
        partial state keyed by user_id.
        """
        self._cleanup_expired_pending()

        # Check if this is a follow-up to a previous extraction
        if user_id in self.pending_extractions:
            return self._handle_follow_up(
                user_message, glucose_level, glucose_history, pregnancy_week, user_id
            )

        # Unsure / undecided initial message — prompt for preferences
        if is_unsure_response(user_message):
            craving_data = build_unsure_craving_data()
            self.pending_extractions[user_id] = {
                "craving_data": craving_data,
                "glucose_level": glucose_level,
                "pregnancy_week": pregnancy_week,
                "missing": "food",
                "created_at": datetime.now(),
            }
            return {
                "complete": False,
                "follow_up_question": (
                    "No problem! Are you in the mood for something "
                    "sweet, salty, savory, or something else?"
                ),
                "missing_field": "food",
                "partial_data": craving_data,
            }

        doc = nlp(user_message)

        wanted_foods, excluded_foods = extract_foods_with_negation_spacy(doc, user_message)
        wanted_categories, excluded_categories = extract_categories_with_negation_spacy(
            doc, user_message, wanted_foods, excluded_foods
        )
        meal_type = extract_meal_type_spacy(doc, wanted_foods)
        intensity = extract_intensity_spacy(doc)

        craving_data = {
            "foods": wanted_foods,
            "categories": wanted_categories,
            "excluded_foods": excluded_foods,
            "excluded_categories": excluded_categories,
            "meal_type": meal_type,
            "intensity": intensity,
        }

        # Case 1 — No positive food or category signal
        if not wanted_foods and not wanted_categories:
            # 1A — Only exclusions provided
            if excluded_foods or excluded_categories:
                if excluded_foods:
                    excluded_text = human_list(excluded_foods)
                    message = f"Got it — no {excluded_text}. What would you like instead?"
                elif excluded_categories:
                    excluded_text = human_list(excluded_categories)
                    message = f"Got it — nothing {excluded_text}. What would you like instead?"
                else:
                    message = "Got it. What would you like instead?"

                self.pending_extractions[user_id] = {
                    "craving_data": craving_data,
                    "glucose_level": glucose_level,
                    "pregnancy_week": pregnancy_week,
                    "missing": "food",
                    "created_at": datetime.now(),
                }

                return {
                    "complete": False,
                    "follow_up_question": message,
                    "missing_field": "food",
                    "partial_data": craving_data,
                }

            # 1B — Off-topic detection
            if not self._is_food_related(user_message):
                logger.info("Off-topic message detected: %s", user_message)
                return {
                    "complete": False,
                    "off_topic": True,
                    "follow_up_question": (
                        "I'm sorry, but I can only help with food and meal recommendations. "
                        "Tell me what you're craving and I'll find something great for you! 🍽️"
                    ),
                }

            # 1C — Food-related but too vague to act on
            self.pending_extractions[user_id] = {
                "craving_data": craving_data,
                "glucose_level": glucose_level,
                "pregnancy_week": pregnancy_week,
                "missing": "food",
                "created_at": datetime.now(),
            }

            return {
                "complete": False,
                "follow_up_question": "What kind of food are you craving?",
                "missing_field": "food",
                "partial_data": craving_data,
            }

        # Case 2 — Categories present but meal context unknown
        if not wanted_foods and wanted_categories and not meal_type:
            self.pending_extractions[user_id] = {
                "craving_data": craving_data,
                "glucose_level": glucose_level,
                "pregnancy_week": pregnancy_week,
                "missing": "meal_type",
                "created_at": datetime.now(),
            }

            category_str = " and ".join(wanted_categories)
            return {
                "complete": False,
                "follow_up_question": (
                    f"Something {category_str} sounds good! "
                    "Is this for a snack or a meal (breakfast/lunch/dinner)?"
                ),
                "missing_field": "meal_type",
                "partial_data": craving_data,
            }

        # Case 3 — Sufficient information to recommend
        return self._build_complete_response(craving_data, glucose_level, glucose_history, pregnancy_week)

    def _handle_follow_up(
        self,
        user_message: str,
        glucose_level: int,
        glucose_history: List[dict],
        pregnancy_week: int,
        user_id: str,
    ) -> Dict[str, Any]:
        """Handle the user's reply to a previous follow-up question and finalize extraction."""
        pending = self.pending_extractions.get(user_id)
        if not pending:
            self.pending_extractions.pop(user_id, None)
            return self.extract_to_json(
                user_message, glucose_level, glucose_history, pregnancy_week, user_id + "_new"
            )

        craving_data = pending["craving_data"]
        missing_field = pending.get("missing")

        # Still unsure on follow-up — proceed with whatever data we have.
        # BUT we still parse the message for exclusions and meal type first,
        # because the user might say "I don't know but no pasta" or "I want dinner
        # but I'm not sure what" — we shouldn't throw that info away.
        if is_unsure_response(user_message):
            doc = nlp(user_message)
            _, new_excluded_foods = extract_foods_with_negation_spacy(doc, user_message)
            _, new_excluded_categories = extract_categories_with_negation_spacy(
                doc, user_message, [], new_excluded_foods
            )
            excluded_foods = list(set(craving_data.get("excluded_foods", []) + new_excluded_foods))
            excluded_categories = list(set(craving_data.get("excluded_categories", []) + new_excluded_categories))
            del self.pending_extractions[user_id]
            unsure_data = build_unsure_craving_data(
                excluded_foods=excluded_foods,
                excluded_categories=excluded_categories,
            )
            # Preserve the meal_type from the previous turn — without this it
            # defaults to "snack" and we get completely wrong suggestions
            unsure_data["meal_type"] = (
                extract_meal_type_spacy(doc, []) or craving_data.get("meal_type")
            )
            return self._build_complete_response(
                unsure_data, glucose_level, glucose_history, pregnancy_week
            )

        del self.pending_extractions[user_id]

        doc = nlp(user_message)

        if missing_field == "meal_type":
            meal_type = self._parse_meal_type_answer(doc, user_message)
            if meal_type:
                craving_data["meal_type"] = meal_type

        elif missing_field == "food":
            wanted_foods, excluded_foods = extract_foods_with_negation_spacy(doc, user_message)
            wanted_categories, excluded_categories = extract_categories_with_negation_spacy(
                doc, user_message, wanted_foods, excluded_foods
            )

            existing_excluded_foods = craving_data.get("excluded_foods", [])
            existing_excluded_categories = craving_data.get("excluded_categories", [])

            craving_data["foods"] = wanted_foods or craving_data.get("foods", [])
            craving_data["categories"] = wanted_categories or craving_data.get("categories", [])
            craving_data["excluded_foods"] = list(set(existing_excluded_foods + excluded_foods))
            craving_data["excluded_categories"] = list(set(existing_excluded_categories + excluded_categories))
            craving_data["meal_type"] = extract_meal_type_spacy(doc, wanted_foods) or craving_data.get("meal_type")

        return self._build_complete_response(craving_data, glucose_level, glucose_history, pregnancy_week)

    def _parse_meal_type_answer(self, doc, message: str) -> Optional[str]:
        """Parse meal type from a short follow-up reply using matcher first, then synonyms."""
        return parse_meal_type_answer(doc, message)

    def _build_complete_response(
        self,
        craving_data: dict,
        glucose_level: int,
        glucose_history: List[dict],
        pregnancy_week: int,
    ) -> Dict[str, Any]:
        """Build the final payload for the recommendation model."""
        logger.debug("entered _build_complete_response")
        meal_type = (craving_data.get("meal_type") or "snack").lower().strip()
        mapped_time = time_of_day_from_meal_type(meal_type)
        time_of_day = mapped_time if mapped_time else get_time_of_day_from_time()

        avg_glucose, trend = _analyze_glucose_trend(glucose_history)
        json_for_model = {
            "craving": {
                "foods": craving_data.get("foods", []),
                "categories": craving_data.get("categories", []),
                "excluded_foods": craving_data.get("excluded_foods", []),
                "excluded_categories": craving_data.get("excluded_categories", []),
                "time_of_day": time_of_day,
                "meal_type": meal_type,
                "intensity": craving_data.get("intensity", "medium"),
            },
            "glucose_level": glucose_level,
            "glucose_avg": avg_glucose,
            "glucose_trend": trend,
            "pregnancy_week": pregnancy_week,
        }
        logger.info("json_for_model: %s", json_for_model)

        model_response = predict(json_for_model)
        logger.info("model_response: %s", model_response)
        return {
            "complete": True,
            "data": model_response,
            "craving_input": {
                "foods": craving_data.get("foods", []),
                "categories": craving_data.get("categories", []),
            },
        }

    def clear_pending(self, user_id: str = "default"):
        """Clear pending follow-up state for a user."""
        if user_id in self.pending_extractions:
            del self.pending_extractions[user_id]


# =============================================================================
## MODULE INSTANCE ##
# =============================================================================

engine = AIEngine()
