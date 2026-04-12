from database import engine, Base
from models import Event

def init_db():
    print("[DB] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created successfully!")

if __name__ == "__main__":
    init_db()
