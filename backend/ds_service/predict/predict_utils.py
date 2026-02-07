import json
import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from backend.ds_service.preprocessing.preprocessing import create_features

def filter_by_constraints(foods_df, user_input):
    """
    Stage 1: Hard Constraints.
    Remove foods strictly forbidden by user prompt.
    """
    print("entered filter_by_constraints")

    # 1. Start with all foods
    valid_foods = foods_df.copy()

    # 2. User Exclusions (Foods)
    excluded_foods = [f.lower() for f in user_input['craving'].get('excluded_foods', [])]
    if excluded_foods:
        valid_foods = valid_foods[~valid_foods['name'].str.lower().isin(excluded_foods)]

    # 3. User Exclusions (Categories)
    excluded_cats = [c.lower() for c in user_input['craving'].get('excluded_categories', [])]
    if excluded_cats:
        # Since 'categories' is a list (['sweet', 'snack']), we check for intersection
        valid_foods = valid_foods[valid_foods['categories'].apply(
            lambda cats: not any(c.lower() in excluded_cats for c in cats)
        )]

    return valid_foods


def calculate_score(food_row, user_input):
    """
    Stage 2: Scoring Logic (The "Brain").
    TODO In the future, this function will be replaced by: model.predict(features)
    """
    print("entered calculate_score")
    score = 0
    reason_components = []
    
    # Unpack user context
    glucose = user_input.get('glucose_level', 90)
    craving_foods = [f.lower() for f in user_input['craving'].get('foods', [])]
    craving_categories = [c.lower() for c in user_input['craving'].get('categories', [])]
    intensity = user_input['craving'].get('intensity', 5) # 1-10 scale
    # get more attributes
    
    return {score, reason_components}


def get_best_matches(user_json, candidates_df):
    """
    Orchestrates the scoring and ranking.
    Returns: The TOP 3 best matches.
    """
    # A. Feature Engineering
    feature_rows = []
    for _, food_item in candidates_df.iterrows():
        food_dict = food_item.to_dict()
        vector = create_features(user_json, food_dict)
        feature_rows.append(vector)
    
    X = pd.DataFrame(feature_rows)

    # B. Model Prediction (The Brain)
    # TODO: Load real model. For now, everyone gets 0.8
    scores = [0.8] * len(X)
    
    # C. Assign Scores
    candidates_df = candidates_df.copy()
    candidates_df['score'] = scores
    
    # D. Rank & Slice (Top 3 Only)
    best_matches = candidates_df.sort_values(by='score', ascending=False).head(2)
    
    return best_matches