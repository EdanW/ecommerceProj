from .preprocessing_utils import encode_trend, encode_intensity, encode_time_of_day

def create_features(user_json, candidate_food):
    """
    Merges the user's current health state with a single food item into
    the 9-feature vector the model expects.

    The model was trained on this exact set of features in this exact order,
    so both sides need to be present and correctly named.
    """
    craving = user_json.get('craving', {})

    features = {
        # user's current metabolic state
        "glucose_level":  user_json.get('glucose_level', 90),   # current reading in mg/dL
        "glucose_avg":    user_json.get('glucose_avg', 90),      # rolling average (A1C proxy)
        "glucose_trend":  encode_trend(user_json.get('glucose_trend', 'stable')),  # -1/0/1
        "pregnancy_week": user_json.get('pregnancy_week', 20),
        "intensity":      encode_intensity(craving.get('intensity', 'medium')),    # 0/1/2
        "time_of_day":    encode_time_of_day(craving.get('time_of_day', 'evening')),  # 0-3

        # food nutrition values from our database
        "food_gi":        candidate_food.get('glycemic_index', 50),  # how fast it spikes glucose
        "food_carbs":     candidate_food.get('carbs', 10),
        "food_sugar":     candidate_food.get('sugar', 2),
    }

    return features
