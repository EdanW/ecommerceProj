# Food Log Feature

## Overview

The Food Log feature allows authenticated users to record daily meals — capturing the time and an optional description. The most recent entry for the current day is always displayed beneath the form, giving users a quick snapshot of their latest logged meal.

---

## Architecture at a Glance

```
User interaction (React)
  │
  ▼
FoodLog component  ──POST /food_logs──►  FastAPI backend  ──► SQLite (foodlog table)
  │                                            │
  ◄──GET /food_logs/today/latest───────────────┘
```

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

- Queries entries where `created_date` matches today's date, ordered by `meal_time` descending, limited to 1.
- Returns `{ "entry": { ... } }` or `{ "entry": null }` if nothing has been logged yet.

#### `GET /food_logs/today`

Returns all food log entries for today, ordered by `meal_time` ascending.

- Response: `{ "entries": [ ... ] }`

#### `POST /food_logs`

Creates a new food log entry for the authenticated user.

- **Request body:** `{ "meal_time": "HH:MM", "note": "optional text" }`
- **Validation:**
  - `meal_time` is required and must match the `HH:MM` format.
  - `note` is optional; if provided, it is trimmed and must not exceed 200 characters.
- `created_date` is set automatically to today's date.
- `user_id` is set from the authenticated user's token.
- Response: `{ "entry": { "id", "meal_time", "note", "created_date" } }`

### Data Injection Scripts (`backend/data injection/`)

These scripts are used to seed or reset test data in the database:

| Script                | Purpose                                                         |
|-----------------------|-----------------------------------------------------------------|
| `load_foodlog_csv.py` | Reads `backend/foodlog.csv`, creates a placeholder user if needed, and inserts all rows into the `foodlog` table. Validates `meal_time` and `created_date` formats. |
| `reset_foodlog.py`    | Deletes all rows from the `foodlog` table (useful for a clean slate). |

**CSV format** (`backend/foodlog.csv`):
```
meal_time,note,created_date
08:00,Oatmeal with berries,2026-01-19
```

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

#### Lifecycle & Data Flow

1. **On mount** — a `useEffect` hook calls `GET /food_logs/today/latest` and populates `latestEntry`.
2. **User fills form** — picks a meal time (HTML5 time picker, 24-hour format) and optionally writes a note. A live character counter shows remaining characters (out of 200).
3. **Submit** — the `submitLog` handler:
   - Validates that `mealTime` is set and `note` is within limit.
   - Sends `POST /food_logs` with the JWT token.
   - On success: clears the form and calls `refreshLatest()` to re-fetch and display the newly created entry.
4. **Display** — beneath the form, a card shows the latest entry (meal time, date, and note) or a "No meals logged yet today" message.

#### Navigation

Accessible from the bottom navigation bar via the **ScrollText** icon. Clicking it sets the app's `view` state to `'foodlog'`, which conditionally renders `<FoodLog token={token} />` in `App.jsx`.

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

### How the simulated data works

1. A hand-crafted CSV file (`backend/foodlog.csv`) contains sample meal entries with realistic times, descriptions, and dates. For example: `08:00,Oatmeal with berries,2026-01-19`.
2. The injection script (`backend/data injection/load_foodlog_csv.py`) reads this CSV, creates a **placeholder user** in the database if one doesn't exist, wipes any previous entries for that user, and inserts the CSV rows into the `foodlog` table.
3. The reset script (`backend/data injection/reset_foodlog.py`) can clear the table entirely for a fresh start.

This approach lets us demonstrate the full feature — form submission, API calls, database queries, and UI rendering — without requiring actual daily user input during development. The `POST /food_logs` endpoint does work with real user input through the frontend form, but the pre-loaded historical data is all script-generated.

### Why simulated data

- **Rapid development** — allows building and testing the entire stack without waiting for real usage.
- **Consistent demos** — the same CSV can be reloaded for repeatable presentations and grading.
- **Schema validation** — the injection scripts validate formats (`HH:MM` for time, `YYYY-MM-DD` for date), which served as an early test of the data model.

---

## Future: Real Data Integration

The Food Log feature is already the closest to "real" data — users can manually submit entries through the frontend form, and those are stored as genuine records. To make the feature fully production-ready, the following enhancements would complete the picture:

### 1. Richer manual input (low effort)

The current form captures meal time and a text note. This could be extended to include:

- **Meal type dropdown** — breakfast, lunch, dinner, snack — stored as a new `tag` column on the `FoodLog` model.
- **Calorie / macros fields** — optional numeric inputs for carbs, protein, fat, and total calories.
- **Photo upload** — allow users to snap or upload a meal photo, stored as a file path or Base64 string (similar to the existing profile picture implementation).

Backend change: add columns to the `FoodLog` model and update the `POST /food_logs` endpoint to accept the new fields.

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

- A new backend endpoint (e.g., `GET /food_lookup?query=...`) would proxy requests to the external API and return standardized results.
- The frontend form would gain a search bar that auto-fills the note and nutritional fields based on the selected food item.
- No hardware required — just a camera for barcode scanning (using a JS library like `quagga2` or `html5-qrcode`).

### 3. Wearable / health app sync (higher effort)

For users who already track meals in apps like MyFitnessPal or Apple Health:

- Implement an **OAuth-based sync** with the third-party API.
- A scheduled backend job (or user-triggered sync button) would pull recent meal entries and insert them as `FoodLog` rows with `source = "myfitnesspal"` (adding a `source` column, similar to the `GlucoseReading` model).
- This turns the food log from a manual diary into an automatic aggregator.

### What stays the same

The core architecture — the `FoodLog` database model, the REST endpoints, and the React component — would remain unchanged. Each enhancement above simply feeds data into the same `POST /food_logs` pipeline, meaning the existing frontend display, validation logic, and JWT authentication all continue to work as-is.

---

## Key Design Decisions

- **Single latest entry display** — keeps the UI minimal and focused rather than showing a scrollable list.
- **Dual validation** — meal time format and note length are validated on both frontend (HTML5 attributes + JS checks) and backend (explicit format and length checks).
- **Automatic date** — `created_date` is always set server-side to prevent client-side date spoofing.
- **JWT authentication** — every request carries the user's Bearer token; the backend extracts `user_id` from the token, ensuring entries are always tied to the correct user.
