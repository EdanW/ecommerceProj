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
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, Tuple, List, Set

# =============================================================================
## THIRD-PARTY IMPORTS ##
# =============================================================================

import spacy
from spacy.matcher import PhraseMatcher

# =============================================================================
## FOOD DATABASE IMPORTS ##
# =============================================================================

from .chat_layer_food_database import (
    FOOD_DATABASE,
    CATEGORY_KEYWORDS,
    MEAL_TYPE_KEYWORDS,
    INTENSITY_KEYWORDS,
)

# =============================================================================
## CONFIG ##
# =============================================================================

TIMEZONE = ZoneInfo("Asia/Jerusalem")
PENDING_TTL_SECONDS = 600

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
## SPACY INITIALIZATION ##
# =============================================================================

try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("SpaCy model loaded: en_core_web_sm")
except OSError:
    logger.warning("SpaCy model not found. Downloading: en_core_web_sm")
    import subprocess

    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
    nlp = spacy.load("en_core_web_sm")
    logger.info("SpaCy model downloaded and loaded: en_core_web_sm")

# =============================================================================
## MATCHERS ##
# =============================================================================

food_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
food_matcher.add("FOOD", [nlp.make_doc(food) for food in FOOD_DATABASE.keys()])

category_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
for category, keywords in CATEGORY_KEYWORDS.items():
    category_matcher.add(category, [nlp.make_doc(kw) for kw in keywords])

meal_type_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
for meal_type, keywords in MEAL_TYPE_KEYWORDS.items():
    meal_type_matcher.add(meal_type, [nlp.make_doc(kw) for kw in keywords])

intensity_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
for intensity, keywords in INTENSITY_KEYWORDS.items():
    intensity_matcher.add(intensity, [nlp.make_doc(kw) for kw in keywords])

logger.info("Initialized matchers (foods=%d)", len(FOOD_DATABASE))

# =============================================================================
## NEGATION SIGNALS ##
# =============================================================================

NEGATION_TOKENS = {
    "not",
    "no",
    "never",
    "n't",
    "dont",
    "without",
    "except",
    "nothing",
    "none",
    "neither",
    "nor",
}

NEGATION_LEMMAS = {
    "hate",
    "dislike",
    "avoid",
    "skip",
    "exclude",
    "reject",
    "detest",
    "loathe",
}

EXCLUSION_PHRASES = [
    "don't want",
    "dont want",
    "do not want",
    "don't like",
    "dont like",
    "do not like",
    "don't feel like",
    "dont feel like",
    "not in the mood for",
    "not craving",
    "can't stand",
    "cant stand",
    "cannot stand",
    "sick of",
    "tired of",
    "allergic to",
    "intolerant to",
    "stay away from",
    "keep away from",
    "anything but",
    "but not",
]

# =============================================================================
## TIME HELPERS ##
# =============================================================================


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


# =============================================================================
## NEGATION DETECTION ##
# =============================================================================


def find_negated_tokens(doc: spacy.tokens.Doc) -> Set[int]:
    """
    Return token indices considered negated.

    Uses dependency parsing (neg relation) when available, with fallbacks for:
    - standalone negation tokens (e.g., "no", "without")
    - negation-implying verbs (e.g., "avoid", "hate") applied to their objects
    """
    negated_indices: Set[int] = set()

    for token in doc:
        if token.dep_ == "neg":
            head = token.head
            negated_indices.add(head.i)
            for child in head.children:
                if child.dep_ != "neg":
                    negated_indices.add(child.i)
                    for descendant in child.subtree:
                        negated_indices.add(descendant.i)

        if token.lower_ in NEGATION_TOKENS:
            for i in range(token.i + 1, min(token.i + 5, len(doc))):
                if doc[i].sent == token.sent:
                    negated_indices.add(i)

        if token.lemma_.lower() in NEGATION_LEMMAS:
            for child in token.children:
                if child.dep_ in ("dobj", "pobj", "attr", "oprd"):
                    negated_indices.add(child.i)
                    for descendant in child.subtree:
                        negated_indices.add(descendant.i)

    return negated_indices


def check_exclusion_phrases(text: str) -> List[Tuple[int, int]]:
    """
    Return character spans following exclusion phrases (e.g., "allergic to", "sick of").

    Used as a lightweight fallback when dependency parsing misses negation scope.
    """
    text_lower = text.lower()
    spans: List[Tuple[int, int]] = []

    for phrase in EXCLUSION_PHRASES:
        start = 0
        while True:
            pos = text_lower.find(phrase, start)
            if pos == -1:
                break

            end_pos = pos + len(phrase) + 50
            for punct in [".", ",", "!", "?", " but ", " and i ", " however "]:
                punct_pos = text_lower.find(punct, pos + len(phrase))
                if punct_pos != -1 and punct_pos < end_pos:
                    end_pos = punct_pos

            spans.append((pos, end_pos))
            start = pos + 1

    return spans

# =============================================================================
## READBALITY HELPERS ##
# =============================================================================

def human_list(items: List[str]) -> str:
    """
    Convert ['a', 'b', 'c'] → 'a, b, and c'
    """
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


# =============================================================================
## EXTRACTION ##
# =============================================================================


def extract_foods_with_negation_spacy(
    doc: spacy.tokens.Doc, text: str
) -> Tuple[List[str], List[str]]:
    """
    Extract foods and classify them as wanted vs excluded.

    Foods are matched via PhraseMatcher against FOOD_DATABASE keys. Exclusion is
    determined by negation scope (dependency-based) and exclusion-phrase spans.
    """
    wanted_foods: List[str] = []
    excluded_foods: List[str] = []

    negated_indices = find_negated_tokens(doc)
    exclusion_spans = check_exclusion_phrases(text)
    matches = food_matcher(doc)

    for _, start, end in matches:
        span = doc[start:end]
        food_text = span.text.lower()

        if food_text in FOOD_DATABASE:
            food_key = food_text
        else:
            lemmatized = " ".join(t.lemma_.lower() for t in span)
            food_key = lemmatized if lemmatized in FOOD_DATABASE else food_text

        is_negated = any(i in negated_indices for i in range(start, end))
        span_start_char = span.start_char
        for ex_start, ex_end in exclusion_spans:
            if ex_start <= span_start_char <= ex_end:
                is_negated = True
                break

        if is_negated:
            if food_key not in excluded_foods:
                excluded_foods.append(food_key)
        else:
            if food_key not in wanted_foods:
                wanted_foods.append(food_key)

    return wanted_foods, excluded_foods


def extract_categories_with_negation_spacy(
    doc: spacy.tokens.Doc,
    text: str,
    wanted_foods: List[str],
    excluded_foods: List[str],
) -> Tuple[List[str], List[str]]:
    """
    Extract taste categories (e.g., sweet, salty) as wanted vs excluded.

    Categories come from:
    - explicit mentions in text (PhraseMatcher)
    - inference from matched foods via FOOD_DATABASE
    Explicit mentions override inferred conflicts.
    """
    wanted_categories: Set[str] = set()
    excluded_categories: Set[str] = set()

    negated_indices = find_negated_tokens(doc)
    exclusion_spans = check_exclusion_phrases(text)

    for food in wanted_foods:
        if food in FOOD_DATABASE:
            wanted_categories.update(FOOD_DATABASE[food]["categories"])

    explicit_wanted: Set[str] = set()
    explicit_excluded: Set[str] = set()

    matches = category_matcher(doc)
    for match_id, start, end in matches:
        category = nlp.vocab.strings[match_id]
        span = doc[start:end]

        is_negated = any(i in negated_indices for i in range(start, end))
        span_start_char = span.start_char
        for ex_start, ex_end in exclusion_spans:
            if ex_start <= span_start_char <= ex_end:
                is_negated = True
                break

        if is_negated:
            explicit_excluded.add(category)
        else:
            explicit_wanted.add(category)

    wanted_categories.update(explicit_wanted)
    excluded_categories.update(explicit_excluded)

    wanted_categories -= explicit_excluded
    excluded_categories -= explicit_wanted

    return list(wanted_categories), list(excluded_categories)


def extract_meal_type_spacy(doc: spacy.tokens.Doc, foods: List[str]) -> Optional[str]:
    """Return meal type from explicit mention, else infer from the first detected food."""
    matches = meal_type_matcher(doc)
    if matches:
        match_id, _, _ = matches[0]
        return nlp.vocab.strings[match_id]

    if foods:
        first_food = foods[0]
        if first_food in FOOD_DATABASE:
            return FOOD_DATABASE[first_food]["meal_type"]

    return None


def extract_intensity_spacy(doc: spacy.tokens.Doc) -> str:
    """Return craving intensity ("high"/"low") from matches, else "medium"."""
    matches = intensity_matcher(doc)
    if matches:
        match_id, _, _ = matches[0]
        return nlp.vocab.strings[match_id]
    return "medium"


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

    def _parse_meal_type_answer(self, doc: spacy.tokens.Doc, message: str) -> Optional[str]:
        """Parse meal type from a short follow-up reply using matcher first, then synonyms."""
        matches = meal_type_matcher(doc)
        if matches:
            match_id, _, _ = matches[0]
            return nlp.vocab.strings[match_id]

        message_lower = message.lower().strip()
        meal_type_synonyms = {
            "snack": ["snack", "snacking", "between meals", "quick bite", "nishnush", "sweet treat"],
            "breakfast": ["breakfast", "morning", "brekkie"],
            "lunch": ["lunch", "midday", "noon"],
            "dinner": ["dinner", "supper", "evening", "tonight"],
            "dessert": ["dessert", "after dinner", "sweet ending"],
        }

        for meal_type, synonyms in meal_type_synonyms.items():
            for synonym in synonyms:
                if synonym in message_lower:
                    return meal_type

        if "meal" in message_lower:
            tod = get_time_of_day_from_time()
            if tod == "morning":
                return "breakfast"
            if tod == "afternoon":
                return "lunch"
            return "dinner"

        return None

    def _build_complete_response(
        self,
        craving_data: dict,
        glucose_level: int,
        glucose_history: List[dict],
        pregnancy_week: int,
    ) -> Dict[str, Any]:
        """Build the final payload for the recommendation model."""
        meal_type = (craving_data.get("meal_type") or "snack").lower().strip()
        mapped_time = time_of_day_from_meal_type(meal_type)
        time_of_day = mapped_time if mapped_time else get_time_of_day_from_time()

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
            "glucose_history": glucose_history,
            "pregnancy_week": pregnancy_week,
        }

        return {"complete": True, "data": json_for_model}

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
