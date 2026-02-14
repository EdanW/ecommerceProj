"""
Wipes all rows from the glucose readings table.
Run this standalone to reset glucose data before a fresh CSV import.
"""

import sys
from pathlib import Path

# Allow imports from the backend package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, create_engine
from sqlalchemy import text

DB_PATH = "backend/database.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

def main():
    # Open a session, delete every glucose row, and commit
    with Session(engine) as session:
        session.exec(text("DELETE FROM glucosereading;"))
        session.commit()
        print("✅ Deleted all rows from glucose table.")

if __name__ == "__main__":
    main()
