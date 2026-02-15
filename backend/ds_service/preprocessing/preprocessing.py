from .preprocessing_utils import encode_trend, encode_intensity, encode_time_of_day

def create_features(user_json, candidate_food):
    """
    Build a feature dictionary from user context and a single candidate food.

    Combines metabolic state (glucose, pregnancy week), craving metadata
    (intensity, time of day), food nutrition, and request-matching signals
    into a flat dict consumed by the scoring pipeline.
    """
    craving = user_json.get('craving', {})

    features = {
        # User metabolic state
        "glucose_level":  user_json.get('glucose_level', 90),
        "glucose_avg":    user_json.get('glucose_avg', 90),
        "glucose_trend":  encode_trend(user_json.get('glucose_trend', 'stable')),
        "pregnancy_week": user_json.get('pregnancy_week', 20),
        "intensity":      encode_intensity(craving.get('intensity', 'medium')),
        "time_of_day":    encode_time_of_day(craving.get('time_of_day', 'evening')),

        # Food nutritional profile
        "food_gi":        candidate_food.get('glycemic_index', 50),
        "food_carbs":     candidate_food.get('carbs', 10),
        "food_sugar":     candidate_food.get('sugar', 2),

        # Request-matching signals
        "matches_request": 1 if candidate_food.get('name', '').lower() in
            [f.lower() for f in craving.get('foods', [])] else 0,
        "matches_category": len(
            set(c.lower() for c in candidate_food.get('categories', [])) &
            set(c.lower() for c in craving.get('categories', []))
        ),
    }

    return features