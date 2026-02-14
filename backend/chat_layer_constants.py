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

# =============================================================================
## UNSURE / UNDECIDED SIGNALS ##
# =============================================================================

# =============================================================================
## FOOD-RELATED CONTEXT SIGNALS ##
# =============================================================================

FOOD_CONTEXT_KEYWORDS = {
    "food",
    "eat",
    "eating",
    "hungry",
    "starving",
    "craving",
    "crave",
    "appetite",
    "meal",
    "cook",
    "cooking",
    "recipe",
    "taste",
    "delicious",
    "yummy",
    "snack",
    "breakfast",
    "lunch",
    "dinner",
    "brunch",
    "supper",
    "dessert",
    "drink",
    "thirsty",
    "calories",
    "nutrition",
    "diet",
    "sugar",
    "carbs",
    "protein",
    "fiber",
    "bake",
    "baking",
    "fry",
    "grill",
    "roast",
    "order",
    "takeout",
    "delivery",
    "restaurant",
    "bite",
    "nibble",
    "munch",
    "treat",
    "flavor",
    "flavour",
    "savory",
    "sweet",
    "salty",
    "sour",
    "spicy",
    "crunchy",
    "creamy",
}

# =============================================================================
## UNSURE / UNDECIDED SIGNALS ##
# =============================================================================

UNSURE_PHRASES = [
    "i don't know",
    "i dont know",
    "i do not know",
    "idk",
    "not sure",
    "no idea",
    "don't know",
    "dont know",
    "do not know",
    "no clue",
    "anything",
    "whatever",
    "surprise me",
    "you choose",
    "you decide",
    "dealer's choice",
    "dealers choice",
    "help me decide",
    "can't decide",
    "cant decide",
    "undecided",
    "no preference",
    "anything is fine",
    "whatever is fine",
    "i'm not sure",
    "im not sure",
]
