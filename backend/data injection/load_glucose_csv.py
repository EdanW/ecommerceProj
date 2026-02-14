"""
Imports glucose readings from a CSV into the database for a specific user.
Flow: look up user -> delete their old readings -> parse CSV -> bulk insert -> commit.
"""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from the backend package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, create_engine, select
from sqlalchemy import delete

from models import User, GlucoseReading

DB_PATH = "backend/database.db"
CSV_PATH = r"backend/glucose_trends_from_today_jerusalem_60d.csv"
USERNAME = "hansis"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

def parse_timestamp_utc_naive(value: str) -> datetime:
    """Convert any ISO-8601 timestamp (with or without tz) to naive UTC datetime."""
    value = value.strip()
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt_utc

def main():
    with Session(engine) as session:
        # 1. Resolve the target user (must already exist)
        user = session.exec(select(User).where(User.username == USERNAME)).first()
        if not user:
            raise SystemExit(f"User '{USERNAME}' not found.")

        # 2. Wipe this user's old glucose readings so we start fresh
        session.exec(delete(GlucoseReading).where(GlucoseReading.user_id == user.id))
        session.commit()

        # 3. Read CSV rows and insert each as a new GlucoseReading
        rows = 0
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.add(
                    GlucoseReading(
                        user_id=user.id,
                        timestamp_utc=parse_timestamp_utc_naive(row["timestamp_utc"]),
                        glucose_mg_dl=int(row["glucose_mg_dl"]),
                        tag=row.get("tag") or None,
                        source=row.get("source") or "simulated",
                    )
                )
                rows += 1

        session.commit()
        print(f"✅ Inserted {rows} clean readings for user '{USERNAME}'")

if __name__ == "__main__":
    main()
