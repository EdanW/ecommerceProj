import csv
from datetime import datetime
from sqlmodel import Session, create_engine, select

from models import User, GlucoseReading

DB_PATH = "backend/database.db"
CSV_PATH = r"backend/glucose_trends_next_2_months.csv"
USERNAME = "hansis"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def parse_timestamp(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def main():
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == USERNAME)).first()
        if not user:
            raise SystemExit(f"User '{USERNAME}' not found.")

        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = 0
            for row in reader:
                reading = GlucoseReading(
                    user_id=user.id,
                    timestamp_utc=parse_timestamp(row["timestamp_utc"]),
                    glucose_mg_dl=int(row["glucose_mg_dl"]),
                    tag=row.get("tag") or None,
                    source=row.get("source") or "simulated",
                )
                session.add(reading)
                rows += 1

        session.commit()
        print(f"Inserted {rows} readings for user '{USERNAME}'.")


if __name__ == "__main__":
    main()
