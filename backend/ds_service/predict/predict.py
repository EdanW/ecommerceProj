import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from .predict_utils import filter_by_constraints, get_best_matches

def _get_safety_threshold(glucose_level):
    """
    Returns the minimum safety score a requested food must achieve to be approved
    without redirection. The threshold scales with current glucose level to reflect
    clinical gestational diabetes management priorities: at low glucose, carbohydrate
    intake is important and aggressive restriction is contraindicated; at elevated
    glucose, stricter filtering is applied to limit glycemic load.
    """
    if glucose_level < 90:
        return 0.05   # low glucose — high tolerance, carbohydrate intake is appropriate
    elif glucose_level < 120:
        return 0.28   # normal range — moderate restriction, high-GI foods may still be acceptable
    else:
        return 0.35   # elevated glucose — standard conservative threshold

# Taste and texture tags shared across unrelated food families.
# Excluded from category-based family matching to prevent spurious cross-family redirects
# (e.g., matching "tuna" to "pasta" solely because both carry the "savory" tag).
_GENERIC_CATEGORIES = {"savory", "sweet", "hot", "cold", "spicy", "crunchy",
                       "creamy", "salty", "sour", "dessert"}


def _categories_of_requested(requested_foods, food_df):
    # Returns all category tags (type and taste) associated with the requested foods.
    rows = food_df[food_df['name'].str.lower().isin(requested_foods)]
    cats = set()
    for cat_list in rows['categories']:
        if isinstance(cat_list, list):
            cats.update(c.lower() for c in cat_list)
    return cats


def _family_categories_of_requested(requested_foods, food_df):
    """
    Returns the type-level category tags for the requested foods, used to anchor
    redirects within the same food family. Type categories (grain, dairy, pasta,
    seafood, etc.) are preferred over generic taste tags because they more precisely
    define what kind of food is being requested.

    Fallback: if a food carries no type-level categories (only generic tags such as
    sweet/cold/creamy), the taste tags are returned instead. Without this fallback,
    an empty category set would cause the redirect to draw from the entire food pool
    rather than staying within a semantically related group.
    """
    all_cats = _categories_of_requested(requested_foods, food_df)
    type_cats = all_cats - _GENERIC_CATEGORIES
    return type_cats if type_cats else all_cats


def _evaluate_single_food(food_name, valid_candidates, food_df, json_input):
    """
    Scores a single named food against the current glucose context and returns
    a recommendation. If the food clears the dynamic safety threshold it is
    approved as-is; otherwise the function finds the highest-scoring alternative
    within the same food-family category pool.

    Intended for use in multi-food requests (e.g. "steak and mashed potatoes")
    where each component of the meal is evaluated independently.

    Returns: (resolved_name, was_redirected, reason)
        resolved_name  — the food being recommended (original or redirect)
        was_redirected — True if the original food was replaced with an alternative
        reason         — one-line human-readable explanation for the recommendation
    """
    food_candidates = valid_candidates[
        valid_candidates['name'].str.lower() == food_name.lower()
    ]
    if not food_candidates.empty:
        matches, reason = get_best_matches(json_input, food_candidates)
        threshold = _get_safety_threshold(json_input.get('glucose_level', 100))
        if not matches.empty and matches.iloc[0]['safety_score'] >= threshold:
            return (matches.iloc[0]['name'], False, reason)

    # food is unsafe or wasn't in the filtered candidate pool — find something similar
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
    Entry point for the recommendation pipeline. Accepts a structured JSON payload
    containing the user's glucose state and parsed craving, and returns the most
    appropriate food recommendation.

    Pipeline:
    1. Convert the food database to a DataFrame and apply constraint filtering
       (exclusions, meal type, condiments, category whitelisting).
    2. If specific foods were requested, score them against the dynamic safety
       threshold. Approved foods are returned directly; foods that fail the threshold
       are redirected to the highest-scoring alternative in the same food family.
    3. Multi-food requests (e.g. a composed meal) are decomposed and each component
       is evaluated independently via _evaluate_single_food().
    4. Vague requests with no named food return the top-scoring candidate from the
       filtered pool.
    """
    # convert the food DB dict into a dataframe so we can filter/sort it
    food_list = []
    for name, stats in FOOD_DB.items():
        item = stats.copy()
        item['name'] = name
        food_list.append(item)
    food_df = pd.DataFrame(food_list)

    # run all the constraint filters (exclusions, meal type, categories…)
    valid_candidates = filter_by_constraints(food_df, json_input)
    if valid_candidates.empty:
        return {
            "food": None,
            "reason": "No matching foods found for the given craving and constraints.",
            "another_option": None
        }

    requested_foods = [f.lower() for f in json_input.get('craving', {}).get('foods', [])]

    # Multi-food requests are decomposed and each component is evaluated independently.
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

        # Primary food in the response is the first successfully resolved component.
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

    # Single food request: score the candidate and apply the safety threshold.
    if requested_foods:
        requested_candidates = valid_candidates[
            valid_candidates['name'].str.lower().isin(requested_foods)
        ]

        if not requested_candidates.empty:
            requested_matches, req_reason = get_best_matches(json_input, requested_candidates)
            top_requested = requested_matches.iloc[0]

            threshold = _get_safety_threshold(json_input.get('glucose_level', 100))
            if top_requested['safety_score'] >= threshold:
                top_pick = top_requested['name']

                # Runner-up selection: score within the most specific type-category pool
                # shared with the top pick. Using the narrowest matching category rather
                # than the full candidate pool keeps the alternative contextually relevant.
                top_type_cats = _family_categories_of_requested([top_pick], food_df)
                runner_up = None
                if top_type_cats:
                    most_specific_cat = min(
                        top_type_cats,
                        key=lambda cat: valid_candidates['categories'].apply(
                            lambda cats: isinstance(cats, list) and
                            cat in [c.lower() for c in cats]
                        ).sum()
                    )
                    same_type_pool = valid_candidates[
                        valid_candidates['categories'].apply(
                            lambda cats: isinstance(cats, list) and
                            most_specific_cat in [c.lower() for c in cats]
                        )
                    ]
                    same_type_pool = same_type_pool[
                        same_type_pool['name'].str.lower() != top_pick.lower()
                    ]
                    if not same_type_pool.empty:
                        ru_matches, _ = get_best_matches(json_input, same_type_pool)
                        runner_up = ru_matches.iloc[0]['name'] if not ru_matches.empty else None

                # fallback: global top scorer if no same-type option found
                if runner_up is None:
                    all_matches, _ = get_best_matches(json_input, valid_candidates)
                    for _, row in all_matches.iterrows():
                        if row['name'].lower() != top_pick.lower():
                            runner_up = row['name']
                            break

                return {
                    "food": top_pick,
                    "reason": req_reason,
                    "another_option": runner_up
                }

            # Food did not clear the safety threshold — redirect to the highest-scoring
            # alternative within the same food-family category pool.
            req_categories = _family_categories_of_requested(requested_foods, food_df)
            if req_categories:
                same_family = valid_candidates[
                    valid_candidates['categories'].apply(
                        lambda cats: isinstance(cats, list) and
                        not set(c.lower() for c in cats).isdisjoint(req_categories)
                    )
                ]
                # Exclude the original food from the redirect pool.
                same_family = same_family[
                    ~same_family['name'].str.lower().isin(requested_foods)
                ]
                if not same_family.empty:
                    family_matches, family_reason = get_best_matches(json_input, same_family)
                    top_pick = family_matches.iloc[0]['name'] if not family_matches.empty else None
                    if top_pick:
                        # Runner-up requires a tighter filter than the primary redirect.
                        # The family pool may span foods with very different taste profiles
                        # (e.g. the dairy family includes both milkshakes and hard cheeses).
                        # The runner-up is additionally required to match the taste tags
                        # of the original request to ensure sensory relevance.
                        all_cats_original = _categories_of_requested(requested_foods, food_df)
                        taste_cats_original = all_cats_original & _GENERIC_CATEGORIES

                        runner_up_pool = same_family[
                            ~same_family['name'].str.lower().isin([top_pick.lower()])
                        ]
                        if taste_cats_original and not runner_up_pool.empty:
                            # Prefer full match (all taste tags present); fall back to
                            # partial match (at least one shared tag) if nothing qualifies.
                            taste_filtered = runner_up_pool[runner_up_pool['categories'].apply(
                                lambda cats: isinstance(cats, list) and
                                taste_cats_original.issubset(set(c.lower() for c in cats))
                            )]
                            if taste_filtered.empty:
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

    # Vague request (no specific food named) or no same-family alternative found:
    # return the top-scoring food from the filtered candidate pool.
    best_matches, top_reason = get_best_matches(json_input, valid_candidates)

    top_pick = best_matches.iloc[0]['name'] if not best_matches.empty else None
    runner_up = best_matches.iloc[1]['name'] if len(best_matches) > 1 else None

    return {
        "food": top_pick,
        "reason": top_reason,
        "another_option": runner_up
    }
