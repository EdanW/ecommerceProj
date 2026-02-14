from .preprocessing_utils import encode_trend, encode_intensity, encode_time_of_day

def create_features(user_json, candidate_food):
    """
    Merges User JSON + Single Food Item into a Feature Dictionary.
    This is then sent into the model for assessment.
    """
    craving = user_json.get('craving', {})
    
    # 1. User Context Features
    # These capture the user's current metabolic state
    features = {
        # --- User State ---
        "glucose_level":  user_json.get('glucose_level', 90),
        "glucose_avg":    user_json.get('glucose_avg', 90),
        "glucose_trend":  encode_trend(user_json.get('glucose_trend', 'stable')),
        "pregnancy_week": user_json.get('pregnancy_week', 20),
        "intensity":      encode_intensity(craving.get('intensity', 'medium')),
        "time_of_day":    encode_time_of_day(craving.get('time_of_day', 'evening')),

        # --- Food Nutrition ---
        "food_gi":        candidate_food.get('glycemic_index', 50),
        "food_carbs":     candidate_food.get('carbs', 10),
        "food_sugar":     candidate_food.get('sugar', 2),
    }
        
    return features