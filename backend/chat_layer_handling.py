"""
Chat layer for the Gestational Diabetes Craving Assistant (Eat42).

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

from .chat_layer_constants import PENDING_TTL_SECONDS
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

        if user_id in self.pending_extractions:
            return self._handle_follow_up(
                user_message, glucose_level, glucose_history, pregnancy_week, user_id
            )

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

        # Case 1 - No wanted foods or categories specified, maybe exclusions
        if not wanted_foods and not wanted_categories:
            if excluded_foods or excluded_categories:
                if excluded_foods:
                    excluded_text = human_list(excluded_foods)
                    message = f"Got it — no {excluded_text}. What would you like instead?"
                elif excluded_categories:
                    excluded_text = human_list(excluded_categories)
                    message = f"Got it — nothing {excluded_text}. What would you like instead?"
                else:
                    message = "Got it. What would you like instead?"
                return {
                "complete": False,
                "follow_up_question": message,
                "missing_field": "food",
                "partial_data": craving_data,
                }

            return {
                "complete": False,
                "follow_up_question": (
                    "What kind of food are you craving? For example: chocolate, pizza, something sweet..."
                ),
                "missing_field": "food",
                "partial_data": craving_data,
            }

        # Case 2 - Wanted categories but no foods, missing meal type
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

        # Case 3 - All required info present
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
        del self.pending_extractions[user_id]

        doc = nlp(user_message)

        if missing_field == "meal_type":
            meal_type = self._parse_meal_type_answer(doc, user_message)
            if meal_type:
                craving_data["meal_type"] = meal_type
                return self._build_complete_response(
                    craving_data, glucose_level, glucose_history, pregnancy_week
                )

            self.pending_extractions[user_id] = {
                "craving_data": craving_data,
                "glucose_level": glucose_level,
                "pregnancy_week": pregnancy_week,
                "missing": "meal_type",
                "created_at": datetime.now(),
            }
            return {
                "complete": False,
                "follow_up_question": "Is this for a snack, breakfast, lunch, or dinner?",
                "missing_field": "meal_type",
                "partial_data": craving_data,
            }

        if missing_field == "food":
            wanted_foods, excluded_foods = extract_foods_with_negation_spacy(doc, user_message)
            wanted_categories, excluded_categories = extract_categories_with_negation_spacy(
                doc, user_message, wanted_foods, excluded_foods
            )

            existing_excluded_foods = craving_data.get("excluded_foods", [])
            existing_excluded_categories = craving_data.get("excluded_categories", [])
            all_excluded_foods = list(set(existing_excluded_foods + excluded_foods))
            all_excluded_categories = list(set(existing_excluded_categories + excluded_categories))

            if wanted_foods or wanted_categories:
                craving_data["foods"] = wanted_foods
                craving_data["categories"] = wanted_categories
                craving_data["excluded_foods"] = all_excluded_foods
                craving_data["excluded_categories"] = all_excluded_categories
                craving_data["meal_type"] = extract_meal_type_spacy(doc, wanted_foods)

                if not craving_data["meal_type"] and not wanted_foods:
                    self.pending_extractions[user_id] = {
                        "craving_data": craving_data,
                        "glucose_level": glucose_level,
                        "pregnancy_week": pregnancy_week,
                        "missing": "meal_type",
                        "created_at": datetime.now(),
                    }
                    return {
                        "complete": False,
                        "follow_up_question": "Is this for a snack or a meal?",
                        "missing_field": "meal_type",
                        "partial_data": craving_data,
                    }

                return self._build_complete_response(
                    craving_data, glucose_level, glucose_history, pregnancy_week
                )

            craving_data["excluded_foods"] = all_excluded_foods
            craving_data["excluded_categories"] = all_excluded_categories

            if excluded_foods:
                return {
                    "complete": False,
                    "follow_up_question": f"Okay, no {', '.join(excluded_foods)}. What would you like instead?",
                    "missing_field": "food",
                    "partial_data": craving_data,
                }
            return {
                "complete": False,
                "follow_up_question": (
                    "I didn't catch that. What food are you craving? (e.g., chocolate, pizza, chips)"
                ),
                "missing_field": "food",
                "partial_data": craving_data,
            }

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
        print("entered _build_complete_response")
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
        print("json_for_model: ", json_for_model)

        model_response = predict(json_for_model)
        print(model_response)
        return {"complete": True, "data": model_response}

    def clear_pending(self, user_id: str = "default"):
        """Clear pending follow-up state for a user."""
        if user_id in self.pending_extractions:
            del self.pending_extractions[user_id]

    def translate_response(self, model_response: Dict[str, Any], original_message: str = "") -> str:
        """Convert the model JSON response into a short user-facing sentence."""
        recommendation = model_response.get("recommendation", "a healthier alternative")
        explanation = model_response.get("explanation", "")

        response = f"Based on your levels, here's a great choice: {recommendation}"
        if explanation:
            response += f" — {explanation}"
        return response + " 💜"


# =============================================================================
## MODULE INSTANCE ##
# =============================================================================

engine = AIEngine()
