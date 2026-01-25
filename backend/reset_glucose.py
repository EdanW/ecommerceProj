from sqlmodel import Session, create_engine
from sqlalchemy import text

DB_PATH = "backend/database.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

def main():
    with Session(engine) as session:
        # If your table name is different, change it here:
        session.exec(text("DELETE FROM glucosereading;"))
        # If you used snake_case table name, try:
        # session.exec(text("DELETE FROM glucose_reading;"))

        session.commit()
        print("✅ Deleted all rows from glucose table.")

if __name__ == "__main__":
    main()