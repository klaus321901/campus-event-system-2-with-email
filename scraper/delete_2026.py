
import os
import sys
from datetime import datetime

# Setup path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from backend.database import SessionLocal
from backend import models

def delete_2026_events():
    db = SessionLocal()
    try:
        # Delete events where event_date is in 2026 or later
        # We assume any current "2026" events might be misidentified 2025 ones
        events_to_delete = db.query(models.Event).filter(
            models.Event.event_date >= datetime(2026, 1, 1)
        ).all()
        
        count = len(events_to_delete)
        for event in events_to_delete:
            db.delete(event)
        
        db.commit()
        print(f"🗑️ Deleted {count} events from 2026 to allow a fresh, accurate scrape.")
        
        # Also clean up duplicate events that might have been created due to logic errors
        # (though source_url is unique, so this is mostly a safety check)
    finally:
        db.close()

if __name__ == "__main__":
    delete_2026_events()
