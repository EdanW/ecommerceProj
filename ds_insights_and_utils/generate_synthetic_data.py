import pandas as pd
import numpy as np
import random
import os

from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB

# --- CONFIG ---
NUM_SAMPLES = 50000  # 50k examples gives the model enough variety without being overkill
OUTPUT_FILE = "backend/ds_service/data/synthetic_diabetes_data.csv"

def generate_data():
    data = []
    food_names = list(FOOD_DB.keys())

    print(f"🚀 Generating {NUM_SAMPLES} aligned scenarios...")

    for _ in range(NUM_SAMPLES):
        # ── A. Random User Context ───────────────────────────────────────────

        # rolling glucose average — similar to what A1C measures in the clinic.
        # represents how well-controlled the user's diabetes is overall.
        # people with a higher average are more sensitive to carb spikes.
        glucose_avg = int(np.random.normal(105, 15))
        glucose_avg = max(80, min(180, glucose_avg))

        # today's actual glucose reading fluctuates around the baseline.
        # clamped to physiologically realistic min/max values.
        glucose_level = int(np.random.normal(glucose_avg, 25))
        glucose_level = max(60, min(350, glucose_level))

        # which direction is glucose heading right now?
        # -1 = falling, 0 = stable, 1 = rising
        # a rising trend is dangerous if you eat something sugary on top of it
        glucose_trend = np.random.choice([-1, 0, 1])

        # time of day affects insulin sensitivity throughout the day.
        # morning (0) = most sensitive, night (3) = most resistant.
        # 0=Morning, 1=Afternoon, 2=Evening, 3=Night
        time_of_day = np.random.choice([0, 1, 2, 3])

        # pregnancy week: insulin resistance increases a lot in late 2nd/3rd trimester
        # intensity: high intensity (2) implies possible stress/cortisol, slightly raises risk
        pregnancy_week = np.random.randint(4, 42)
        intensity = np.random.choice([0, 1, 2])   # 0=Low, 1=Med, 2=High

        # ── B. Pick a Random Food ────────────────────────────────────────────
        food_name = random.choice(food_names)
        stats = FOOD_DB[food_name]

        # add small random noise so the model sees slight variation —
        # real-world values won't be exactly the same every time either
        noise = np.random.uniform(0.9, 1.1)
        food_carbs = round(stats.get("carbs", 10) * noise, 1)
        food_sugar = round(stats.get("sugar", 2) * noise, 1)
        food_gi = stats.get("glycemic_index", 50)  # GI doesn't really vary per serving

        # ── C. Oracle Risk Score ─────────────────────────────────────────────
        # this is the "ground truth" that we train the model against.
        # the model will learn to approximate this logic from the 50k examples.
        #
        # risk = (carbs + sugar weighted) * GI factor * context multipliers

        risk_score = 0

        # base impact: sugar is weighted 1.5x because it hits faster than complex carbs
        risk_score += (food_carbs * 1.0)
        risk_score += (food_sugar * 1.5)

        # GI multiplier: high-GI foods cause sharper glucose spikes
        # a food at GI=100 doubles the base risk compared to GI=50
        gi_factor = food_gi / 50.0
        risk_score *= gi_factor

        # context multipliers — these adjust risk based on the user's current state
        if glucose_level > 160:
            risk_score *= 1.5   # already high — any extra glucose is a bigger deal

        if glucose_trend == 1:
            risk_score += (food_sugar * 2.0)  # rising + eating sugar = bad combo

        if time_of_day == 3:
            risk_score *= 1.4   # night = high insulin resistance, harder to process carbs

        if pregnancy_week > 24:
            risk_score *= 1.25  # late pregnancy causes significant insulin resistance

        if glucose_avg > 120:
            risk_score *= 1.2   # chronically high average = less metabolic flexibility

        if intensity == 2:
            risk_score *= 1.1   # high stress slightly elevates baseline risk

        # ── D. Dynamic Threshold ─────────────────────────────────────────────
        # whether a food gets labelled "safe" depends on the user's current glucose.
        # we can't use a single fixed cutoff for everyone.
        #
        # original bug: we used a fixed threshold of 45, which meant pasta (risk ~56)
        # was ALWAYS labelled unsafe even when the user's glucose was totally normal.
        # the model then learned "zero-carb foods always win" and recommended tuna
        # for literally every request. not ideal.
        #
        # fix: the threshold scales with current glucose level.
        # low glucose → more permissive (pasta is fine at 115 mg/dL)
        # normal range → moderate (most regular foods are okay)
        # high glucose → strict (limit carbs/sugar hard)
        if glucose_level < 120:
            base_threshold = 75
        elif glucose_level < 160:
            base_threshold = 60
        else:
            base_threshold = 35

        # small noise on the threshold so the model sees a distribution of examples
        # near the boundary, not a hard cliff
        threshold_noise = np.random.normal(0, 3.0)
        effective_threshold = base_threshold + threshold_noise

        is_safe = 1 if risk_score < effective_threshold else 0

        # ── E. Save Row ──────────────────────────────────────────────────────
        data.append({
            # user state
            "glucose_level": glucose_level,
            "glucose_avg": glucose_avg,
            "glucose_trend": glucose_trend,
            "pregnancy_week": pregnancy_week,
            "intensity": intensity,
            "time_of_day": time_of_day,
            # food nutrition
            "food_gi": food_gi,
            "food_carbs": food_carbs,
            "food_sugar": food_sugar,
            # label
            "is_safe": is_safe
        })

    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    safe_count = df['is_safe'].sum()
    print(f"✅ Saved {len(df)} rows to {OUTPUT_FILE}")
    print(f"📊 Class Balance: Safe={safe_count} ({safe_count/len(df):.0%}) | Unsafe={len(df)-safe_count}")

if __name__ == "__main__":
    generate_data()
