from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    pregnancy_start_date: Optional[str] = None
    medical_notes: Optional[str] = None
    profile_picture: Optional[str] = Field(default=None)  # New: Stores Base64 string


class GlucoseLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    level: int
    timestamp: str


class GlucoseReading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    timestamp_utc: datetime = Field(index=True, nullable=False)
    glucose_mg_dl: int = Field(nullable=False)
    tag: Optional[str] = None
    source: str = Field(default="simulated", nullable=False)


class DailyHabit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: str
    water_glasses: int = 0
    movement_minutes: int = 0
    sleep_hours: float = 0.0

class CravingFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    craving_input: str
    ai_suggestion: str
    is_liked: bool
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())