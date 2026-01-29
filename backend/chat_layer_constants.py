"""
Constants and configuration for the chat layer.
"""

from zoneinfo import ZoneInfo

# =============================================================================
## CONFIGURATION ##
# =============================================================================

TIMEZONE = ZoneInfo("Asia/Jerusalem")
PENDING_TTL_SECONDS = 600

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
