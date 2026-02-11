# Eat42 - Gestational Diabetes Craving Assistant

A web application that helps pregnant women with gestational diabetes find satisfying food alternatives that align with their glucose levels.

## Overview

Eat42 takes a user's food craving as free-text input, extracts structured information using NLP (SpaCy), and combines it with real-time glucose data and pregnancy context to recommend suitable food options through a scoring-based recommendation model.

## Architecture

### Backend (FastAPI + Python)

- **Chat Layer** - NLP pipeline that parses user cravings into structured JSON:
  - Negation-aware food and category extraction (SpaCy + PhraseMatcher)
  - Follow-up question handling for incomplete input
  - Unsure/undecided detection with context preservation
- **Recommendation Model** - Scores food candidates based on:
  - Craving match (foods, categories, exclusions)
  - Glucose level and trend analysis
  - Time of day and meal type
  - Pregnancy week
- **REST API** - User auth, glucose tracking, craving analysis, food logging
- **SQLite** - User profiles, glucose readings, craving feedback, food logs

### Frontend (React + Vite)

- Dashboard with glucose status and pregnancy tracker
- Chat interface for craving input
- Glucose trend charts (Recharts)

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
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

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Create new user |
| POST | `/token` | Login / get JWT |
| GET | `/status` | Dashboard data (glucose, pregnancy) |
| POST | `/analyze_craving` | Submit craving, get recommendation |
| POST | `/clear_chat` | Reset conversation state |
| GET | `/glucose/trends` | Glucose readings over time range |
| POST | `/feedback` | Log user feedback on suggestions |
| GET | `/food_logs/today` | Today's food log entries |
| POST | `/food_logs` | Add food log entry |
| PUT | `/update_profile` | Update user profile |
| DELETE | `/delete_account` | Delete user and all data |

## Tech Stack

- **Backend:** Python, FastAPI, SQLModel, SpaCy, Pandas
- **Frontend:** React, Vite, Axios, Recharts
- **Auth:** JWT (python-jose), bcrypt (passlib)
- **Database:** SQLite
