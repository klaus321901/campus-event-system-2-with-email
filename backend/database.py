from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Always load .env from the backend folder (works regardless of cwd)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./campus_events.sqlite3")
print("[DB] Database connection initialized")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    # check_same_thread is only needed for SQLite
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
