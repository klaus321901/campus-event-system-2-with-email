"""
Promote all staging events to the frontend.
Run this after scraping when you're happy with the new events:

    python publish_staging.py

To also delete old events (id < threshold), run:
    python publish_staging.py --delete-old
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal
from backend import models

db = SessionLocal()

try:
    # Count staging vs published
    staging = db.query(models.Event).filter(models.Event.is_published == False).count()
    live = db.query(models.Event).filter(models.Event.is_published == True).count()
    print(f"\n📊 Current state: {live} LIVE events, {staging} STAGING events")

    if staging == 0:
        print("✅ No staging events to publish.")
    else:
        confirm = input(f"\nPublish all {staging} staging events to frontend? (y/n): ").strip().lower()
        if confirm == 'y':
            updated = db.query(models.Event).filter(
                models.Event.is_published == False
            ).update({"is_published": True})
            db.commit()
            print(f"✅ Published {updated} events. Refresh localhost:8000 to see them.")
        else:
            print("Cancelled.")

    # Optional: delete old events
    if '--delete-old' in sys.argv:
        # Delete all events that were published before the current staging batch
        # i.e., events with lower IDs (old scrape)
        all_events = db.query(models.Event).order_by(models.Event.id).all()
        if all_events:
            latest_id = max(e.id for e in all_events)
            # Keep only events from this scrape session (created in last 24h)
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(hours=24)
            old = db.query(models.Event).filter(models.Event.created_at < cutoff).all()
            if old:
                confirm2 = input(f"\nDelete {len(old)} old events (created before 24h ago)? (y/n): ").strip().lower()
                if confirm2 == 'y':
                    for e in old:
                        db.delete(e)
                    db.commit()
                    print(f"🗑️  Deleted {len(old)} old events.")
            else:
                print("No old events to delete.")

finally:
    db.close()
