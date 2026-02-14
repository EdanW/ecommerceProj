from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select, delete
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .models import User, GlucoseLog, GlucoseReading, DailyHabit, CravingFeedback, FoodLog
from .auth import get_password_hash, verify_password, create_access_token, get_current_user
from .simulator import get_current_glucose_level
from .chat_layer_handling import engine as chat_layer_engine

# Database Setup
sqlite_file_name = "backend/database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine_db = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine_db)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# --- Helpers ---
def calculate_pregnancy_data(start_date_str):
    if not start_date_str:
        return None

    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
        now = datetime.now()
        days_pregnant = (now - start).days
        weeks = days_pregnant // 7

        trimester = 1
        if weeks > 13: trimester = 2
        if weeks > 26: trimester = 3

        # Baby Size Logic with Emojis
        size = "a Poppy Seed 🌱"
        if weeks >= 40:
            size = "a Watermelon 🍉"
        elif weeks >= 36:
            size = "a Honeydew 🍈"
        elif weeks >= 32:
            size = "a Squash 🥒"
        elif weeks >= 28:
            size = "an Eggplant 🍆"
        elif weeks >= 24:
            size = "a Cantaloupe 🍈"
        elif weeks >= 20:
            size = "a Banana 🍌"
        elif weeks >= 16:
            size = "an Avocado 🥑"
        elif weeks >= 12:
            size = "a Plum 🍑"
        elif weeks >= 8:
            size = "a Raspberry 🍓"

        return {"week": weeks, "trimester": trimester, "size": size}
    except:
        return None
    
## Calculates the last N glucose readings for a user
def get_last_n_glucose_readings(n: int = 10) -> list[dict]:
    """Fetch the last N glucose readings from the database."""
    with Session(engine_db) as session:
        statement = (
            select(GlucoseReading)
            .order_by(desc(GlucoseReading.timestamp_utc))
            .limit(n)
        )
        readings = session.exec(statement).all()

    return [
        {
            "timestamp_utc": r.timestamp_utc.isoformat(),
            "glucose_mg_dl": r.glucose_mg_dl,
            "tag": r.tag,
        }
        for r in readings
    ]

def _generate_assistant_message(
    model_response: dict,
    craving_input: dict,
    glucose_level: int,
    glucose_status: str
) -> str:
    """Turn model output into a user-facing message."""
    food = model_response.get("food")
    another_option = model_response.get("another_option")

    requested_foods = [f.lower() for f in craving_input.get("foods", [])]

    # No recommendation from model
    if not food:
        return (
            "I couldn't find a great match right now. "
            "Could you try describing what you're in the mood for differently? 💜"
        )

    # Check if the model's top pick matches what the user asked for
    craving_approved = food.lower() in requested_foods if requested_foods else False

    if craving_approved:
        # Model approved the user's craving
        if glucose_status == "Elevated":
            message = (
                f"Your glucose is a bit elevated ({glucose_level} mg/dL), "
                f"but {food} can still work — just keep the portion in check! 🍽️"
            )
        elif glucose_status == "Low":
            message = (
                f"Your glucose is on the lower side ({glucose_level} mg/dL), "
                f"and {food} sounds like a great pick right now! 🎉"
            )
        else:
            message = (
                f"Your glucose looks good ({glucose_level} mg/dL) — "
                f"{food} sounds like a great choice! 🎉"
            )
    else:
        # Model suggested something different
        if glucose_status == "Elevated":
            message = (
                f"Your glucose is a bit elevated ({glucose_level} mg/dL), "
                f"so that might not be the best option right now. "
                f"A better alternative would be {food}!"
            )
        elif glucose_status == "Low":
            message = (
                f"Your glucose is on the lower side ({glucose_level} mg/dL). "
                f"I'd suggest going with {food} instead!"
            )
        else:
            message = (
                f"Your glucose looks good ({glucose_level} mg/dL)! "
                f"I'd recommend {food} — it's a great option for you right now."
            )

    if another_option:
        message += f"\nAnother option for you: {another_option}."

    message += " 💜"
    return message



# --- Models ---
class RegisterRequest(BaseModel):
    username: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    pregnancy_start_date: Optional[str] = None
    medical_notes: Optional[str] = None
    profile_picture: Optional[str] = None  # Base64 Image


class LoginRequest(BaseModel):
    username: str
    password: str


class CravingRequest(BaseModel):
    food_name: str

class FeedbackRequest(BaseModel):
    craving: str
    suggestion: str
    is_liked: bool

class FoodLogRequest(BaseModel):
    meal_time: str
    note: Optional[str] = None

# --- Routes ---

@app.post("/register")
def register(user_data: RegisterRequest):
    with Session(engine_db) as session:
        existing_user = session.exec(select(User).where(User.username == user_data.username)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        hashed_pw = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            hashed_password=hashed_pw,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            phone=user_data.phone,
            age=user_data.age,
            height=user_data.height,
            weight=user_data.weight,
            pregnancy_start_date=user_data.pregnancy_start_date,
            medical_notes=user_data.medical_notes,
            profile_picture=user_data.profile_picture
        )
        session.add(new_user)
        session.commit()
        return {"message": "User created"}


@app.post("/token")
def login(user: LoginRequest):
    with Session(engine_db) as session:
        db_user = session.exec(select(User).where(User.username == user.username)).first()
        if not db_user or not verify_password(user.password, db_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        access_token = create_access_token(data={"sub": db_user.username})
        return {"access_token": access_token, "token_type": "bearer"}


@app.get("/status")
def get_dashboard_data(current_user: User = Depends(get_current_user)):
    glucose_data = get_current_glucose_level()
    preg_data = calculate_pregnancy_data(current_user.pregnancy_start_date)

    # Decide what name to show (First Name OR Username)
    display_name = current_user.first_name if current_user.first_name else current_user.username

    return {
        "display_name": display_name,
        "username": current_user.username,
        "pregnancy_data": preg_data,  # Can be None if date missing
        "glucose": glucose_data,
        "wellness_message": "You're doing wonderfully" if glucose_data['level'] < 130 else "Small steps, big impact",
        "profile": {
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "age": current_user.age,
            "height": current_user.height,
            "weight": current_user.weight,
            "pregnancy_start_date": current_user.pregnancy_start_date,
            "medical_notes": current_user.medical_notes,
            "profile_picture": current_user.profile_picture
        }
    }


@app.get("/glucose/trends")
def get_glucose_trends(
    start: datetime,
    end: datetime,
    current_user: User = Depends(get_current_user)
):
    # Check date range validity
    if end < start:
        raise HTTPException(status_code=400, detail="End must be after start")

    with Session(engine_db) as session:
        # Compose a query for glucose readings within the date range
        statement = (
            select(GlucoseReading)
            .where(
                # Uncomment the line below to filter by user if needed
                # GlucoseReading.user_id == current_user.id,
                GlucoseReading.timestamp_utc >= start,
                GlucoseReading.timestamp_utc <= end
            )
            .order_by(GlucoseReading.timestamp_utc)
        )
        readings = session.exec(statement).all()  # Execute the query

    # Format and return the readings as a list of dicts (ISO format for timestamps)
    return {
        "readings": [
            {
                "timestamp_utc": r.timestamp_utc.isoformat(),
                "glucose_mg_dl": r.glucose_mg_dl,
                "tag": r.tag,
                "source": r.source
            }
            for r in readings
        ]
    }


@app.put("/update_profile")
def update_profile(data: RegisterRequest, current_user: User = Depends(get_current_user)):
    with Session(engine_db) as session:
        user = session.get(User, current_user.id)

        if data.first_name is not None: user.first_name = data.first_name
        if data.last_name is not None: user.last_name = data.last_name
        if data.email is not None: user.email = data.email
        if data.phone is not None: user.phone = data.phone
        if data.age is not None: user.age = data.age
        if data.height is not None: user.height = data.height
        if data.weight is not None: user.weight = data.weight
        if data.pregnancy_start_date is not None: user.pregnancy_start_date = data.pregnancy_start_date
        if data.medical_notes is not None: user.medical_notes = data.medical_notes
        if data.profile_picture is not None: user.profile_picture = data.profile_picture

        session.add(user)
        session.commit()
        return {"message": "Updated"}

@app.post("/feedback")
def log_feedback(data: FeedbackRequest, current_user: User = Depends(get_current_user)):
    with Session(engine_db) as session:
        feedback = CravingFeedback(
            user_id=current_user.id,
            craving_input=data.craving,
            ai_suggestion=data.suggestion,
            is_liked=data.is_liked
        )
        session.add(feedback)
        session.commit()
    return {"status": "recorded"}

@app.post("/analyze_craving")
def check_craving(request: CravingRequest, current_user: User = Depends(get_current_user)):
    glucose_data = get_current_glucose_level()
    glucose_history = get_last_n_glucose_readings(n=10)

    # Calculate current week or default to 28 if unknown
    week = 28
    preg_data = calculate_pregnancy_data(current_user.pregnancy_start_date)
    if preg_data:
        week = preg_data["week"]

    user_id = str(current_user.id)

    extraction = chat_layer_engine.extract_to_json(
        user_message=request.food_name,
        glucose_level=glucose_data["level"],
        glucose_history=glucose_history,
        pregnancy_week=week,
        user_id=user_id
    )

    # If incomplete, return follow-up question
    if not extraction.get("complete"):
        return extraction

    model_response = extraction.get("data", {})
    craving_input = extraction.get("craving_input", {})

    # Generate human-readable message from the model output
    assistant_message = _generate_assistant_message(
        model_response=model_response,
        craving_input=craving_input,
        glucose_level=glucose_data["level"],
        glucose_status=glucose_data["status"]
    )

    return {
        **extraction,
        "model_response": model_response,
        "assistant_message": assistant_message
    }



@app.post("/clear_chat")
def clear_chat(current_user: User = Depends(get_current_user)):
    user_id = str(current_user.id)
    chat_layer_engine.clear_pending(str(current_user.id))
    return {"message": "Chat cleared"}


@app.get("/food_logs/today")
def list_today_food_logs(current_user: User = Depends(get_current_user)):
    # Get today's date in ISO format
    today = datetime.now().date().isoformat()
    with Session(engine_db) as session:
        # Query all food logs for today (not filtered by user here)
        statement = (
            select(FoodLog)
            .where(
                # To filter logs by user, uncomment the following line:
                # FoodLog.user_id == current_user.id,
                FoodLog.created_date == today
            )
            .order_by(FoodLog.meal_time)
        )
        entries = session.exec(statement).all()
    # Return list of today's food log entries
    return {
        "entries": [
            {
                "id": entry.id,
                "meal_time": entry.meal_time,
                "note": entry.note,
                "created_date": entry.created_date
            }
            for entry in entries
        ]
    }


@app.get("/food_logs/today/latest")
def get_latest_food_log(current_user: User = Depends(get_current_user)):
    # Get today's date
    today = datetime.now().date().isoformat()
    with Session(engine_db) as session:
        # Get all entries for today (across users)
        all_entries_today = session.exec(
            select(FoodLog).where(FoodLog.created_date == today)
        ).all()
        # Try to fetch latest log for the current user
        statement = (
            select(FoodLog)
            .where(
                FoodLog.user_id == current_user.id,
                FoodLog.created_date == today
            )
            .order_by(desc(FoodLog.meal_time))
            .limit(1)
        )
        entry = session.exec(statement).first()
        # If no user log exists, get the latest entry for anyone
        if not entry and all_entries_today:
            fallback_entry = session.exec(
                select(FoodLog)
                .where(FoodLog.created_date == today)
                .order_by(desc(FoodLog.meal_time))
                .limit(1)
            ).first()
            entry = fallback_entry

    if not entry:
        return {"entry": None}

    # Return most recent food log for today
    return {
        "entry": {
            "id": entry.id,
            "meal_time": entry.meal_time,
            "note": entry.note,
            "created_date": entry.created_date
        }
    }


@app.post("/food_logs")
def create_food_log(data: FoodLogRequest, current_user: User = Depends(get_current_user)):
    # Validate required meal_time field
    if not data.meal_time:
        raise HTTPException(status_code=400, detail="Meal time is required")

    # Validate time format (must be HH:MM)
    try:
        datetime.strptime(data.meal_time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Meal time must be HH:MM")

    # Clean and validate note length
    note = data.note.strip() if data.note else None
    if note and len(note) > 200:
        raise HTTPException(status_code=400, detail="Note must be 200 characters or less")

    # Create new food log entry for user
    new_entry = FoodLog(
        user_id=current_user.id,
        meal_time=data.meal_time,
        note=note,
        created_date=datetime.now().date().isoformat()
    )

    # Save to database
    with Session(engine_db) as session:
        session.add(new_entry)
        session.commit()
        session.refresh(new_entry)

    # Return the newly created entry
    return {
        "entry": {
            "id": new_entry.id,
            "meal_time": new_entry.meal_time,
            "note": new_entry.note,
            "created_date": new_entry.created_date
        }
    }


@app.post("/log_habit")
def log_habit(data: dict, current_user: User = Depends(get_current_user)):
    return {"status": "ok"}


@app.delete("/delete_account")
def delete_account(current_user: User = Depends(get_current_user)):
    with Session(engine_db) as session:
        session.exec(delete(GlucoseLog).where(GlucoseLog.user_id == current_user.id))
        session.exec(delete(GlucoseReading).where(GlucoseReading.user_id == current_user.id))
        session.exec(delete(DailyHabit).where(DailyHabit.user_id == current_user.id))
        session.exec(delete(CravingFeedback).where(CravingFeedback.user_id == current_user.id))
        session.exec(delete(FoodLog).where(FoodLog.user_id == current_user.id))

        session.delete(current_user)
        session.commit()

    return {"message": "Account deleted"}