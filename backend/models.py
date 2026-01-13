from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    pregnancy_week: int = 28  # Default based on Ellie's story [cite: 2]

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