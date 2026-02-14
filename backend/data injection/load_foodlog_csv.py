import csv
import sys
from datetime import datetime
from pathlib import Path

# Add backend/ to sys.path so we can import models
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, create_engine, select
from sqlalchemy import delete

from models import User, FoodLog

DB_PATH = "backend/database.db"
CSV_PATH = r"backend/foodlog.csv"
USERNAME = "placeholder"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

def parse_meal_time(value: str) -> str:
    value = value.strip()
    datetime.strptime(value, "%H:%M")
    return value

def parse_created_date(value: str) -> str:
    value = value.strip()
    if not value:
        return datetime.now().date().isoformat()
    datetime.strptime(value, "%Y-%m-%d")
    return value

def ensure_placeholder_user(session: Session) -> User:
    user = session.exec(select(User).where(User.username == USERNAME)).first()
    if user:
        return user

    user = User(
        username=USERNAME,
        hashed_password="placeholder",
        first_name="placeholder",
        last_name="placeholder",
        email="placeholder@example.com",
        phone="0000000000",
        medical_notes="placeholder"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def main():
    with Session(engine) as session:
        user = ensure_placeholder_user(session)

        session.exec(delete(FoodLog).where(FoodLog.user_id == user.id))
        session.commit()

        rows = 0
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                meal_time = parse_meal_time(row["meal_time"])
                created_date = parse_created_date(row.get("created_date", ""))
                note = (row.get("note") or "").strip() or None

                session.add(
                    FoodLog(
                        user_id=user.id,
                        meal_time=meal_time,
                        note=note,
                        created_date=created_date
                    )
                )
                rows += 1

        session.commit()
        print(f"Inserted {rows} food logs for user '{USERNAME}'.")

if __name__ == "__main__":
    main()
