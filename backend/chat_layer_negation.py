"""
Negation detection logic for the chat layer.
"""

from typing import List, Tuple, Set
import spacy.tokens

from .chat_layer_constants import (
    NEGATION_TOKENS,
    NEGATION_LEMMAS,
    EXCLUSION_PHRASES,
)


SCOPE_BREAKERS = {",", ".", "!", "?", ";"}
POSITIVE_SIGNALS = {"maybe", "perhaps", "possibly", "how about", "or"}


def find_negated_tokens(doc: spacy.tokens.Doc) -> Set[int]:
    """
    Return token indices considered negated.

    Uses dependency parsing (neg relation) when available, with fallbacks for:
    - standalone negation tokens (e.g., "no", "without")
    - negation-implying verbs (e.g., "avoid", "hate") applied to their objects

    Negation scope stops at punctuation (commas, periods, etc.).
    Positive signals (maybe, perhaps) override negation for following tokens.
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
                    if doc[i].text in SCOPE_BREAKERS:
                        break
                    negated_indices.add(i)

        if token.lemma_.lower() in NEGATION_LEMMAS:
            for child in token.children:
                if child.dep_ in ("dobj", "pobj", "attr", "oprd"):
                    negated_indices.add(child.i)
                    for descendant in child.subtree:
                        negated_indices.add(descendant.i)

    # Positive signals override negation
    for token in doc:
        if token.lower_ in POSITIVE_SIGNALS:
            for i in range(token.i, min(token.i + 4, len(doc))):
                negated_indices.discard(i)

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
