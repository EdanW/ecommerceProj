import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from .predict_utils import filter_by_constraints, get_best_matches

# Minimum safety score for a user-requested food to be approved.
# If the requested food scores at or above this threshold, recommend it
# (even if a "safer" food exists). Only redirect if the food is genuinely risky.
_REQUESTED_FOOD_SAFETY_THRESHOLD = 0.40

# Generic taste/texture tags shared by almost every food — useless for
# deciding whether two foods are in the same family.
_GENERIC_CATEGORIES = {"savory", "sweet", "hot", "cold", "spicy", "crunchy",
                       "creamy", "salty", "sour"}


def _categories_of_requested(requested_foods, food_df):
    """Return ALL categories (including taste) for the requested foods."""
    rows = food_df[food_df['name'].str.lower().isin(requested_foods)]
    cats = set()
    for cat_list in rows['categories']:
        if isinstance(cat_list, list):
            cats.update(c.lower() for c in cat_list)
    return cats


def _family_categories_of_requested(requested_foods, food_df):
    """
    Return the best category set to use for same-family redirect matching.

    Strategy (two-tier):
      1. Prefer meaningful food-TYPE categories (strip generic taste tags).
         e.g. pasta → {pasta, grain, italian}  — keeps redirect within grain foods.
      2. If ONLY generic/taste categories exist (e.g. chocolate milkshake is
         purely sweet+cold+creamy), use those taste tags as the fallback.
         This stops a sweet craving from being redirected to avocado — it will
         stay in the sweet/cold/creamy space (fruit, yogurt, smoothie, etc.).
    """
    all_cats = _categories_of_requested(requested_foods, food_df)
    type_cats = all_cats - _GENERIC_CATEGORIES
    # If meaningful type categories exist, use those (more precise).
    # Otherwise fall back to all (taste) categories so the redirect stays
    # at least in the right flavour family.
    return type_cats if type_cats else all_cats


def _evaluate_single_food(food_name, valid_candidates, food_df, json_input):
    """
    Evaluate one requested food item independently.
    Returns (resolved_name, was_redirected, reason):
      - resolved_name : the food to recommend (may differ from food_name on redirect)
      - was_redirected: True if we swapped to a safer alternative
      - reason        : explanation string (or None if no result found)
    """
    food_candidates = valid_candidates[
        valid_candidates['name'].str.lower() == food_name.lower()
    ]
    if not food_candidates.empty:
        matches, reason = get_best_matches(json_input, food_candidates)
        if not matches.empty and matches.iloc[0]['safety_score'] >= _REQUESTED_FOOD_SAFETY_THRESHOLD:
            return (matches.iloc[0]['name'], False, reason)

    # Food is unsafe or not in candidates — redirect to same family
    req_categories = _family_categories_of_requested([food_name], food_df)
    if req_categories:
        same_family = valid_candidates[
            valid_candidates['categories'].apply(
                lambda cats: isinstance(cats, list) and
                not set(c.lower() for c in cats).isdisjoint(req_categories)
            )
        ]
        same_family = same_family[~same_family['name'].str.lower().isin([food_name.lower()])]
        if not same_family.empty:
            family_matches, family_reason = get_best_matches(json_input, same_family)
            if not family_matches.empty:
                return (family_matches.iloc[0]['name'], True, family_reason)

    return (None, True, None)


def predict(json_input):
    """
    The main entry point.
    Input: JSON string or dict
    Output: JSON with recommendation and reason.

    Strategy:
      1. Filter candidates by constraints (exclusions, categories, meal type).
      2. If the user asked for a specific food, score IT first.
         - If it clears the safety threshold → recommend it (user's wish respected).
         - If it's below the threshold → redirect, but stay in the same category
           family as what the user asked for (e.g. grain/pasta, not fish).
      3. If the user gave no specific food → recommend the overall best pick.
    """
    print("entered predict")

    # 1. Build food dataframe
    food_list = []
    for name, stats in FOOD_DB.items():
        item = stats.copy()
        item['name'] = name
        food_list.append(item)
    food_df = pd.DataFrame(food_list)

    # 2. Discard irrelevant foods
    valid_candidates = filter_by_constraints(food_df, json_input)
    if valid_candidates.empty:
        return {
            "food": None,
            "reason": "no foods in POC database that support this scenario",
            "another_option": None
        }

    requested_foods = [f.lower() for f in json_input.get('craving', {}).get('foods', [])]

    # 3a. Multi-food meal: evaluate each requested food independently
    if len(requested_foods) > 1:
        meal_assessment = {}
        primary_reason = None
        for food_name in requested_foods:
            resolved, redirected, reason = _evaluate_single_food(
                food_name, valid_candidates, food_df, json_input
            )
            meal_assessment[food_name] = {"resolved": resolved, "redirected": redirected}
            if primary_reason is None and reason:
                primary_reason = reason

        # Primary food = first resolved food in the list
        primary = next(
            (meal_assessment[f]["resolved"] for f in requested_foods if meal_assessment[f]["resolved"]),
            None
        )
        return {
            "food": primary,
            "reason": primary_reason or "This fits within your calculated safety limits.",
            "another_option": None,
            "meal_assessment": meal_assessment,
        }

    # 3. If user requested specific foods, evaluate those first
    if requested_foods:
        requested_candidates = valid_candidates[
            valid_candidates['name'].str.lower().isin(requested_foods)
        ]

        if not requested_candidates.empty:
            requested_matches, req_reason = get_best_matches(json_input, requested_candidates)
            top_requested = requested_matches.iloc[0]

            if top_requested['safety_score'] >= _REQUESTED_FOOD_SAFETY_THRESHOLD:
                # Requested food is safe enough — honour the user's preference
                top_pick = top_requested['name']

                # Runner-up: different food from the full pool
                all_matches, _ = get_best_matches(json_input, valid_candidates)
                runner_up = None
                for _, row in all_matches.iterrows():
                    if row['name'].lower() != top_pick.lower():
                        runner_up = row['name']
                        break

                return {
                    "food": top_pick,
                    "reason": req_reason,
                    "another_option": runner_up
                }

            # Requested food is unsafe — redirect, but stay in the same category
            # family so we don't swap pasta for fish.
            req_categories = _family_categories_of_requested(requested_foods, food_df)
            if req_categories:
                same_family = valid_candidates[
                    valid_candidates['categories'].apply(
                        lambda cats: isinstance(cats, list) and
                        not set(c.lower() for c in cats).isdisjoint(req_categories)
                    )
                ]
                # Exclude the exact food(s) the user asked for (they already failed)
                same_family = same_family[
                    ~same_family['name'].str.lower().isin(requested_foods)
                ]
                if not same_family.empty:
                    family_matches, family_reason = get_best_matches(json_input, same_family)
                    top_pick = family_matches.iloc[0]['name'] if not family_matches.empty else None
                    if top_pick:
                        # Runner-up: prefer foods that also share a taste/texture tag with
                        # the original request so we don't suggest parmesan for a milkshake.
                        all_cats_original = _categories_of_requested(requested_foods, food_df)
                        taste_cats_original = all_cats_original & _GENERIC_CATEGORIES

                        runner_up_pool = same_family[
                            ~same_family['name'].str.lower().isin([top_pick.lower()])
                        ]
                        if taste_cats_original and not runner_up_pool.empty:
                            taste_filtered = runner_up_pool[runner_up_pool['categories'].apply(
                                lambda cats: isinstance(cats, list) and
                                not set(c.lower() for c in cats).isdisjoint(taste_cats_original)
                            )]
                            if not taste_filtered.empty:
                                runner_up_pool = taste_filtered

                        runner_up = None
                        if not runner_up_pool.empty:
                            ru_matches, _ = get_best_matches(json_input, runner_up_pool)
                            runner_up = ru_matches.iloc[0]['name'] if not ru_matches.empty else None

                        return {
                            "food": top_pick,
                            "reason": family_reason,
                            "another_option": runner_up
                        }

    # 4. Vague request or no same-family alternative found → best overall pick
    best_matches, top_reason = get_best_matches(json_input, valid_candidates)

    top_pick = best_matches.iloc[0]['name'] if not best_matches.empty else None
    runner_up = best_matches.iloc[1]['name'] if len(best_matches) > 1 else None

    return {
        "food": top_pick,
        "reason": top_reason,
        "another_option": runner_up
    }
