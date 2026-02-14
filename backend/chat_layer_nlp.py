"""
SpaCy NLP initialization and matchers for the chat layer.
"""

import logging
import sys
import spacy
from spacy.matcher import PhraseMatcher

from .chat_layer_food_database import (
    FOOD_DATABASE,
    CATEGORY_KEYWORDS,
    MEAL_TYPE_KEYWORDS,
    INTENSITY_KEYWORDS,
)

logger = logging.getLogger(__name__)

# =============================================================================
## SPACY INITIALIZATION ##
# =============================================================================

try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("SpaCy model loaded: en_core_web_sm")
except OSError:
    logger.warning("SpaCy model not found. Downloading: en_core_web_sm")
    import subprocess

    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
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
