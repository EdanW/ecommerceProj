# Nouri - Gestational Diabetes Craving Assistant

A mobile-first web app that helps pregnant women with gestational diabetes find satisfying food options that fit their current glucose levels and pregnancy context.

## Overview

Nouri takes a user's food craving as free-text input, extracts structured information using NLP (SpaCy), and combines it with real-time glucose data and pregnancy context to recommend suitable food options through a trained XGBoost scoring model.

For example, a user can type *"I want something sweet and crunchy, but not chocolate"* and Nouri will:
1. Parse the craving (sweet + crunchy, exclude chocolate)
2. Ask a follow-up if anything is missing (e.g., "Is this for a snack or a meal?")
3. Score all matching foods using the user's current glucose level, trend, and pregnancy week
4. Return the safest best-fit recommendation with a human-readable explanation

---

## Architecture

### Backend (FastAPI + Python)

- **Chat Layer** — NLP pipeline that converts free-text cravings into structured JSON:
  - Negation-aware food and category extraction (SpaCy + PhraseMatcher)
  - Follow-up question handling when required fields are missing
  - Unsure/undecided detection ("surprise me", "I don't know") with graceful fallback
- **Recommendation Model** — Two-stage pipeline:
  1. **Filter** — Removes foods that don't match the craving (excluded foods/categories, wrong meal type)
  2. **Score** — XGBoost binary classifier (`is_safe`) ranks the remaining candidates using 9 features:
     - *User context:* current glucose, average glucose, glucose trend (−1/0/1), pregnancy week, craving intensity
     - *Food nutrition:* glycemic index (GI), carbs, sugar
- **REST API** — User auth, glucose tracking, craving analysis, food logging, feedback
- **Database** — SQLite via SQLModel; stores user profiles, glucose readings, food logs, and craving feedback

### Frontend (React + Vite)

- Mobile-first UI built inside a phone-frame layout
- Dashboard with live glucose status and pregnancy week tracker (with baby-size comparisons)
- Chat interface for craving input with follow-up question support
- Glucose trend charts (Recharts)
- Food log viewer and profile management

---

## Project Structure

```
ecommerceProj/
├── backend/
│   ├── main.py                        # FastAPI app + all API routes
│   ├── models.py                      # SQLModel DB models
│   ├── auth.py                        # JWT auth + password hashing
│   ├── simulator.py                   # Mock glucose sensor (dev only)
│   ├── chat_layer_handling.py         # Main NLP engine (AIEngine class)
│   ├── chat_layer_extractors.py       # SpaCy-based food/category extraction
│   ├── chat_layer_negation.py         # Negation detection logic
│   ├── chat_layer_nlp.py              # SpaCy model + PhraseMatcher setup
│   ├── chat_layer_food_database.py    # Food database + keyword mappings
│   ├── chat_layer_constants.py        # Negation/unsure signal constants
│   ├── chat_layer_time_utils.py       # Time-of-day bucketing
│   ├── chat_layer_unsure.py           # Undecided response handling
│   ├── ds_service/
│   │   ├── predict/
│   │   │   ├── predict.py             # Prediction pipeline entry point
│   │   │   └── predict_utils.py       # Model loading, filtering, scoring
│   │   ├── preprocessing/
│   │   │   ├── preprocessing.py       # Feature engineering
│   │   │   └── preprocessing_utils.py # Encoding helpers (trend, intensity, time)
│   │   ├── models/
│   │   │   └── food_safety_model.pkl  # Trained XGBoost model
│   │   └── utils/
│   │       └── chat_layer_ds_utils.py # Glucose trend analysis
│   └── data injection/                # Standalone scripts to seed the DB from CSV
├── ds_insights_and_utils/
│   ├── generate_synthetic_data.py     # Generates 50K labeled training samples via risk oracle
│   ├── train_model.py                 # Trains XGBoost with 5-fold CV, saves food_safety_model.pkl
│   └── evaluate_baselines.py          # Compares XGBoost vs random guesser vs static heuristic
├── frontend/
│   └── src/
│       ├── App.jsx                    # Root component + routing
│       └── components/                # Auth, Dashboard, Profile, Charts, FoodLog
├── README.md
├── MODEL_README.md                    # Full data science write-up (math, pipeline, decisions)
├── CHAT_LAYER_README.md
├── FOOD_LOG_README.md
└── GLUCOSE_LEVELS_README.md
```

---

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and expects the backend at `http://localhost:8000`.

---

## API Endpoints

All endpoints except `/register` and `/token` require a `Authorization: Bearer <token>` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Create a new user account |
| POST | `/token` | Login and receive a JWT |
| GET | `/status` | Dashboard data (glucose, pregnancy info, profile) |
| POST | `/analyze_craving` | Submit a craving message, get a food recommendation |
| POST | `/clear_chat` | Reset conversation follow-up state for the current user |
| GET | `/glucose/trends` | Glucose readings over a given time range |
| POST | `/feedback` | Log user thumbs up/down on a food suggestion |
| GET | `/food_logs/today` | All food log entries for today |
| GET | `/food_logs/today/latest` | The most recent food log entry for today |
| POST | `/food_logs` | Add a new food log entry |
| PUT | `/update_profile` | Update user profile fields |
| DELETE | `/delete_account` | Permanently delete user and all associated data |

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python, FastAPI, SQLModel, SQLite |
| NLP | SpaCy (`en_core_web_sm`), PhraseMatcher |
| ML / Data | XGBoost, scikit-learn, Pandas, NumPy, joblib |
| Auth | JWT (`python-jose`), bcrypt (`passlib`) |
| Frontend | React, Vite, Axios, Recharts, Lucide Icons |

---

## Data Science and Recommendation System

The model was trained on **50,000 synthetically generated scenarios** labeled by a rule-based risk oracle that simulates clinically-informed safety thresholds (carbs, sugar, GI, glucose level/trend, time of day, and pregnancy stage). An XGBoost binary classifier (`is_safe`) was then trained on these samples using an 80/20 split and validated with 5-fold stratified cross-validation.

Model performance was evaluated against two baselines: a random guesser and a static carb/sugar heuristic (the kind of rule a dietitian might give verbally). The XGBoost model outperforms both, particularly in cases where context matters — for example, the same food can be safe in the morning but risky at night or during a glucose spike.

Full write-up, including the math behind the oracle risk function, the XGBoost loss function and gradient boosting mechanics, worked examples, and prediction pipeline details can be found in [`MODEL_README.md`](MODEL_README.md).
