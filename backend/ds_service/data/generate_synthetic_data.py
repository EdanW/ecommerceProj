import pandas as pd
import numpy as np
import random
import os

from backend.chat_layer_food_database import FOOD_DATABASE as FOOD_DB


# --- CONFIG ---
NUM_SAMPLES = 50000 
OUTPUT_FILE = "backend/ds_service/data/synthetic_diabetes_data.csv"

def generate_data():
    data = []
    food_names = list(FOOD_DB.keys())
    
    print(f"🚀 Generating {NUM_SAMPLES} aligned scenarios...")

    for _ in range(NUM_SAMPLES):
        # --- A. Random User Context ---
        
        # 1. Glucose Baseline (New Feature)
        # Represents the user's general health (A1C proxy). 
        # Higher avg = more likely to spike.
        glucose_avg = int(np.random.normal(105, 15)) 
        glucose_avg = max(80, min(180, glucose_avg))
        
        # 2. Current Glucose (Fluctuates around avg)
        glucose_level = int(np.random.normal(glucose_avg, 25))
        glucose_level = max(60, min(350, glucose_level))
        
        # 3. Trend (-1: Falling, 0: Stable, 1: Rising)
        glucose_trend = np.random.choice([-1, 0, 1])
        
        # 4. Time (0: Morning, 1: Afternoon, 2: Evening, 3: Night)
        # We assume your encoder maps Night to 3
        time_of_day = np.random.choice([0, 1, 2, 3]) 
        
        # 5. Pregnancy & Intensity (New Features)
        pregnancy_week = np.random.randint(4, 42) # Weeks 4 to 42
        intensity = np.random.choice([0, 1, 2])   # 0=Low, 1=Med, 2=High

        # --- B. Pick a Food ---
        food_name = random.choice(food_names)
        stats = FOOD_DB[food_name]
        
        # Add 10% noise so values aren't static
        noise = np.random.uniform(0.9, 1.1)
        food_carbs = round(stats.get("carbs", 10) * noise, 1)
        food_sugar = round(stats.get("sugar", 2) * noise, 1)
        food_gi = stats.get("glycemic_index", 50) # GI is usually constant

        # --- C. The "Oracle" Risk Logic ---
        # Calculates the Ground Truth Label
        
        risk_score = 0
        
        # 1. Base Impact (Carbs & Sugar)
        risk_score += (food_carbs * 1.0) 
        risk_score += (food_sugar * 1.5)
        
        # 2. GI Multiplier
        # High GI foods hit harder
        gi_factor = food_gi / 50.0 
        risk_score *= gi_factor

        # 3. User Context Multipliers
        
        # High Current Glucose
        if glucose_level > 160: risk_score *= 1.5
        
        # Rising Trend (Dangerous with sugar)
        if glucose_trend == 1: 
            risk_score += (food_sugar * 2.0)
            
        # Night Time (3) = High Insulin Resistance
        if time_of_day == 3: 
            risk_score *= 1.4
            
        # Pregnancy Stage 
        # Insulin resistance increases significantly in late 2nd/3rd trimester
        if pregnancy_week > 24:
            risk_score *= 1.25
            
        # Chronic High Avg Glucose (General Resistance)
        if glucose_avg > 120:
            risk_score *= 1.2
            
        # Intensity 
        # (Minor factor: High intensity might imply stress/cortisol, slightly increasing risk)
        if intensity == 2:
            risk_score *= 1.1

        # 4. Labeling with Noisy Threshold
        
        threshold_noise = np.random.normal(0, 3.0) 
        effective_threshold = 45 + threshold_noise
        
        # Now, a score of 46 might still be "Safe" if the noise pushes the threshold to 48.
        is_safe = 1 if risk_score < effective_threshold else 0
        
        # --- D. Append Data (Matching 9 Features EXACTLY) ---
        data.append({
            # User
            "glucose_level": glucose_level,
            "glucose_avg": glucose_avg,
            "glucose_trend": glucose_trend,
            "pregnancy_week": pregnancy_week,
            "intensity": intensity,
            "time_of_day": time_of_day,
            # Food
            "food_gi": food_gi,
            "food_carbs": food_carbs,
            "food_sugar": food_sugar,
            # Target
            "is_safe": is_safe
        })

    # Save
    df = pd.DataFrame(data)
    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    
    # Stats
    safe_count = df['is_safe'].sum()
    print(f"✅ Saved {len(df)} rows to {OUTPUT_FILE}")
    print(f"📊 Class Balance: Safe={safe_count} ({safe_count/len(df):.0%}) | Unsafe={len(df)-safe_count}")

if __name__ == "__main__":
    generate_data()