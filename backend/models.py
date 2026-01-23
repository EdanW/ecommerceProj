from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str

    # New Fields
    first_name: Optional[str] = None  # Added
    last_name: Optional[str] = None  # Added
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    pregnancy_start_date: Optional[str] = None
    medical_notes: Optional[str] = None

class GlucoseLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    level: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Add this class to your existing models.py
class DailyHabit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    water_glasses: int = 0
    movement_minutes: int = 0
    sleep_hours: float = 0.0