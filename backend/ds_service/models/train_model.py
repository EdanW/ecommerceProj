import pandas as pd
import xgboost as xgb
import joblib
import os
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report

# --- CONFIG ---
DATA_PATH = "backend/ds_service/data/synthetic_diabetes_data.csv"
MODEL_PATH = "backend/ds_service/models/food_safety_model.pkl"

def train():
    print("🚀 Starting Model Training...")
    
    # 1. Load Data
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: Data file not found at {DATA_PATH}")
        print("Run 'python -m backend.ds_service.data.generate_synthetic_data' first.")
        return

    df = pd.read_csv(DATA_PATH)
    
    # 2. Separate Features (X) and Target (y)
    # The 'is_safe' column is what we want to predict
    X = df.drop(columns=['is_safe'])
    y = df['is_safe']
    
    print(f"   Loaded {len(df)} rows.")
    print(f"   Features: {list(X.columns)}")

    # 3. Split Data (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. Initialize XGBoost
    model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        eval_metric='logloss'
    )
    
    # --- 5. Cross-Validation (The Robustness Check) ---
    print("\n🔄 Running 5-Fold Cross-Validation...")
    
    # StratifiedKFold ensures every fold has the same % of safe/unsafe examples
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # This trains the model 5 times on different subsets of X_train
    cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring='accuracy')
    
    print(f"   CV Scores per fold: {cv_scores}")
    print(f"   ✅ Average CV Accuracy: {cv_scores.mean():.2%} (+/- {cv_scores.std() * 2:.2%})")
    
    # Logic check: If accuracy swings wildly (e.g., 80% to 99%), the model is unstable
    if cv_scores.std() > 0.03:
        print("   ⚠️ Warning: High variance in model performance. Data might be too noisy.")

    # 6. Final Training
    # Now that we know the architecture is stable, we train on the FULL X_train
    print("\n💪 Training final model on full training set...")
    model.fit(X_train, y_train)

    # 7. Evaluate on the Hold-Out Test Set
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"📊 Final Test Set Accuracy: {accuracy:.2%}")
    print("\nDetailed Report:")
    print(classification_report(y_test, y_pred))

    # 8. Save the Model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"💾 Model saved to: {MODEL_PATH}")
    
    # 9. Feature Importance
    print("\n🔍 Top 5 Most Important Features:")
    importance = model.feature_importances_
    feats = pd.DataFrame({'Feature': X.columns, 'Importance': importance})
    print(feats.sort_values(by='Importance', ascending=False).head(5))
    
if __name__ == "__main__":
    train()