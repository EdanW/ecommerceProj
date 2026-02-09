import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from .predict_utils import filter_by_constraints, get_best_matches


def predict(json_input):
    """
    The main entry point. 
    Input: JSON string or dict
    Output: JSON with recommendation and reason.
    Output format:
    {
        food: string,
        reason: string,
        another_option: string,
    }
    """
    print("entered predict")
    # 1. Load and Transform Data (since its a dict of dicts)
    food_list = []
    for name, stats in FOOD_DB.items():
        # Create a copy so we don't mess up the original DB
        item = stats.copy()
        # IMPORTANT: Inject the key ('chocolate') as the 'name' attribute
        item['name'] = name 
        food_list.append(item)
    food_df = pd.DataFrame(food_list)

    #2. discard irrelevant foods
    valid_candidates = filter_by_constraints(food_df, json_input)
    
    best_matches = get_best_matches(json_input, valid_candidates)

    # Guard
    top_pick = best_matches.iloc[0]['name'] if not best_matches.empty else None
    runner_up = best_matches.iloc[1]['name'] if len(best_matches) > 1 else None

    return {
        "food": top_pick,
        "reason": 'TODO',
        "another_option": runner_up
    }