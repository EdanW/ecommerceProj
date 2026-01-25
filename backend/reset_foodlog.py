from sqlmodel import Session, create_engine, select
from sqlalchemy import text

from models import User

DB_PATH = "backend/database.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
USERNAME = "placeholder"

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
        ensure_placeholder_user(session)
        session.exec(text("DELETE FROM foodlog;"))
        session.commit()
        print("Deleted all rows from foodlog table.")

if __name__ == "__main__":
    main()
