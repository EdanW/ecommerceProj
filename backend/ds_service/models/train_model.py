import pandas as pd
import xgboost as xgb
import joblib
import os
from sklearn.model_selection import train_test_split
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

    # 4. Initialize & Train XGBoost
    # n_estimators=100 means it builds 100 little decision trees to vote
    model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    
    print("   Training XGBoost Classifier...")
    model.fit(X_train, y_train)

    # 5. Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"✅ Training Complete!")
    print(f"📊 Accuracy on Test Set: {accuracy:.2%}")
    print("\nDetailed Report:")
    print(classification_report(y_test, y_pred))

    # 6. Save the Model
    # Ensure directory exists
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"💾 Model saved to: {MODEL_PATH}")
    
    # 7. Sanity Check: What matters most?
    print("\n🔍 Top 5 Most Important Features:")
    # Get feature importance
    importance = model.feature_importances_
    # Map to column names
    feats = pd.DataFrame({'Feature': X.columns, 'Importance': importance})
    print(feats.sort_values(by='Importance', ascending=False).head(5))
if __name__ == "__main__":
    train()