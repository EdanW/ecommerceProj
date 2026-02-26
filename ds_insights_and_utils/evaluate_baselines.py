import pandas as pd
import joblib
import random
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# --- CONFIG ---
DATA_PATH = "backend/ds_service/data/synthetic_diabetes_data.csv"
MODEL_PATH = "backend/ds_service/models/food_safety_model.pkl"

def run_evaluation():
    print("🥊 Starting Model vs. Baseline Comparison...\n")
    
    # 1. Load Data
    if not os.path.exists(DATA_PATH):
        print("❌ Data not found! Run generation script first.")
        return

    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=['is_safe'])
    y_true = df['is_safe']
    
    # Use the EXACT same split seed as training to ensure we test on unseen data
    _, X_test, _, y_test = train_test_split(X, y_true, test_size=0.2, random_state=42)
    
    print(f"   Testing on {len(X_test)} unseen examples.")

    # --- CONTESTANT 1: The Random Guesser ---
    # Just flips a coin.
    y_pred_random = [random.choice([0, 1]) for _ in range(len(y_test))]

    # --- CONTESTANT 2: The Static Heuristic (Standard Guidelines) ---
    # Logic: "If Carbs < 45g AND Sugar < 15g, it's Safe."
    # This ignores Glucose Level, Time of Day, and Trends.
    y_pred_heuristic = []
    for _, row in X_test.iterrows():
        # Standard clinical advice often sets 45-60g as a limit
        if row['food_carbs'] < 45 and row['food_sugar'] < 15:
            y_pred_heuristic.append(1) # Predict Safe
        else:
            y_pred_heuristic.append(0) # Predict Unsafe

    # --- CONTESTANT 3: Our XGBoost Model ---
    if not os.path.exists(MODEL_PATH):
        print("❌ Model not found! Run training script first.")
        return
        
    model = joblib.load(MODEL_PATH)
    y_pred_model = model.predict(X_test)

    # 3. Calculate Scores & Compare
    results = []
    
    for name, pred in [("Random Guess", y_pred_random), 
                       ("Static Heuristic", y_pred_heuristic), 
                       ("XGBoost Model", y_pred_model)]:
        
        acc = accuracy_score(y_test, pred)
        prec = precision_score(y_test, pred)
        rec = recall_score(y_test, pred)
        f1 = f1_score(y_test, pred)
        
        results.append({
            "Model": name,
            "Accuracy": f"{acc:.1%}",
            "Precision (Safety)": f"{prec:.1%}",
            "Recall (Finding Food)": f"{rec:.1%}",
            "F1 Score": f"{f1:.1%}"
        })

    # 4. Display Results Table
    results_df = pd.DataFrame(results)
    print("\n🏆 FINAL RESULTS 🏆")
    print(results_df.to_markdown(index=False))
    
    # 5. The "Aha!" Moment: Why did the Heuristic Fail?
    print("\n🔍 Case Study: Where did the Heuristic get it wrong?")
    
    # Find a case where Heuristic said SAFE (1) but Truth was UNSAFE (0)
    # This is a "False Negative" - the most dangerous error (approving unsafe food).
    failures = X_test.copy()
    failures['heuristic_pred'] = y_pred_heuristic
    failures['true_label'] = y_test
    failures['model_pred'] = y_pred_model
    
    # Filter for Dangerous Mistakes
    dangerous_mistakes = failures[(failures['heuristic_pred'] == 1) & (failures['true_label'] == 0)]
    
    if not dangerous_mistakes.empty:
        # Get the first example
        example = dangerous_mistakes.iloc[0]
        
        print(f"\n   Example Scenario: User wants to eat a food with {example['food_carbs']}g Carbs.")
        print(f"   ---------------------------------------------------------------")
        print(f"   ❌ Heuristic says:   SAFE  (Because {example['food_carbs']}g < 45g limit)")
        print(f"   ✅ Ground Truth is:  UNSAFE")
        print(f"   🤖 Model says:       {'SAFE' if example['model_pred'] == 1 else 'UNSAFE'}")
        print(f"   ---------------------------------------------------------------")
        print(f"   Why it's actually UNSAFE (The Context):")
        print(f"   - Current Glucose: {example['glucose_level']} (High?)")
        print(f"   - Time of Day:     {example['time_of_day']} (3=Night is risky)")
        print(f"   - Glucose Trend:   {example['glucose_trend']} (1=Rising is bad)")
    else:
        print("   (No obvious heuristic failures found in this batch)")

if __name__ == "__main__":
    run_evaluation()