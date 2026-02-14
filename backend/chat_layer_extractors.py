"""
Extraction functions for the chat layer.
"""

from typing import List, Tuple, Optional, Set
import spacy.tokens

from .chat_layer_food_database import FOOD_DATABASE
from .chat_layer_nlp import (
    nlp,
    food_matcher,
    category_matcher,
    meal_type_matcher,
    intensity_matcher,
)
from .chat_layer_negation import (
    find_negated_tokens,
    check_exclusion_phrases,
)


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


def _filter_overlapping_matches(matches: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
    """
    Remove shorter matches contained within longer ones,
    e.g. keep "chocolate milkshake" instead of "chocolate" + "milkshake".
    """
    if not matches:
        return []
    
    # Sort by start position, then by length (longer first)
    sorted_matches = sorted(matches, key=lambda x: (x[1], -(x[2] - x[1])))
    
    filtered = []
    for match in sorted_matches:
        _, start, end = match
        
        is_overlapping = False
        for kept_match in filtered:
            _, kept_start, kept_end = kept_match

            if start < kept_end and end > kept_start:
                is_overlapping = True
                break
        
        if not is_overlapping:
            filtered.append(match)
    
    return filtered


def extract_foods_with_negation_spacy(
    doc: spacy.tokens.Doc, text: str
) -> Tuple[List[str], List[str]]:
    """
    Extract foods and classify them as wanted vs excluded.

    Foods are matched via PhraseMatcher against FOOD_DATABASE keys. Exclusion is
    determined by negation scope (dependency-based) and exclusion-phrase spans.
    
    Longer matches take priority over shorter overlapping matches
    """
    wanted_foods: List[str] = []
    excluded_foods: List[str] = []

    negated_indices = find_negated_tokens(doc)
    exclusion_spans = check_exclusion_phrases(text)
    
    # Get all matches and filter to keep only longest non-overlapping ones
    all_matches = food_matcher(doc)
    matches = _filter_overlapping_matches(list(all_matches))

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


def parse_meal_type_answer(doc: spacy.tokens.Doc, message: str) -> Optional[str]:
    """Parse meal type from a short follow-up reply using matcher first, then synonyms."""
    from .chat_layer_time_utils import get_time_of_day_from_time

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