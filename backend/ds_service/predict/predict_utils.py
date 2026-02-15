import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from backend.ds_service.preprocessing.preprocessing import create_features


def _compute_risk_score(features):
    """
    Compute a glucose-risk score for a food given user context.
    Uses the same oracle logic as generate_synthetic_data.py.
    """
    food_carbs = features.get('food_carbs', 10)
    food_sugar = features.get('food_sugar', 2)
    food_gi = features.get('food_gi', 50)
    glucose_level = features.get('glucose_level', 90)
    glucose_avg = features.get('glucose_avg', 90)
    glucose_trend = features.get('glucose_trend', 0)
    time_of_day = features.get('time_of_day', 0)
    pregnancy_week = features.get('pregnancy_week', 20)
    intensity = features.get('intensity', 1)

    # 1. Base Impact (Carbs & Sugar)
    risk_score = (food_carbs * 1.0) + (food_sugar * 1.5)

    # 2. GI Multiplier
    gi_factor = food_gi / 50.0
    risk_score *= gi_factor

    # 3. User Context Multipliers
    if glucose_level > 160:
        risk_score *= 1.5
    elif glucose_level > 130:
        risk_score *= 1.2

    if glucose_trend == 1:  # Rising
        risk_score += (food_sugar * 2.0)

    if time_of_day == 4:  # Night
        risk_score *= 1.4

    if pregnancy_week > 24:
        risk_score *= 1.25

    if glucose_avg > 120:
        risk_score *= 1.2

    if intensity == 3:  # High
        risk_score *= 1.1

    return risk_score


# Meal type compatibility groups
_MEAL_COMPAT = {
    "breakfast": {"breakfast", "snack"},
    "lunch": {"lunch", "dinner", "snack"},
    "dinner": {"dinner", "lunch", "snack"},
    "snack": {"snack", "breakfast", "lunch", "dinner", "dessert"},
    "dessert": {"dessert", "snack"},
}


def filter_by_constraints(foods_df, user_input):
    """
    Apply hard constraints to eliminate ineligible foods before scoring.

    Filters applied (in order):
        1. User-excluded foods
        2. User-excluded categories
        3. Category whitelist (keep only matching categories)
        4. Non-recommendable items (condiments, drinks)
        5. Meal-type compatibility
    """
    valid_foods = foods_df.copy()
    craving = user_input.get('craving', {})

    # 1. Remove explicitly excluded foods
    excluded_foods = [f.lower() for f in craving.get('excluded_foods', [])]
    if excluded_foods:
        valid_foods = valid_foods[~valid_foods['name'].str.lower().isin(excluded_foods)]

    # 2. Remove foods belonging to excluded categories
    excluded_cats = [c.lower() for c in craving.get('excluded_categories', [])]
    if excluded_cats:
        valid_foods = valid_foods[valid_foods['categories'].apply(
            lambda cats: not any(c.lower() in excluded_cats for c in cats)
        )]

    # 3. If the user specified desired categories, keep only foods that match at least one
    target_cats = [c.lower() for c in craving.get('categories', [])]
    if target_cats:
        valid_foods = valid_foods[valid_foods['categories'].apply(
            lambda food_cats: not set(c.lower() for c in food_cats).isdisjoint(target_cats)
        )]

    # 4. Exclude non-recommendable items (condiments, drinks) unless explicitly requested
    requested_foods = [f.lower() for f in craving.get('foods', [])]
    for tag in ('condiment', 'drink'):
        user_asked_for_tagged = any(
            f in FOOD_DB and tag in FOOD_DB[f].get('categories', [])
            for f in requested_foods
        )
        if not user_asked_for_tagged:
            valid_foods = valid_foods[valid_foods['categories'].apply(
                lambda cats, t=tag: t not in [c.lower() for c in cats]
            )]

    # 5. Keep only foods compatible with the requested meal type
    requested_meal = (craving.get('meal_type') or '').lower()
    if requested_meal and requested_meal in _MEAL_COMPAT:
        compatible_meals = _MEAL_COMPAT[requested_meal]
        valid_foods = valid_foods[valid_foods['meal_type'].str.lower().isin(compatible_meals)]

    return valid_foods


def _compute_relevance_score(food_name, food_cats, food_meal,
                              requested_foods, requested_cats, requested_meal,
                              compatible_meals):
    """
    Score how well a food matches the user's intent (0.0–1.0).

    Exact-name matching is handled separately in ``get_best_matches``
    to keep it outside the safety/relevance blend.
    """
    score = 0.0

    # Category overlap
    if requested_cats:
        overlap = len(food_cats & requested_cats)
        total = len(requested_cats)
        score += 0.60 * (overlap / max(total, 1))

        # Penalise missing requested categories
        missing = len(requested_cats - food_cats)
        score -= 0.30 * (missing / total)

    # Meal-type alignment
    if food_meal == requested_meal:
        score += 0.20
    elif food_meal in compatible_meals:
        score += 0.0
    else:
        score -= 0.10

    return max(0.0, min(score, 1.0))


def get_best_matches(user_json, candidates_df):
    """
    Score, rank, and return the top 2 food candidates.

    Final score = 0.30 * safety + 0.70 * relevance, with an additive
    exact-match boost applied outside the blend for user-requested foods.
    """
    craving = user_json.get('craving', {})
    requested_foods = [f.lower() for f in craving.get('foods', [])]
    requested_cats = set(c.lower() for c in craving.get('categories', []))
    requested_meal = (craving.get('meal_type') or 'snack').lower()
    compatible_meals = _MEAL_COMPAT.get(requested_meal, {requested_meal, 'snack'})

    # Build feature vectors for every candidate
    feature_rows = []
    for _, food_item in candidates_df.iterrows():
        feature_rows.append(create_features(user_json, food_item.to_dict()))

    # Score each candidate
    scores = []
    for idx, (_, food_item) in enumerate(candidates_df.iterrows()):
        features = feature_rows[idx]
        food_name = food_item['name'].lower()
        food_cats = set(c.lower() for c in food_item.get('categories', []))
        food_meal = (food_item.get('meal_type') or 'snack').lower()

        # Safety component (0–1): inverse of glucose risk, normalised to 200
        risk = _compute_risk_score(features)
        safety = max(0.0, 1.0 - risk / 200.0)

        # Relevance component (0–1): category & meal-type alignment
        relevance = _compute_relevance_score(
            food_name, food_cats, food_meal,
            requested_foods, requested_cats, requested_meal,
            compatible_meals
        )

        final_score = (0.3 * safety) + (0.7 * relevance)

        # Exact-match boost (outside the blend so safety alone cannot veto
        # a food the user explicitly asked for)
        if food_name in requested_foods:
            final_score += 0.30 if safety > 0.15 else 0.05

        scores.append(final_score)

    candidates_df = candidates_df.copy()
    candidates_df['score'] = scores

    return candidates_df.sort_values(by='score', ascending=False).head(2)
