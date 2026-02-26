import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from backend.ds_service.preprocessing.preprocessing import create_features
import numpy as np
import joblib
import os

_MODEL = None
_MODEL_PATH = "backend/ds_service/models/food_safety_model.pkl"

def load_model():
    # lazy load — only reads the .pkl file the first time, then keeps it in memory.
    # avoids reloading the model on every single request which would be very slow.
    global _MODEL
    if _MODEL is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {_MODEL_PATH}. Train it first!")
        print(f"🧠 Loading XGBoost Model from {_MODEL_PATH}...")
        _MODEL = joblib.load(_MODEL_PATH)
    return _MODEL


def filter_by_constraints(foods_df, user_input):
    # takes the full food database and progressively narrows it down based on
    # what the user said. each step removes more foods from the pool.
    print("entered filter_by_constraints")

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

    # meal type filter (breakfast / lunch / dinner / snack)
    # pasta is tagged as "dinner" in our DB, so if someone asks for lunch,
    # we'd normally remove it from the pool entirely and never consider it.
    # to fix that, we re-add any food the user explicitly named even if the
    # meal type doesn't match — the model will still score it and decide.
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
    print(f'filtered down to {len(valid_foods)} valid foods')
    return valid_foods


def generate_reason(features):
    """
    Builds a one-line explanation of why the top food was picked.
    Looks at glucose trend, time of day, GI, and sugar content
    and picks the most relevant thing to tell the user.
    """
    reasons = []

    # check glucose context first
    if features.get('glucose_trend', 0) == -1:
        reasons.append("is safe while your levels are trending down")
    elif features.get('glucose_level', 100) < 90:
        reasons.append("helps maintain your current stable levels")

    if features.get('time_of_day') == 0:  # morning
        reasons.append("fits your high morning insulin sensitivity")
    elif features.get('time_of_day') == 3 and features.get('food_carbs', 0) < 30:
        reasons.append("is light enough for late-night digestion")

    # food-specific properties
    if features.get('food_gi', 50) < 55:
        reasons.append("has a low Glycemic Index to prevent spikes")
    if features.get('food_sugar', 0) < 5:
        reasons.append("has minimal sugar")

    if not reasons:
        return "This fits within your calculated safety limits."

    return f"This option {reasons[0]}."


def get_best_matches(user_json, candidates_df):
    """
    Scores every food in candidates_df against the user's current glucose state
    using the XGBoost classifier, then returns the top 2 results.

    The model outputs a probability from 0 to 1 — how likely this food is "safe"
    for this user right now. We sort by that score and take the top 2.

    Returns: (top_2_dataframe, reason_string_for_winner)
    """
    model = load_model()

    # build a feature vector for each food by combining user state + food nutrition
    feature_rows = []
    for _, food_item in candidates_df.iterrows():
        food_dict = food_item.to_dict()
        vector = create_features(user_json, food_dict)
        feature_rows.append(vector)

    X_full = pd.DataFrame(feature_rows)

    # the model was trained with exactly these 9 features in this order
    model_cols = ['glucose_level', 'glucose_avg', 'glucose_trend', 'pregnancy_week',
                  'intensity', 'time_of_day', 'food_gi', 'food_carbs', 'food_sugar']

    X_model = X_full[model_cols]

    # predict_proba returns [prob_class_0, prob_class_1] — we want class 1 (safe)
    scores = model.predict_proba(X_model)[:, 1]

    candidates_df = candidates_df.copy()

    # add a small random jitter so foods with similar safety scores rotate
    # instead of always returning the same winner. jitter is capped at 0.08
    # (8%) so genuinely unsafe foods (scoring << safe ones) still won't surface.
    jitter = np.random.uniform(0, 0.08, size=len(scores))
    candidates_df['safety_score'] = scores + jitter

    best_matches = candidates_df.sort_values(by='safety_score', ascending=False).head(2)

    # generate a human-readable reason for why the top pick was chosen
    top_reason = "No recommendation found."
    if not best_matches.empty:
        top_index = best_matches.index[0]
        top_features = feature_rows[candidates_df.index.get_loc(top_index)]
        top_reason = generate_reason(top_features)

    return best_matches, top_reason
