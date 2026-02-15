import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from .predict_utils import filter_by_constraints, get_best_matches


def predict(json_input):
    """
    Generate a food recommendation from a structured craving payload.

    Returns ``{"food": str, "reason": str, "another_option": str | None}``.
    """
    # Build a flat DataFrame from the food database
    food_list = []
    for name, stats in FOOD_DB.items():
        item = stats.copy()
        item['name'] = name
        food_list.append(item)
    food_df = pd.DataFrame(food_list)

    # Stage 1 — eliminate ineligible foods
    valid_candidates = filter_by_constraints(food_df, json_input)

    # Stage 2 — score and rank remaining candidates
    best_matches = get_best_matches(json_input, valid_candidates)

    # Multi-food combo handling (e.g. "pasta and salad")
    requested_foods = [f.lower() for f in json_input.get('craving', {}).get('foods', [])]
    if len(requested_foods) > 1:
        all_requested_in_db = all(f in FOOD_DB for f in requested_foods)
        if all_requested_in_db:
            combo_name = " and ".join(requested_foods)
            non_requested = valid_candidates[
                ~valid_candidates['name'].str.lower().isin(requested_foods)
            ]
            if not non_requested.empty:
                runner_up_matches = get_best_matches(json_input, non_requested)
                runner_up = runner_up_matches.iloc[0]['name'] if not runner_up_matches.empty else None
            else:
                runner_up = None
            return {
                "food": combo_name,
                "reason": "TODO",
                "another_option": runner_up
            }

    top_pick = best_matches.iloc[0]['name'] if not best_matches.empty else None
    runner_up = best_matches.iloc[1]['name'] if len(best_matches) > 1 else None

    return {
        "food": top_pick,
        "reason": "TODO",
        "another_option": runner_up
    }