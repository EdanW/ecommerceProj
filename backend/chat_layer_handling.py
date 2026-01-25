"""
Chat layer for AI Engine for Gestational Diabetes Craving Assistant
=====================================================

This module parses user cravings using keyword matching.

Features:
- 100% in-house parsing (no API calls)
- Keyword-based food and category detection
- Smart meal type inference
- Follow-up questions when info is incomplete
- NEGATION DETECTION: "I don't want X" → excluded_foods
- English only

Project: Eat42 - Gestational Diabetes Support App
"""

import re
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, Tuple, List

# Import from our food database
from .chat_layer_food_database import (
    FOOD_DATABASE,
    CATEGORY_KEYWORDS,
    MEAL_TYPE_KEYWORDS,
    INTENSITY_KEYWORDS,
)

## CONFIGURATION ## 

TIMEZONE = ZoneInfo("Asia/Jerusalem")
PENDING_TTL_SECONDS = 600  # Follow-up state expires after 10 minutes

# Negation phrases to detect "I don't want X"
NEGATION_PHRASES = [
    "don't want", "dont want", "do not want",
    "don't like", "dont like", "do not like",
    "don't feel like", "dont feel like", "do not feel like",
    "not in the mood for", "not craving",
    "no ", "not ", "never ", "hate ", "hates ",
    "can't stand", "cant stand", "cannot stand",
    "sick of", "tired of", "avoid", "avoiding",
    "allergic to", "intolerant to",
    "stay away from", "keep away from",
    "without ", "except ", "but not ", "anything but ",
]

## LOGGING SETUP ##

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


## HELPER FUNCTIONS ##

def get_time_of_day_from_time() -> str:
    """Get time of day based on current time"""
    now = datetime.now(TIMEZONE)
    hour = now.hour
    
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"

def time_of_day_from_meal_type(meal_type: Optional[str]) -> Optional[str]:
    """
    Map meal_type to an appropriate time_of_day when the user implies a meal
    Return None if we should fall back to current time
    """
    if not meal_type:
        return None

    meal_type = meal_type.lower().strip()

    if meal_type == "breakfast":
        return "morning"
    if meal_type == "lunch":
        return "afternoon"
    if meal_type == "dinner":
        return "evening"
    # dessert is usually after dinner
    if meal_type == "dessert":
        return "evening"

    return None


def find_negation_context(message: str) -> List[Tuple[int, int]]:
    """
    Find positions in the message where negation applies.
    Returns list of (start, end) tuples marking negated regions.
    """
    message_lower = message.lower()
    negated_regions = []
    
    for phrase in NEGATION_PHRASES:
        start = 0
        while True:
            pos = message_lower.find(phrase, start)
            if pos == -1:
                break
            # Define the negated region
            end_pos = pos + len(phrase) + 50
            # Look for sentence boundaries
            for punct in ['.', ',', '!', '?', ' but ', ' and i ', ' however ']:
                punct_pos = message_lower.find(punct, pos + len(phrase))
                if punct_pos != -1 and punct_pos < end_pos:
                    end_pos = punct_pos
            negated_regions.append((pos, end_pos))
            start = pos + 1
    
    return negated_regions


def is_in_negated_region(position: int, negated_regions: List[Tuple[int, int]]) -> bool:
    """Check if a position falls within any negated region."""
    for start, end in negated_regions:
        if start <= position <= end:
            return True
    return False


def extract_foods_with_negation(message: str) -> Tuple[List[str], List[str]]:
    """
    Extract food items, separating wanted from excluded foods.
    
    Returns:
        (wanted_foods, excluded_foods)
    """
    message_lower = message.lower()
    wanted_foods = []
    excluded_foods = []
    
    # Find negated regions
    negated_regions = find_negation_context(message)
    
    # Sort by length (longest first) to avoid substring issues
    sorted_foods = sorted(FOOD_DATABASE.keys(), key=len, reverse=True)
    
    # Track what we've already matched to avoid duplicates
    matched_positions = set()
    
    for food in sorted_foods:
        start = 0
        while True:
            pos = message_lower.find(food, start)
            if pos == -1:
                break
            
            # Check if this position overlaps with already matched food
            food_range = set(range(pos, pos + len(food)))
            if food_range & matched_positions:
                start = pos + 1
                continue
            
            # Mark these positions as matched
            matched_positions.update(food_range)
            
            # Check if this food is in a negated context
            if is_in_negated_region(pos, negated_regions):
                if food not in excluded_foods:
                    excluded_foods.append(food)
            else:
                if food not in wanted_foods:
                    wanted_foods.append(food)
            
            start = pos + 1
    
    return wanted_foods, excluded_foods


def extract_categories_with_negation(message: str, wanted_foods: list, excluded_foods: list) -> Tuple[List[str], List[str]]:
    """
    Extract taste/texture categories, separating wanted from excluded.

    Fixes:
    - word-boundary matching for single-word keywords (prevents spicy->icy)
    - scans ALL occurrences (not just first) so negation can apply correctly per mention
    """
    message_lower = message.lower()
    wanted_categories = set()
    excluded_categories = set()

    # Find negated regions
    negated_regions = find_negation_context(message)

    # Categories from wanted foods
    for food in wanted_foods:
        if food in FOOD_DATABASE:
            wanted_categories.update(FOOD_DATABASE[food]["categories"])

    # Explicit category keywords
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            keyword_l = keyword.lower().strip()
            for pos in _find_all_keyword_positions(message_lower, keyword_l):
                if is_in_negated_region(pos, negated_regions):
                    excluded_categories.add(category)
                else:
                    wanted_categories.add(category)

    return list(wanted_categories), list(excluded_categories)


def extract_meal_type(message: str, foods: list) -> Optional[str]:
    """Extract meal type from message or infer from foods."""
    message_lower = message.lower()
    
    # First check for explicit meal type keywords
    for meal_type, keywords in MEAL_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                return meal_type
    
    # If we have foods, infer from the first food's typical meal type
    if foods:
        first_food = foods[0]
        if first_food in FOOD_DATABASE:
            return FOOD_DATABASE[first_food]["meal_type"]
    
    # Can't determine meal type
    return None


def extract_intensity(message: str) -> str:
    """Extract craving intensity from message."""
    message_lower = message.lower()
    
    for intensity, keywords in INTENSITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                return intensity
    
    return "medium"  # Default

def _find_all_keyword_positions(text: str, keyword: str) -> List[int]:
    """
    Return all start positions where keyword appears in text.

    Rules:
    - Multi-word keywords (contain spaces): substring match, all occurrences.
    - Single-word keywords: word-boundary regex match (prevents 'spicy' -> 'icy').
    """
    if not keyword:
        return []

    if " " in keyword:
        positions = []
        start = 0
        while True:
            pos = text.find(keyword, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions

    pattern = re.compile(rf"\b{re.escape(keyword)}\b")
    return [m.start() for m in pattern.finditer(text)]


## MAIN CLASS ##

class AIEngine:
    """
    AI Engine for craving extraction - NO API CALLS!
    
    Uses keyword matching for fast, free, unlimited parsing.
    Now with NEGATION DETECTION!
    """
    
    def __init__(self):
        # Store partial data for multi-turn conversations
        self.pending_extractions: Dict[str, Dict[str, Any]] = {}
        logger.info("AI Engine initialized (keyword-based, no API)")
    
    
    def _cleanup_expired_pending(self):
        """Remove expired pending extractions."""
        now = datetime.now()
        expired_users = [
            user_id for user_id, data in self.pending_extractions.items()
            if (now - data.get("created_at", now)) > timedelta(seconds=PENDING_TTL_SECONDS)
        ]
        for user_id in expired_users:
            del self.pending_extractions[user_id]
            logger.info("Cleared expired pending extraction for user")
    
    
    def extract_to_json(
        self, 
        user_message: str, 
        glucose_level: int, 
        pregnancy_week: int,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Extract craving from user message using keyword matching.
        
        Returns:
            - If complete: {"complete": True, "data": {...}}
            - If need follow-up: {"complete": False, "follow_up_question": "...", ...}
        """
        # Cleanup expired pending states
        self._cleanup_expired_pending()
        
        # Check if this is a follow-up answer
        if user_id in self.pending_extractions:
            return self._handle_follow_up(user_message, glucose_level, pregnancy_week, user_id)
        
        # Parse the message
        wanted_foods, excluded_foods = extract_foods_with_negation(user_message)
        wanted_categories, excluded_categories = extract_categories_with_negation(
            user_message, wanted_foods, excluded_foods
        )
        meal_type = extract_meal_type(user_message, wanted_foods)
        intensity = extract_intensity(user_message)

        craving_data = {
            "foods": wanted_foods,
            "categories": wanted_categories,
            "excluded_foods": excluded_foods,
            "excluded_categories": excluded_categories,
            "meal_type": meal_type,
            "intensity": intensity,
        }
        
        # Check if we need to ask follow-up questions
        # Case 1: No wanted foods AND no wanted categories - we don't understand what they want
        if not wanted_foods and not wanted_categories:
            # But if they said what they DON'T want acknowledge it
            if excluded_foods or excluded_categories:
                return {
                    "complete": False,
                    "follow_up_question": f"Got it, no {', '.join(excluded_foods) if excluded_foods else 'that'}! What would you like instead?",
                    "missing_field": "food",
                    "partial_data": craving_data
                }
            else:
                return {
                    "complete": False,
                    "follow_up_question": "What kind of food are you craving? For example: chocolate, pizza, something sweet...",
                    "missing_field": "food",
                    "partial_data": craving_data
                }
        
        # Case 2: Categories but no specific food AND no meal type
        if not wanted_foods and wanted_categories and not meal_type:
            # Store for follow-up
            self.pending_extractions[user_id] = {
                "craving_data": craving_data,
                "glucose_level": glucose_level,
                "pregnancy_week": pregnancy_week,
                "missing": "meal_type",
                "created_at": datetime.now()
            }
            
            category_str = " and ".join(wanted_categories)
            return {
                "complete": False,
                "follow_up_question": f"Something {category_str} sounds good! Is this for a snack or a meal (breakfast/lunch/dinner)?",
                "missing_field": "meal_type",
                "partial_data": craving_data
            }
        
        # We have enough info
        return self._build_complete_response(craving_data, glucose_level, pregnancy_week)
    
    
    def _handle_follow_up(self, user_message: str, glucose_level: int, pregnancy_week: int, user_id: str) -> Dict[str, Any]:
        """Handle user's answer to a follow-up question."""
        
        pending = self.pending_extractions.get(user_id)
        if not pending:
            self.pending_extractions.pop(user_id, None)
            return self.extract_to_json(user_message, glucose_level, pregnancy_week, user_id + "_new")

        craving_data = pending["craving_data"]
        missing_field = pending.get("missing")
        
        # Remove from pending
        del self.pending_extractions[user_id]
        
        if missing_field == "meal_type":
            # Try to extract meal type from answer
            meal_type = self._parse_meal_type_answer(user_message)
            
            if meal_type:
                craving_data["meal_type"] = meal_type
                return self._build_complete_response(craving_data, glucose_level, pregnancy_week)
            else:
                # Still unclear, ask again
                self.pending_extractions[user_id] = {
                    "craving_data": craving_data,
                    "glucose_level": glucose_level,
                    "pregnancy_week": pregnancy_week,
                    "missing": "meal_type",
                    "created_at": datetime.now()
                }
                return {
                    "complete": False,
                    "follow_up_question": "Is this for a snack, breakfast, lunch, or dinner?",
                    "missing_field": "meal_type",
                    "partial_data": craving_data
                }
        
        elif missing_field == "food":
            # They should have given us a food - parse with negation
            wanted_foods, excluded_foods = extract_foods_with_negation(user_message)
            wanted_categories, excluded_categories = extract_categories_with_negation(user_message, wanted_foods, excluded_foods)
            
            # Merge with existing excluded items
            existing_excluded_foods = craving_data.get("excluded_foods", [])
            existing_excluded_categories = craving_data.get("excluded_categories", [])
            
            all_excluded_foods = list(set(existing_excluded_foods + excluded_foods))
            all_excluded_categories = list(set(existing_excluded_categories + excluded_categories))
            
            if wanted_foods or wanted_categories:
                craving_data["foods"] = wanted_foods
                craving_data["categories"] = wanted_categories
                craving_data["excluded_foods"] = all_excluded_foods
                craving_data["excluded_categories"] = all_excluded_categories
                craving_data["meal_type"] = extract_meal_type(user_message, wanted_foods)
                
                # If we now have food but no meal type ask for it
                if not craving_data["meal_type"] and not wanted_foods:
                    self.pending_extractions[user_id] = {
                        "craving_data": craving_data,
                        "glucose_level": glucose_level,
                        "pregnancy_week": pregnancy_week,
                        "missing": "meal_type",
                        "created_at": datetime.now()
                    }
                    return {
                        "complete": False,
                        "follow_up_question": "Is this for a snack or a meal?",
                        "missing_field": "meal_type",
                        "partial_data": craving_data
                    }
                
                return self._build_complete_response(craving_data, glucose_level, pregnancy_week)
            else:
                # Still don't understand what they want
                craving_data["excluded_foods"] = all_excluded_foods
                craving_data["excluded_categories"] = all_excluded_categories
                
                if excluded_foods:
                    return {
                        "complete": False,
                        "follow_up_question": f"Okay, no {', '.join(excluded_foods)}. What would you like instead?",
                        "missing_field": "food",
                        "partial_data": craving_data
                    }
                else:
                    return {
                        "complete": False,
                        "follow_up_question": "I didn't catch that. What food are you craving? (e.g., chocolate, pizza, chips)",
                        "missing_field": "food",
                        "partial_data": craving_data
                    }
        
        # Fallback so won't crash 
        return self._build_complete_response(craving_data, glucose_level, pregnancy_week)
    
    
    def _parse_meal_type_answer(self, message: str) -> Optional[str]:
        """Parse meal type from user's follow-up answer."""
        message_lower = message.lower().strip()
        
        # Direct matches
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
        
        # Check for "meal" - use time of day
        if "meal" in message_lower:
            time = get_time_of_day_from_time()
            if time == "morning":
                return "breakfast"
            elif time == "afternoon":
                return "lunch"
            else:
                return "dinner"
        
        return None
    
    
    def _build_complete_response(self, craving_data: dict, glucose_level: int, pregnancy_week: int) -> Dict[str, Any]:
        """Build the complete JSON response."""
        
        # If no meal_type, default to snack
        meal_type = (craving_data.get("meal_type") or "snack").lower().strip()

        # Prefer time_of_day implied by meal_type when relevant
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
                "intensity": craving_data.get("intensity", "medium")
            },
            "glucose_level": glucose_level,
            "pregnancy_week": pregnancy_week
        }
        
        return {
            "complete": True,
            "data": json_for_model
        }
    
    
    def clear_pending(self, user_id: str = "default"):
        """Clear any pending extraction for a user."""
        if user_id in self.pending_extractions:
            del self.pending_extractions[user_id]
    
    
    def translate_response(
        self, 
        model_response: Dict[str, Any],
        original_message: str = ""
    ) -> str:
        """
        Convert model's JSON recommendation to human natural language.
        """
        recommendation = model_response.get("recommendation", "a healthier alternative")
        explanation = model_response.get("explanation", "")
        
        response = f"Based on your levels, here's a great choice: {recommendation}"
        
        if explanation:
            response += f" — {explanation}"
        
        response += " 💜"
        
        return response


## MODULE INSTANCE ##
engine = AIEngine()
