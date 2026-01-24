from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select, delete
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .models import User, GlucoseLog, DailyHabit, CravingFeedback
from .auth import get_password_hash, verify_password, create_access_token, get_current_user
from .simulator import get_current_glucose_level
from .ai_engine import engine as ai_engine

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
    # Calculate current week or default to 28 if unknown
    week = 28
    preg_data = calculate_pregnancy_data(current_user.pregnancy_start_date)
    if preg_data:
        week = preg_data['week']

    return ai_engine.analyze_craving(request.food_name, glucose_data['level'], week)


@app.post("/log_habit")
def log_habit(data: dict, current_user: User = Depends(get_current_user)):
    return {"status": "ok"}


@app.delete("/delete_account")
def delete_account(current_user: User = Depends(get_current_user)):
    with Session(engine_db) as session:
        session.exec(delete(GlucoseLog).where(GlucoseLog.user_id == current_user.id))
        session.exec(delete(DailyHabit).where(DailyHabit.user_id == current_user.id))
        session.exec(delete(CravingFeedback).where(CravingFeedback.user_id == current_user.id))

        session.delete(current_user)
        session.commit()

    return {"message": "Account deleted"}