# Chat Layer Handling — Technical Documentation

## Overview

The chat layer is the NLP pipeline that converts a user's free-text food craving into a structured JSON payload. It powers the **Nouri** Gestational Diabetes Craving Assistant.

The pipeline handles:
- Extracting foods, categories, meal types, and intensity from natural language
- Negation-aware parsing ("I want pizza but not pepperoni")
- Follow-up conversations when required fields are missing
- "Unsure" detection ("I don't know", "surprise me")
- Off-topic rejection (non-food messages)

---

## High-Level Flow

```
User message
    │
    ▼
AIEngine.extract_to_json()
    │
    ├── Pending follow-up? → _handle_follow_up()
    │
    └── First message → NLP Extraction
            │
            ├── Food extractor
            ├── Category extractor
            ├── Meal type extractor
            └── Intensity extractor
            │
            ▼
        Completeness validation
            │
    ┌───────────────┬───────────────┐
    │               │               │
Incomplete      Off-topic        Complete
→ Follow-up     → Reject         → Return JSON
```

---

## File Structure

| File | Purpose |
|------|---------|
| `chat_layer_handling.py` | Main engine — stateful extraction, follow-ups, orchestration |
| `chat_layer_extractors.py` | Food/category/meal/intensity extraction with negation |
| `chat_layer_nlp.py` | SpaCy model + PhraseMatcher initialization |
| `chat_layer_negation.py` | Dependency-based negation detection + exclusion phrases |
| `chat_layer_constants.py` | All constants: negation tokens, food keywords, unsure phrases |
| `chat_layer_time_utils.py` | Time-of-day bucketing and meal type → time mapping |
| `chat_layer_unsure.py` | "I don't know" / "surprise me" detection |
| `chat_layer_food_database.py` | 700+ food entries with nutrition, categories, meal type |
| `main.py` | FastAPI endpoint + response message generation |

---

## Core Component — `AIEngine`

Located in `chat_layer_handling.py`.

### Entry Method

```python
extract_to_json(
    user_message,
    glucose_level,
    glucose_history,
    pregnancy_week,
    user_id
)
```

### Responsibilities

1. Clean expired pending states (TTL = 600 seconds)
2. Route follow-up replies to `_handle_follow_up()`
3. Detect "unsure" messages
4. Run NLP extraction
5. Validate completeness
6. Return structured JSON

---

## NLP Extraction Pipeline

All extraction runs through SpaCy (`en_core_web_sm`) and PhraseMatcher.

### 1) Food Extraction

- Matches against 700+ food database keys
- Longest-span match wins  
  - `"chocolate milkshake"` beats `"chocolate"` + `"milkshake"`
- Classifies foods as:
  - `wanted_foods`
  - `excluded_foods`

### 2) Category Extraction

Matches taste/texture categories such as:

- sweet, salty, savory, spicy
- creamy, crunchy
- hot, cold
- hearty, rich

Also:

- Infers categories from matched foods
- Explicit mentions override inferred conflicts
- Produces:
  - `wanted_categories`
  - `excluded_categories`

### 3) Meal Type Extraction

Recognizes:

- breakfast, lunch, dinner, snack, dessert

Fallback:

- If no meal type found, uses the first matched food’s `meal_type`.

### 4) Intensity Extraction

Detects craving intensity:

High:
- "dying for"
- "really craving"

Low:
- "maybe"
- "light"

Default:
- `medium`

---

## Negation Handling

Located in `chat_layer_negation.py`.

### Layer 1 — Dependency-Based Negation

- Uses SpaCy dependency parsing
- Detects: `not`, `no`, `never`, `n't`
- Traverses negation scope in the dependency tree
- Stops at punctuation (scope breaker)

Example:

```
"I want pizza but not pepperoni"
→ pizza = wanted
→ pepperoni = excluded
```

### Layer 2 — Phrase-Based Exclusions

Detects idiomatic patterns such as:

- "don't want"
- "sick of"
- "allergic to"
- "no more"

Any food inside detected spans is marked excluded.

---

## Completeness Validation

After extraction:

| Condition | Action |
|------------|--------|
| No foods AND no categories | Ask clarification |
| Only exclusions present | Ask "What would you like instead?" |
| Not food-related | Reject message |
| Categories but no meal type | Ask snack vs meal |
| Sufficient info | Return structured JSON |

---

## Follow-Up State Management

Partial extractions are stored in:

```python
pending_extractions[user_id]
```

- TTL: 600 seconds
- Only missing fields are filled in follow-up
- Exclusions are preserved and merged correctly

This enables multi-turn interactions without database persistence.

---

## Unsure Detection

Located in `chat_layer_unsure.py`.

Detects phrases such as:

- "I don't know"
- "anything"
- "whatever"
- "surprise me"

Returns a neutral structured extraction instead of triggering follow-up.

---

## Food Database

Located in `chat_layer_food_database.py`.

Each entry contains:

```python
{
    "id": 42,
    "categories": ["savory", "hot", "hearty"],
    "meal_type": "dinner",
    "glycemic_index": 55,
    "carbs": 30,
    "sugar": 5
}
```

Used for:

- PhraseMatcher patterns
- Category inference
- Meal type fallback

---

## Output Format

The Chat Layer returns:

```json
{
  "craving": {
    "foods": [],
    "categories": [],
    "excluded_foods": [],
    "excluded_categories": [],
    "time_of_day": "",
    "meal_type": "",
    "intensity": "medium"
  },
  "glucose_level": 0,
  "glucose_avg": 0,
  "glucose_trend": "",
  "pregnancy_week": 0
}
```

It extracts and structures user intent.  
It does not rank, score, or recommend foods.

---

## Design Principles

- Deterministic rule-based extraction
- Two-layer negation system
- Longest-span match resolution
- Explicit user intent overrides inferred signals
- Short-lived stateful follow-up logic