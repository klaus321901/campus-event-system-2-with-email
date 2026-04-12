import os
import sys
from sqlalchemy.orm import Session

# Add the project root to sys.path so we can import from backend
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from backend.database import SessionLocal
    from backend import models
except ImportError as e:
    print(f"[ERROR] Could not import backend modules: {e}")
    sys.exit(1)

def publish_scraped_events():
    """
    Finds all unpublished scraped events and marks them as published.
    """
    db: Session = SessionLocal()
    try:
        # Filter for unpublished events with 'instagram' source_type
        # .update() is more efficient than looping through each record
        updated_count = db.query(models.Event).filter(
            models.Event.source_type == "instagram",
            models.Event.is_published == False
        ).update({"is_published": True}, synchronize_session=False)
        
        db.commit()
        print(f"{updated_count} scraped events published successfully")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Transaction failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    publish_scraped_events()
