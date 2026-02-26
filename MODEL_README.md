# Food Safety Recommendation Model

This document covers the full data science pipeline behind Nouri's food recommendation feature — the training data, the math, the model architecture, and how predictions turn into user-facing suggestions.

---

## Overview

The core problem: **given a pregnant woman's current glucose reading and a food she wants to eat, should she eat it?**

This is a binary classification problem. The model outputs a probability between 0 and 1 representing how "safe" a food is for this specific user at this specific moment. We use that score to either approve the user's food choice or redirect them to a safer alternative in the same food family.

---

## The Data Pipeline

Since we don't have access to a real clinical dataset, we generate synthetic training data using a handcrafted **oracle risk function** — a rule set that encodes domain knowledge about gestational diabetes into numerical labels. The model then learns to approximate this function from 50,000 examples.

### Step 1 — Feature Space

Each training example is a 9-dimensional vector describing one (user state, food) pair.

**User Features (6)**

| Feature | Description | Distribution |
|---|---|---|
| `glucose_level` | Current blood glucose in mg/dL | N(glucose_avg, 25), clamped [60, 350] |
| `glucose_avg` | Rolling glucose average — proxy for A1C / overall control | N(105, 15), clamped [80, 180] |
| `glucose_trend` | Direction glucose is heading: −1 falling, 0 stable, +1 rising | Uniform over {−1, 0, 1} |
| `pregnancy_week` | Week of pregnancy | Uniform integer [4, 42] |
| `intensity` | Activity/stress level: 0 = low, 1 = medium, 2 = high | Uniform over {0, 1, 2} |
| `time_of_day` | 0 = morning, 1 = afternoon, 2 = evening, 3 = night | Uniform over {0, 1, 2, 3} |

**Food Features (3)**

| Feature | Description |
|---|---|
| `food_gi` | Glycemic Index — rate at which food raises blood glucose (0–100 scale) |
| `food_carbs` | Grams of carbohydrates per serving (± 10% uniform noise applied) |
| `food_sugar` | Grams of sugar per serving (± 10% uniform noise applied) |

The ±10% noise on carbs and sugar ensures the model sees a realistic spread of values rather than memorizing the exact numbers from our food database.

---

### Step 2 — Oracle Risk Function

The oracle assigns a numerical risk score **R** to each (user, food) pair. This score is what the model is trained to predict from.

**Base risk:**

```
R_base = (food_carbs × 1.0) + (food_sugar × 1.5)
R = R_base × (food_gi / 50)
```

Sugar is weighted 1.5× because monosaccharides are absorbed faster than complex carbohydrates and cause a sharper glucose response. The GI factor scales risk proportionally to how quickly the food raises blood glucose — a food at GI 100 doubles the base risk relative to GI 50.

**Context multipliers** are then applied in sequence:

| Condition | Effect | Rationale |
|---|---|---|
| `glucose_level > 160` | R × 1.5 | Already elevated — any additional spike carries greater risk |
| `glucose_trend == 1` | R += food_sugar × 2.0 | Rising trend + dietary sugar compounds the spike |
| `time_of_day == 3` (night) | R × 1.4 | Insulin resistance peaks at night |
| `pregnancy_week > 24` | R × 1.25 | Late 2nd/3rd trimester significantly increases insulin resistance |
| `glucose_avg > 120` | R × 1.2 | Chronically elevated average signals reduced metabolic flexibility |
| `intensity == 2` | R × 1.1 | High stress elevates cortisol, slightly increasing baseline risk |

**Worked example — chocolate milkshake at normal glucose:**

```
food_carbs = 65g, food_sugar = 55g, food_gi = 63
glucose_level = 147, glucose_trend = 0, pregnancy_week = 28, time_of_day = 1

R_base = (65 × 1.0) + (55 × 1.5) = 65 + 82.5 = 147.5
gi_factor = 63 / 50 = 1.26
R = 147.5 × 1.26 = 185.85

Multipliers: pregnancy_week > 24 → R × 1.25
R = 185.85 × 1.25 = 232.3

Threshold at glucose_level 147 (normal range): 60
232.3 > 60  →  is_safe = 0  (unsafe — correctly flagged)
```

**Worked example — grilled chicken at normal glucose:**

```
food_carbs = 0g, food_sugar = 0g, food_gi = 0
R_base = 0, gi_factor = 0 / 50 = 0
R = 0 × 0 = 0

Any threshold → 0 < 60  →  is_safe = 1  (safe)
```

---

### Step 3 — Dynamic Safety Threshold

The label `is_safe` is determined by comparing R against a threshold τ that scales with the user's current glucose level:

| Glucose Level | τ | Rationale |
|---|---|---|
| < 120 mg/dL | 75 | Low glucose — the user can tolerate moderate carbs |
| 120–160 mg/dL | 60 | Normal range — most regular foods are fine |
| > 160 mg/dL | 35 | Already elevated — limit carbs/sugar aggressively |

```
is_safe = 1  if  R < τ + ε,  where ε ~ N(0, 3)
is_safe = 0  otherwise
```

The small Gaussian noise ε on τ ensures the model sees examples on both sides of the boundary near the threshold, preventing it from learning a hard cliff rather than a smooth probability.

**Why this matters:** An earlier version used a fixed τ = 45 for all glucose levels. This caused pasta (R ≈ 56 at normal glucose) to always be labelled unsafe regardless of context. The model learned that zero-carb foods always win and recommended tuna for nearly every request. The dynamic threshold fixed this.

---

## The Model

### Algorithm: XGBoost Gradient Boosted Classifier

XGBoost builds an **additive ensemble** of T decision trees. Each tree is trained to correct the residual errors of all previous trees. The final prediction is the sum:

```
F_T(x) = Σ_{t=1}^{T} f_t(x)
```

where each f_t is a shallow decision tree fitted at step t.

**Loss function — Binary Cross-Entropy (log loss):**

```
L(y, p) = −[ y · log(p) + (1 − y) · log(1 − p) ]
```

where y ∈ {0, 1} is the true label (safe/unsafe) and p ∈ (0, 1) is the predicted probability. The model minimizes the sum of this loss over all training examples.

**How each new tree is chosen:**

At step t, the new tree f_t is fit to the **negative gradient** of the loss with respect to the previous prediction F_{t−1}(x):

```
r_i = −∂L(y_i, F_{t-1}(x_i)) / ∂F_{t-1}(x_i)
```

These are called "pseudo-residuals." The tree learns to predict them, and its predictions are added to the ensemble scaled by the learning rate η = 0.1:

```
F_t(x) = F_{t-1}(x) + η · f_t(x)
```

With 100 trees and η = 0.1, the ensemble gradually converges on the true class boundary.

**Converting raw score to probability:**

XGBoost's raw output F_T(x) is a log-odds score. `predict_proba` converts it to a probability via the sigmoid function:

```
p = σ(F_T(x)) = 1 / (1 + e^(−F_T(x)))
```

This is the "safety score" we compare against a dynamic threshold based on the user's current glucose level. At p = 0.5 the model is equally confident in both classes; the dynamic threshold gives more benefit of the doubt when glucose is low (where eating carbs is medically important) and is stricter when glucose is already elevated.

**Hyperparameters:**

| Parameter | Value | Reasoning |
|---|---|---|
| `n_estimators` | 100 | Number of trees T in the ensemble |
| `max_depth` | 5 | Maximum depth per tree — limits overfitting by capping complexity |
| `learning_rate` | 0.1 | Step size η — smaller = more conservative updates, less overfitting |
| `eval_metric` | logloss | Optimisation objective (binary cross-entropy) |

---

### Training Procedure (`train_model.py`)

1. **80/20 split** — 80% training set, 20% hold-out test set. `random_state=42` makes the split reproducible.

2. **5-fold stratified cross-validation** on the training set:
   - Splits the 40,000 training examples into 5 equal folds
   - Trains on 4 folds, validates on the 5th — repeated 5 times
   - `StratifiedKFold` ensures each fold preserves the same safe/unsafe class ratio as the full dataset
   - If the standard deviation across folds exceeds 0.03, it means accuracy is inconsistent across data subsets — a sign of a data quality issue

3. **Final training** on the full 40,000-example training set once the architecture is validated

4. **Hold-out evaluation** — accuracy, precision, recall, and F1 on the 20% test set the model never saw during training

5. Model serialized to disk as `food_safety_model.pkl` using `joblib`

**Achieved accuracy:** ~98% on the hold-out test set, with tight cross-validation variance indicating the model generalises well and is not overfit to the training data.

---

### Feature Importance

XGBoost calculates feature importance as **Gain** — the average improvement in log loss (reduction in prediction error) achieved by all splits that use a given feature, averaged across all 100 trees. Features with higher Gain contributed more to accurate classification.

Top 5 features in order:

1. `glucose_level` — the current reading is the single strongest signal, because the dynamic threshold is directly tied to it
2. `food_gi` — directly controls the gi_factor multiplier in the oracle
3. `food_carbs` — largest contributor to R_base
4. `food_sugar` — weighted 1.5× in R_base and adds extra risk when glucose_trend is rising
5. `glucose_trend` — a rising trend compounds the sugar additive term

Time of day, pregnancy week, glucose_avg, and intensity have lower but non-negligible importance, capturing context that carb count alone cannot.

---

## The Prediction Pipeline

At inference time:

```
User message (free text)
    ↓
SpaCy NLP layer — extracts food names, meal type, excluded foods, craving categories
    ↓
filter_by_constraints() — removes condiments, excluded items, wrong meal types, blacklisted categories
    ↓
For each remaining candidate food:
    create_features(user_state, food) → 9-feature vector
    model.predict_proba(vector) → safety score p ∈ [0, 1]
    ↓
Ranking and recommendation logic
    ↓
User-facing response
```

### Recommendation Logic (`predict.py`)

**Case 1: Single specific food (e.g. "I want pasta")**
- Score the requested food
- p ≥ threshold → approve it (user gets what they asked for)
- p < threshold → redirect to the safest food in the same category family
- Threshold is dynamic: 0.05 (glucose < 90), 0.28 (glucose 90–120), 0.35 (glucose ≥ 120)

**Case 2: Multi-food meal (e.g. "steak and mashed potatoes")**
- Each food is evaluated independently
- The response addresses both the main dish and the side

**Case 3: Vague craving (e.g. "something sweet for a snack")**
- No specific food to evaluate → return the highest-scoring candidate from the filtered pool

### Category-Family Redirect

When redirecting, we don't just pick the globally safest food (that gave us tuna every time). We find the safest food within the same **type family** as what the user requested.

Each food has type categories (pasta, grain, dairy, seafood…) and generic taste tags (savory, sweet, cold, creamy…). We strip the taste tags to identify the actual food family:

- "pasta" → type categories: `{pasta, grain, italian}` → redirect stays within grain/carb foods
- "chocolate milkshake" → type categories: `{dairy, drink, dessert}` → redirect stays within sweet cold drinks

**Edge case:** if a food only has taste tags (no type categories), we use the taste tags for matching instead of getting an empty set that could redirect to anything.

**Runner-up filtering:** the second suggestion must share all taste tags with the original request — not just one. This prevents "parmesan" from appearing as a milkshake alternative just because both are tagged `dairy`. Parmesan has `savory` and `salty` but not `sweet` + `cold` + `creamy`, so it gets filtered out.

---

## File Structure

```
backend/ds_service/
├── predict/
│   ├── predict.py              # recommendation logic (approve/redirect/multi-food)
│   └── predict_utils.py        # model loading, candidate filtering, scoring
├── preprocessing/
│   ├── preprocessing.py        # builds the 9-feature vector from user+food data
│   └── preprocessing_utils.py  # encodes trend (-1/0/1), intensity (0/1/2), time (0-3)
├── models/
│   └── food_safety_model.pkl   # trained XGBoost model (loaded at runtime)
├── data/
│   └── synthetic_diabetes_data.csv   # 50k training examples
└── MODEL_README.md             # this file

ds_insights_and_utils/
├── generate_synthetic_data.py   # generates training data using the oracle risk function
└── train_model.py               # trains XGBoost with 5-fold CV, saves the pkl
```

---

## Reproducing the Model

```bash
python3 -m ds_insights_and_utils.generate_synthetic_data
python3 -m ds_insights_and_utils.train_model
```

This regenerates 50,000 training examples, retrains XGBoost, and overwrites the `.pkl` file. The server loads the new model on the next request (lazy loading — it reads the file once and caches it in memory).
