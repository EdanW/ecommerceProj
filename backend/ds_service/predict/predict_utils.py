import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from backend.ds_service.preprocessing.preprocessing import create_features
import numpy as np
import joblib
import os

_MODEL = None
_MODEL_PATH = "backend/ds_service/models/food_safety_model.pkl"
def load_model():
    """Singleton pattern to load model only once."""
    global _MODEL
    if _MODEL is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {_MODEL_PATH}. Train it first!")
        print(f"🧠 Loading XGBoost Model from {_MODEL_PATH}...")
        _MODEL = joblib.load(_MODEL_PATH)
    return _MODEL


def filter_by_constraints(foods_df, user_input):
    print("entered filter_by_constraints")

    # 1. Start with all foods
    valid_foods = foods_df.copy()
    # 2. User Requested Exclusions (Foods)
    excluded_foods = [f.lower() for f in user_input['craving'].get('excluded_foods', [])]
    if excluded_foods:
        valid_foods = valid_foods[~valid_foods['name'].str.lower().isin(excluded_foods)]

    # 3. User Requested Exclusions (Categories)
    excluded_cats = [c.lower() for c in user_input['craving'].get('excluded_categories', [])]
    if excluded_cats:
        # Since 'categories' is a list (['sweet', 'snack']), we check for intersection
        valid_foods = valid_foods[valid_foods['categories'].apply(
            lambda cats: not any(c.lower() in excluded_cats for c in cats)
        )]
    
    # 4. Whitelist - include only desired categories
    target_cats = [c.lower() for c in user_input['craving'].get('categories', [])]
    if target_cats:
        # Logic: Keep food IF it shares AT LEAST ONE category with the request
        valid_foods = valid_foods[valid_foods['categories'].apply(
            lambda food_cats: not set(c.lower() for c in food_cats).isdisjoint(target_cats)
        )]

    # 5. Filter for same meal type
    target_meal = user_input['craving'].get('meal_type')
    
    if target_meal:
        target_meal = target_meal.lower()
        if 'meal_type' in valid_foods.columns:
            valid_foods = valid_foods[valid_foods['meal_type'].str.lower() == target_meal]        
        else:
            print ('warning: meal type missing, skipping this filter')
    print(f'filtered down to {len(valid_foods)} valid foods')
    return valid_foods


def generate_reason(features):
    """
    Explains WHY the top choice is safe/good.
    features: dict or Series of the top food's data.
    """
    reasons = []
    
    # 1. Biological Context
    if features.get('glucose_trend', 0) == -1:
        reasons.append("is safe while your levels are trending down")
    elif features.get('glucose_level', 100) < 90:
        reasons.append("helps maintain your current stable levels")
        
    if features.get('time_of_day') == 0: # Morning
        reasons.append("fits your high morning insulin sensitivity")
    elif features.get('time_of_day') == 3 and features.get('food_carbs', 0) < 30:
        reasons.append("is light enough for late-night digestion")

    # 2. Food Properties
    if features.get('food_gi', 50) < 55:
        reasons.append("has a low Glycemic Index to prevent spikes")
    if features.get('food_sugar', 0) < 5:
        reasons.append("has minimal sugar")

    # 3. Construct Sentence
    if not reasons:
        return "This fits within your calculated safety limits."
    
    return f"This option {reasons[0]}."


def get_best_matches(user_json, candidates_df):
    """
    Orchestrates the scoring and ranking.
    Returns: 
        Tuple (Dataframe of top 2 matches, string reason for the first one)
    """
    model = load_model()
    # A. Feature Engineering
    feature_rows = []
    for _, food_item in candidates_df.iterrows():
        food_dict = food_item.to_dict()
        vector = create_features(user_json, food_dict)
        feature_rows.append(vector)
    
    X_full = pd.DataFrame(feature_rows)

    # B. Model Prediction (The Brain)
    model_cols = ['glucose_level', 'glucose_avg', 'glucose_trend', 'pregnancy_week', 
                  'intensity', 'time_of_day', 'food_gi', 'food_carbs', 'food_sugar']

    # Ensure X only has the columns the model expects
    X_model = X_full[model_cols]    

    # C. Model Prediction
    scores = model.predict_proba(X_model)[:, 1]

    # D. Assign Scores
    candidates_df = candidates_df.copy()
    candidates_df['safety_score'] = scores
    
    # E. Rank & Slice (Top 2 Only)
    best_matches = candidates_df.sort_values(by='safety_score', ascending=False).head(2)
    
    # F. Generate Reason for the Winner
    top_reason = "No recommendation found."
    if not best_matches.empty:
        # Get the feature vector for the top match to explain it
        top_index = best_matches.index[0]
        # We need the features we created in step A corresponding to this index
        # (Assuming the index was preserved from candidates_df)
        top_features = feature_rows[candidates_df.index.get_loc(top_index)]
        
        top_reason = generate_reason(top_features)

    return best_matches, top_reason