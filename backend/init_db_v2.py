from backend.database import engine, Base
from backend import models

def init_db():
    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    init_db()
