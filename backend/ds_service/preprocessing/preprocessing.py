from backend.ds_service.preprocessing.preprocessing_utils import (
    encode_trend,
    encode_intensity,
    encode_time_of_day,
)


def create_features(user_json, candidate_food):
    """
    Merges User JSON + Single Food Item into a Feature Dictionary.
    This is then sent into the model for assessment.
    """
    craving = user_json.get('craving', {})
    
    # 1. User Context Features
    features = {
        "glucose_level": user_json.get('glucose_level', 90),
        "glucose_avg": user_json.get('glucose_avg', 90),
        "glucose_trend": encode_trend(user_json.get('glucose_trend', 'stable')),
        "pregnancy_week": user_json.get('pregnancy_week', 20),
        "intensity": encode_intensity(craving.get('intensity', 'medium')),
        "time_of_day": encode_time_of_day(craving.get('time_of_day', 'evening')),
    }

    # 2. Food Attributes (From the DB row)
    # Ensure these keys match your DB exactly
    features["food_gi"] = candidate_food.get('glycemic_index', 50)
    features["food_carbs"] = candidate_food.get('carbs', 10)
    
    # 3. Interaction Features (The "Smart" Matching)
    
    # A. Name Match (Did they ask for this specific food?)
    requested_foods = [f.lower() for f in craving.get('foods', [])]
    food_name = candidate_food['name'].lower()
    
    # Check if any requested food string is inside the candidate name
    # e.g. request "apple" matches candidate "green apple"
    is_food_match = 1 if any(req in food_name for req in requested_foods) else 0
    features["matches_request"] = is_food_match

    # B. Category Match (Did they ask for this category?)
    requested_cats = [c.lower() for c in craving.get('categories', [])]
    
    # Handle if DB categories are a list or string
    db_cats = candidate_food.get('categories', [])
    if isinstance(db_cats, str):
        db_cats = [db_cats] # Convert string to list if needed
    
    current_food_cats = [c.lower() for c in db_cats]
    
    # Check for overlap
    is_cat_match = 1 if not set(requested_cats).isdisjoint(current_food_cats) else 0
    features["matches_category"] = is_cat_match

    return features