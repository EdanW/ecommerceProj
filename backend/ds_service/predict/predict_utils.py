import pandas as pd
from backend.ds_service.preprocessing.preprocessing import create_features
import numpy as np
import joblib
import os

_MODEL = None
_MODEL_PATH = "backend/ds_service/models/food_safety_model.pkl"

def load_model():
    # Singleton loader: deserializes the model on first call and caches it for
    # subsequent requests, avoiding repeated disk I/O per inference call.
    global _MODEL
    if _MODEL is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {_MODEL_PATH}. Train it first!")
        _MODEL = joblib.load(_MODEL_PATH)
    return _MODEL


def filter_by_constraints(foods_df, user_input):
    # Progressively narrows the full food pool by applying constraint filters
    # in order: condiment removal, explicit exclusions, category exclusions,
    # category whitelist, and meal-type matching.
    valid_foods = foods_df.copy()

    # remove condiments (butter, ketchup, mayo, ranch, soy sauce…)
    requested_foods = [f.lower() for f in user_input['craving'].get('foods', [])]
    valid_foods = valid_foods[valid_foods['categories'].apply(
        lambda cats: isinstance(cats, list) and "condiment" not in [c.lower() for c in cats]
    ) | valid_foods['name'].str.lower().isin(requested_foods)]

    # remove anything the user explicitly said they don't want
    excluded_foods = [f.lower() for f in user_input['craving'].get('excluded_foods', [])]
    if excluded_foods:
        valid_foods = valid_foods[~valid_foods['name'].str.lower().isin(excluded_foods)]

    # expand exclusions to the type-family of each excluded food.
    # e.g. "chicken wings" has type category "wings" → also exclude "wings",
    # "buffalo wings", "hot wings" so the user doesn't get a variant they
    # clearly didn't want. only non-generic type tags are used for this.
    _GENERIC_CATS = {"savory", "sweet", "hot", "cold", "spicy", "crunchy",
                     "creamy", "salty", "sour", "dessert", "protein", "meat",
                     "seafood", "dairy", "drink", "vegetable", "fruit", "bread",
                     "grain", "soup", "salad", "pasta", "italian"}
    excluded_cats = [c.lower() for c in user_input['craving'].get('excluded_categories', [])]
    if excluded_foods:
        for food_name in excluded_foods:
            rows = foods_df[foods_df['name'].str.lower() == food_name]
            for _, row in rows.iterrows():
                if isinstance(row.get('categories'), list):
                    type_cats = [c.lower() for c in row['categories']
                                 if c.lower() not in _GENERIC_CATS]
                    excluded_cats = list(set(excluded_cats + type_cats))

    # remove entire categories the user excluded (including auto-expanded ones above)
    if excluded_cats:
        valid_foods = valid_foods[valid_foods['categories'].apply(
            lambda cats: not any(c.lower() in excluded_cats for c in cats)
        )]

    # whitelist filter — only keep foods that match at least one requested category.
    _CATEGORY_ALIASES = {
        "salty":  ["salty", "savory"],
        "savory": ["savory", "salty"],
    }
    target_cats = [c.lower() for c in user_input['craving'].get('categories', [])]
    if target_cats:
        expanded_cats = set()
        for cat in target_cats:
            expanded_cats.update(_CATEGORY_ALIASES.get(cat, [cat]))
        valid_foods = valid_foods[valid_foods['categories'].apply(
            lambda food_cats: not set(c.lower() for c in food_cats).isdisjoint(expanded_cats)
        )]

    # Meal-type filter. Foods explicitly requested by the user are re-included
    # even when their tagged meal_type does not match the requested meal, allowing
    # the model to score and surface them rather than silently dropping them.
    target_meal = user_input['craving'].get('meal_type')

    if target_meal:
        target_meal = target_meal.lower()
        if 'meal_type' in valid_foods.columns:
            meal_match = valid_foods['meal_type'].str.lower() == target_meal
            meal_filtered = valid_foods[meal_match]
            if requested_foods:
                requested_but_dropped = valid_foods[
                    valid_foods['name'].str.lower().isin(requested_foods) & ~meal_match
                ]
                valid_foods = pd.concat([meal_filtered, requested_but_dropped]).drop_duplicates(subset=['name'])
            else:
                valid_foods = meal_filtered
        else:
            print('warning: meal type missing, skipping this filter')
    return valid_foods


def generate_reason(features):
    """
    Produces a single user-facing sentence explaining the primary reason the top
    food was selected. Prioritises glucose context (trend, current level), then
    time-of-day suitability, then food nutritional properties (GI, sugar).
    Returns a generic fallback if no specific condition is met.
    """
    reasons = []

    if features.get('glucose_trend', 0) == -1:
        reasons.append("is safe while your levels are trending down")
    elif features.get('glucose_level', 100) < 90:
        reasons.append("helps maintain your current stable levels")

    if features.get('time_of_day') == 1:  # morning
        reasons.append("fits your high morning insulin sensitivity")
    elif features.get('time_of_day') == 4 and features.get('food_carbs', 0) < 30:  # night
        reasons.append("is light enough for late-night digestion")

    if features.get('food_gi', 50) < 55:
        reasons.append("has a low Glycemic Index to prevent spikes")
    if features.get('food_sugar', 0) < 5:
        reasons.append("has minimal sugar")

    if not reasons:
        return "This fits within your calculated safety limits."

    return f"This option {reasons[0]}."


def get_best_matches(user_json, candidates_df):
    """
    Scores each food in candidates_df using the XGBoost safety classifier and
    returns the top 2 results sorted by safety score descending.

    Each food is converted to a 9-feature vector (user context + food nutrition)
    and passed through model.predict_proba(). The resulting class-1 probability
    represents the model's confidence that the food is safe for this user at this
    moment. A small uniform jitter is added before ranking to introduce variety
    among foods with similar scores.

    Returns: (top_2_dataframe, reason_string_for_winner)
    """
    model = load_model()

    # Build a 9-feature vector for each candidate by combining user state and food nutrition.
    feature_rows = []
    for _, food_item in candidates_df.iterrows():
        food_dict = food_item.to_dict()
        vector = create_features(user_json, food_dict)
        feature_rows.append(vector)

    X_full = pd.DataFrame(feature_rows)

    # Feature order must match the training schema exactly.
    model_cols = ['glucose_level', 'glucose_avg', 'glucose_trend', 'pregnancy_week',
                  'intensity', 'time_of_day', 'food_gi', 'food_carbs', 'food_sugar']

    X_model = X_full[model_cols]

    # predict_proba returns [prob_class_0, prob_class_1] — we want class 1 (safe)
    scores = model.predict_proba(X_model)[:, 1]

    candidates_df = candidates_df.copy()

    # Uniform jitter in [0, 0.08] breaks ties between foods with similar safety
    # scores, producing variety in recommendations without meaningfully affecting
    # the relative ordering of foods with substantially different scores.
    jitter = np.random.uniform(0, 0.08, size=len(scores))
    candidates_df['safety_score'] = scores + jitter

    best_matches = candidates_df.sort_values(by='safety_score', ascending=False).head(2)

    top_reason = "No recommendation found."
    if not best_matches.empty:
        top_index = best_matches.index[0]
        top_features = feature_rows[candidates_df.index.get_loc(top_index)]
        top_reason = generate_reason(top_features)

    return best_matches, top_reason
