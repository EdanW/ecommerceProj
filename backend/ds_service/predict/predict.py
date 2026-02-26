import pandas as pd
from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB
from .predict_utils import filter_by_constraints, get_best_matches

def _get_safety_threshold(glucose_level):
    """
    Dynamic safety threshold based on current glucose.

    At low glucose (< 90) the user actually needs carbs — being too restrictive
    here is medically wrong. At normal glucose we apply a moderate threshold.
    At elevated glucose we're stricter.

    The model is somewhat conservative so we keep thresholds low enough that
    reasonable foods (potatoes at 80 mg/dL, mac and cheese at 120 mg/dL) still pass.
    """
    if glucose_level < 90:
        return 0.05   # near-unconditional approval — user needs carbs, redirecting is medically wrong
    elif glucose_level < 120:
        return 0.28   # moderate — high-GI foods can still pass at normal glucose
    else:
        return 0.35   # standard — elevated glucose, only redirect genuinely risky picks

# these tags show up on basically every food (pasta is savory, ice cream is cold, etc.)
# they don't tell us anything useful about what FAMILY a food belongs to.
# we strip them out before doing category-based matching so "tuna" doesn't
# accidentally match "pasta" just because both are tagged savory.
_GENERIC_CATEGORIES = {"savory", "sweet", "hot", "cold", "spicy", "crunchy",
                       "creamy", "salty", "sour", "dessert"}


def _categories_of_requested(requested_foods, food_df):
    # grabs ALL category tags from the food(s) the user asked for,
    # including taste tags like sweet/cold/creamy
    rows = food_df[food_df['name'].str.lower().isin(requested_foods)]
    cats = set()
    for cat_list in rows['categories']:
        if isinstance(cat_list, list):
            cats.update(c.lower() for c in cat_list)
    return cats


def _family_categories_of_requested(requested_foods, food_df):
    """
    Figures out which food "family" the requested food belongs to, so when
    we have to redirect (food is unsafe), we stay in the same ballpark.

    We prefer the meaningful type categories (grain, dairy, pasta, seafood…)
    over generic taste tags. For example pasta gives us {grain, italian, pasta}
    which keeps the redirect within carb foods instead of jumping to fish.

    The edge case is something like a chocolate milkshake whose only tags are
    sweet/cold/creamy — all generic. If we stripped those we'd have nothing left
    and the redirect could land on literally any food (we once got avocado).
    So if there are no type categories, we fall back and use the taste tags.
    """
    all_cats = _categories_of_requested(requested_foods, food_df)
    type_cats = all_cats - _GENERIC_CATEGORIES
    return type_cats if type_cats else all_cats


def _evaluate_single_food(food_name, valid_candidates, food_df, json_input):
    """
    Scores one specific food and figures out what to actually recommend.

    If the food is safe enough (above our threshold) → return it as-is.
    If it's not → find the closest alternative in the same food family.

    Used for multi-food requests like "steak and mashed potatoes" so we can
    evaluate the main dish and the side independently instead of just picking
    whichever one scores highest overall.

    Returns: (resolved_name, was_redirected, reason)
        resolved_name  — what we're actually going to recommend
        was_redirected — True if we swapped it for something safer
        reason         — one-line explanation for the user
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
    Main prediction function. Takes the user's current glucose state + craving
    and returns the best food to eat right now.

    The overall flow:
    1. Filter the full food database down to realistic candidates (removes excluded
       foods, wrong meal types, condiments, etc.)
    2. If the user asked for specific foods, score those first.
       - Safe enough? Give them what they asked for.
       - Too risky? Redirect, but stay within the same food family.
    3. If the user asked for multiple foods (e.g. a meal), evaluate each separately.
    4. If the request was vague (no specific food named), just return the top scorer.
    """
    print("entered predict")

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
            "reason": "no foods in POC database that support this scenario",
            "another_option": None
        }

    requested_foods = [f.lower() for f in json_input.get('craving', {}).get('foods', [])]

    # if the user named more than one food (like "steak and mashed potatoes"),
    # handle each one separately so we can address the whole meal in our response
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

        # the "primary" food shown in the response is just the first one that resolved
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

    # single food request — score it and decide whether to approve or redirect
    if requested_foods:
        requested_candidates = valid_candidates[
            valid_candidates['name'].str.lower().isin(requested_foods)
        ]

        if not requested_candidates.empty:
            requested_matches, req_reason = get_best_matches(json_input, requested_candidates)
            top_requested = requested_matches.iloc[0]

            threshold = _get_safety_threshold(json_input.get('glucose_level', 100))
            if top_requested['safety_score'] >= threshold:
                # food is safe enough — give the user what they asked for
                top_pick = top_requested['name']

                # runner-up: prefer something in the same type family as the top pick.
                # find the most specific type category (the one with the fewest matching
                # foods in the candidate pool) and score within that narrower pool.
                # this prevents e.g. "tuna in water" appearing as runner-up to "chicken
                # salad" just because it has 0 carbs — a salad-family food is far more
                # relevant.
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

            # food didn't clear the threshold — redirect to something safer
            # but stay in the same category family (no suggesting fish for pasta)
            req_categories = _family_categories_of_requested(requested_foods, food_df)
            if req_categories:
                same_family = valid_candidates[
                    valid_candidates['categories'].apply(
                        lambda cats: isinstance(cats, list) and
                        not set(c.lower() for c in cats).isdisjoint(req_categories)
                    )
                ]
                # drop the original food (it already failed the safety check)
                same_family = same_family[
                    ~same_family['name'].str.lower().isin(requested_foods)
                ]
                if not same_family.empty:
                    family_matches, family_reason = get_best_matches(json_input, same_family)
                    top_pick = family_matches.iloc[0]['name'] if not family_matches.empty else None
                    if top_pick:
                        # for the runner-up we need a tighter filter.
                        # the "same family" pool can be broad — dairy includes both
                        # milkshakes AND parmesan. we require the runner-up to also
                        # match the TASTE profile of the original (sweet/cold/creamy)
                        # so we don't suggest cheese as an alternative to a milkshake.
                        all_cats_original = _categories_of_requested(requested_foods, food_df)
                        taste_cats_original = all_cats_original & _GENERIC_CATEGORIES

                        runner_up_pool = same_family[
                            ~same_family['name'].str.lower().isin([top_pick.lower()])
                        ]
                        if taste_cats_original and not runner_up_pool.empty:
                            # strictest filter first: must match ALL taste tags
                            # e.g. milkshake needs sweet+cold+creamy, not just one of them
                            taste_filtered = runner_up_pool[runner_up_pool['categories'].apply(
                                lambda cats: isinstance(cats, list) and
                                taste_cats_original.issubset(set(c.lower() for c in cats))
                            )]
                            if taste_filtered.empty:
                                # nothing matched all tags — relax to "at least one"
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

    # vague request (no specific food named) or no same-family alternative found —
    # just return whatever scores highest in the filtered pool
    best_matches, top_reason = get_best_matches(json_input, valid_candidates)

    top_pick = best_matches.iloc[0]['name'] if not best_matches.empty else None
    runner_up = best_matches.iloc[1]['name'] if len(best_matches) > 1 else None

    return {
        "food": top_pick,
        "reason": top_reason,
        "another_option": runner_up
    }
