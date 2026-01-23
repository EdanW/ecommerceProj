from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select
from pydantic import BaseModel
from .models import User, GlucoseLog
from .auth import get_password_hash, verify_password, create_access_token, get_current_user
from .simulator import get_current_glucose_level
from .ai_engine import engine as ai_engine
from .models import DailyHabit
from .models import GlucoseLog
import random
from datetime import datetime, timedelta

# database:
# Database Setup
sqlite_file_name = "backend/database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine_db = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine_db)


app = FastAPI()

# Allow CORS for the separate frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change to specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# --- Pydantic Models for Requests ---
class LoginRequest(BaseModel):
    username: str
    password: str


class CravingRequest(BaseModel):
    food_name: str


# --- Routes ---

@app.post("/register")
def register(user: LoginRequest):
    with Session(engine_db) as session:
        existing_user = session.exec(select(User).where(User.username == user.username)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        hashed_pw = get_password_hash(user.password)
        new_user = User(username=user.username, hashed_password=hashed_pw)
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
    # Combines User Data + Simulated Glucose
    glucose_data = get_current_glucose_level()
    return {
        "user": current_user.username,
        "week": current_user.pregnancy_week,
        "glucose": glucose_data,
        "streak": 3,  # Mocked streak [cite: 43]
        "wellness_message": "You're doing wonderfully" if glucose_data['level'] < 130 else "Small steps, big impact"
    }


@app.post("/analyze_craving")
def check_craving(request: CravingRequest, current_user: User = Depends(get_current_user)):
    # 1. Get current physical state
    glucose_data = get_current_glucose_level()

    # 2. Ask AI Engine
    ai_response = ai_engine.analyze_craving(
        craving_text=request.food_name,
        current_glucose=glucose_data['level'],
        week=current_user.pregnancy_week
    )
    return ai_response

class HabitUpdate(BaseModel):
    habit_type: str # 'water', 'movement', 'sleep'
    value: int


@app.post("/log_habit")
def log_habit(update: HabitUpdate, current_user: User = Depends(get_current_user)):
    today = datetime.now().strftime("%Y-%m-%d")
    with Session(engine_db) as session:
        # Find today's entry or create one
        statement = select(DailyHabit).where(
            DailyHabit.user_id == current_user.id,
            DailyHabit.date == today
        )
        habit_log = session.exec(statement).first()

        if not habit_log:
            habit_log = DailyHabit(user_id=current_user.id, date=today)
            session.add(habit_log)

        # Update specific field
        if update.habit_type == 'water':
            habit_log.water_glasses += update.value
        elif update.habit_type == 'movement':
            habit_log.movement_minutes += update.value

        session.commit()
        session.refresh(habit_log)
        return habit_log


@app.post("/ingest_data")
def ingest_external_data(data: dict, current_user: User = Depends(get_current_user)):
    """
    Simulates fetching data from Google Health API.
    In a real app, 'data' would contain the OAuth token.
    Here, we just generate 30 days of mock history for the user.
    """
    if data.get('source') != 'google_health':
        raise HTTPException(status_code=400, detail="Unsupported source")

    with Session(engine_db) as session:
        # Generate 30 mock entries
        for i in range(30):
            date = datetime.now() - timedelta(days=i)
            # Create a mock reading
            log = GlucoseLog(
                user_id=current_user.id,
                level=random.randint(75, 150),
                timestamp=date
            )
            session.add(log)
        session.commit()

    return {"status": "success", "imported_count": 30}