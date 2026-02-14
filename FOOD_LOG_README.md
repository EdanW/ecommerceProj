# Food Log Feature

## Overview

The Food Log feature allows authenticated users to record daily meals — capturing the time and an optional description. The most recent entry for the current day is always displayed beneath the form, giving users a quick snapshot of their latest logged meal.

---

## Backend

### Database Model (`backend/models.py`)

The `FoodLog` table stores one row per meal entry:

| Column         | Type          | Description                                      |
|----------------|---------------|--------------------------------------------------|
| `id`           | Integer (PK)  | Auto-generated primary key                       |
| `user_id`      | Integer (FK)  | References `user.id` — links entry to its owner  |
| `meal_time`    | String        | Time of the meal in `"HH:MM"` format             |
| `note`         | String (opt.) | Free-text description, max 200 characters         |
| `created_date` | String        | ISO date (`YYYY-MM-DD`), defaults to today        |

### API Endpoints (`backend/main.py`)

All endpoints require a valid JWT Bearer token.

#### `GET /food_logs/today/latest`

Returns the most recent food log entry for the current user today.

#### `GET /food_logs/today`

Returns all food log entries for today, ordered by `meal_time` ascending.

#### `POST /food_logs`

Creates a new food log entry for the authenticated user.

### Data Injection Scripts (`backend/data injection/`)

These scripts are used to seed or reset test data in the database:

| Script                | Purpose                                                         |
|-----------------------|-----------------------------------------------------------------|
| `load_foodlog_csv.py` | Reads `backend/foodlog.csv`, creates a placeholder user if needed, and inserts all rows into the `foodlog` table. Validates `meal_time` and `created_date` formats. |
| `reset_foodlog.py`    | Deletes all rows from the `foodlog` table (useful for a clean slate). |

---

## Frontend

### Component: `FoodLog` (`frontend/src/components/HealthWidgets.jsx`)

A single React component that handles both input and display.

#### State

| State          | Purpose                                 |
|----------------|-----------------------------------------|
| `mealTime`     | Controlled value for the time input     |
| `note`         | Controlled value for the note textarea  |
| `latestEntry`  | The most recent entry fetched from API  |
| `loading`      | True while fetching the latest entry    |
| `saving`       | True while submitting a new entry       |
| `error`        | Error message string (if any)           |

---

## End-to-End Flow

```
1. User taps "Food Log" icon in bottom nav
2. FoodLog component mounts
3. useEffect fires  ──►  GET /food_logs/today/latest
4. Backend authenticates token, queries SQLite, returns latest entry
5. Component displays the entry (or "No meals logged yet")

6. User enters meal time + note, taps "Submit"
7. Frontend validates inputs
8. POST /food_logs  ──►  Backend validates, inserts row into SQLite
9. Backend returns the new entry
10. Frontend clears form, calls GET /food_logs/today/latest
11. Updated latest entry is displayed
```

---

## Current Data: Simulated via Scripts

**All food log data currently in the system is simulated.** There is no real user input being collected in production — the database is populated entirely by injection scripts that load pre-written CSV files.

---

## Future: Real Data Integration

The Food Log feature is already the closest to "real" data — users can manually submit entries through the frontend form, and those are stored as genuine records. To make the feature fully production-ready, the following enhancements would complete the picture:

### 1. Richer manual input (low effort)

The current form captures meal time and a text note. This could be extended to include:

- **Meal type dropdown** — breakfast, lunch, dinner, snack — stored as a new `tag` column on the `FoodLog` model.
- **Calorie / macros fields** — optional numeric inputs for carbs, protein, fat, and total calories.

### 2. Barcode / food database lookup (medium effort)

Integrate with a public food API such as [Open Food Facts](https://world.openfoodfacts.org/data) or the USDA FoodData Central API:

```
User scans barcode or searches food name
       │
       ▼
Frontend sends query  ──►  Backend proxies to food API
       │                          │
       ◄──── returns nutritional info (calories, carbs, etc.)
       │
       ▼
Auto-fills the food log form  ──►  POST /food_logs
```

### 3. Wearable / health app sync (higher effort)

For users who already track meals in other apps:

- A scheduled backend job (or user-triggered sync button) would pull recent meal entries and insert them as `FoodLog` rows with `source = "myfoodapp"` (requires adding a `source` column).
- This turns the food log from a manual diary into an automatic aggregator.

### What stays the same

The core architecture — the `FoodLog` database model, the REST endpoints, and the React component — would remain unchanged. Each enhancement above simply feeds data into the same `POST /food_logs` pipeline, meaning the existing frontend display, validation logic, and JWT authentication all continue to work as-is.
