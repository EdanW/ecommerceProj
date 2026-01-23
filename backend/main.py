from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select
from pydantic import BaseModel
from typing import Optional
from .models import User, GlucoseLog, DailyHabit
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


# --- Updated Request Models ---
class RegisterRequest(BaseModel):
    username: str
    password: str
    first_name: Optional[str] = None  # Added
    last_name: Optional[str] = None  # Added
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    pregnancy_start_date: Optional[str] = None
    medical_notes: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class CravingRequest(BaseModel):
    food_name: str


# --- API Routes ---

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
            first_name=user_data.first_name,  # Save Name
            last_name=user_data.last_name,  # Save Surname
            email=user_data.email,
            phone=user_data.phone,
            age=user_data.age,
            height=user_data.height,
            weight=user_data.weight,
            pregnancy_start_date=user_data.pregnancy_start_date,
            medical_notes=user_data.medical_notes
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
    return {
        "user": current_user.username,  # Keep for internal logic if needed
        "week": 28,
        "glucose": glucose_data,
        "wellness_message": "You're doing wonderfully" if glucose_data['level'] < 130 else "Small steps, big impact",
        # THIS FIXES THE EMPTY PROFILE BUG:
        "profile": {
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "age": current_user.age,
            "height": current_user.height,
            "weight": current_user.weight,
            "pregnancy_start_date": current_user.pregnancy_start_date,
            "medical_notes": current_user.medical_notes
        }
    }


@app.put("/update_profile")
def update_profile(data: RegisterRequest, current_user: User = Depends(get_current_user)):
    with Session(engine_db) as session:
        user = session.get(User, current_user.id)

        # Update fields if provided (and not None)
        if data.first_name is not None: user.first_name = data.first_name
        if data.last_name is not None: user.last_name = data.last_name
        if data.email is not None: user.email = data.email
        if data.phone is not None: user.phone = data.phone
        if data.age is not None: user.age = data.age
        if data.height is not None: user.height = data.height
        if data.weight is not None: user.weight = data.weight
        if data.pregnancy_start_date is not None: user.pregnancy_start_date = data.pregnancy_start_date
        if data.medical_notes is not None: user.medical_notes = data.medical_notes

        session.add(user)
        session.commit()
        return {"message": "Updated"}


@app.post("/analyze_craving")
def check_craving(request: CravingRequest, current_user: User = Depends(get_current_user)):
    glucose_data = get_current_glucose_level()
    return ai_engine.analyze_craving(request.food_name, glucose_data['level'], 28)


@app.post("/log_habit")
def log_habit(data: dict, current_user: User = Depends(get_current_user)):
    return {"status": "ok"}