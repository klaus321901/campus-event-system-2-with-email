
import sqlite3
from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.orm import sessionmaker
import os
import sys
from dotenv import load_dotenv

# Setup path to import backend modules
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from backend import models

# Load environment variables
load_dotenv(os.path.join(root_dir, 'backend', '.env'))

# DB URLs
SQLITE_DB_URL = f"sqlite:///{os.path.join(root_dir, 'campus_events.db')}"
# Fallback to default if .env load failed for some reason
POSTGRES_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:3366@localhost:5432/campus_events")

def migrate():
    print("🚀 Starting Migration from SQLite to PostgreSQL...")
    
    # 1. Connect to SQLite (Source)
    sqlite_engine = create_engine(SQLITE_DB_URL)
    
    # 2. Connect to PostgreSQL (Target)
    try:
        pg_engine = create_engine(POSTGRES_DB_URL)
        # Test connection
        conn = pg_engine.connect()
        conn.close()
    except Exception as e:
        print(f"❌ Could not connect to PostgreSQL: {e}")
        print("💡 Make sure you created the database 'campus_events' in PGAdmin first!")
        return

    # 3. Create tables in PostgreSQL if they don't exist
    print("🛠️ Creating tables in PostgreSQL...")
    models.Base.metadata.create_all(bind=pg_engine)
    
    # 4. Data Transfer
    PGSession = sessionmaker(bind=pg_engine)
    pg_session = PGSession()
    
    try:
        # Transfer Users
        print("👤 Migrating Users...")
        with sqlite_engine.connect() as conn:
            users = conn.execute(select("*").select_from(Table("users", MetaData(), autoload_with=sqlite_engine))).fetchall()
            for u in users:
                # Check if user exists
                exists = pg_session.query(models.User).filter(models.User.email == u.email).first()
                if not exists:
                    new_user = models.User(
                        id=u.id,
                        username=getattr(u, 'username', u.email),
                        email=u.email,
                        hashed_password=u.hashed_password,
                        is_active=getattr(u, 'is_active', True)
                    )
                    pg_session.add(new_user)
        pg_session.commit()

        # Transfer Events
        print("🗓️ Migrating Events...")
        with sqlite_engine.connect() as conn:
            events = conn.execute(select("*").select_from(Table("events", MetaData(), autoload_with=sqlite_engine))).fetchall()
            for e in events:
                # Check if event exists (using source_url as unique key)
                exists = pg_session.query(models.Event).filter(models.Event.source_url == e.source_url).first()
                if not exists:
                    new_event = models.Event(
                        title=e.title,
                        description=e.description,
                        club_name=e.club_name,
                        profile_pic=e.profile_pic,
                        source_url=e.source_url,
                        image_path=e.image_path,
                        registration_link=e.registration_link,
                        date_str=e.date_str,
                        event_date=e.event_date,
                        venue=e.venue,
                        category=e.category
                    )
                    pg_session.add(new_event)
        pg_session.commit()

        # Transfer Feedback
        print("💬 Migrating Feedback...")
        try:
            with sqlite_engine.connect() as conn:
                feedback = conn.execute(select("*").select_from(Table("feedback", MetaData(), autoload_with=sqlite_engine))).fetchall()
                for f in feedback:
                    new_f = models.Feedback(
                        user_id=f.user_id,
                        event_id=f.event_id,
                        rating=f.rating,
                        comment=f.comment
                    )
                    pg_session.add(new_f)
            pg_session.commit()
        except:
             print("⚠️ Feedback migration skipped (table might be empty or missing).")

        print("\n✅ Migration Successful! Your data is now in PostgreSQL.")
        print("You can now safely submit or run the backend.")

    except Exception as ex:
        pg_session.rollback()
        print(f"❌ Error during migration: {ex}")
    finally:
        pg_session.close()

if __name__ == "__main__":
    migrate()
