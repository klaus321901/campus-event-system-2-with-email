import json
import os
from sqlalchemy.orm import Session
from backend.database import SessionLocal, engine
from backend import models
from ml.nlp_processor import parse_date_to_datetime

def sync_json_to_db():
    print("🔄 Starting Sync: JSON -> Database...")
    
    # Paths for different JSON files
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PROCESSED_FILE = os.path.join(BASE_DIR, "data", "processed_events.json")
    SCRAPED_FILE = os.path.join(BASE_DIR, "data", "scraped_data.json")
    
    db = SessionLocal()
    
    # Try to load processed data first (richer content)
    data = []
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r") as f:
            data = json.load(f)
            print(f"📄 Found {len(data)} events in processed_events.json")
    elif os.path.exists(SCRAPED_FILE):
        with open(SCRAPED_FILE, "r") as f:
            data = json.load(f)
            print(f"📄 Found {len(data)} events in scraped_data.json")
    else:
        print("❌ No JSON data files found.")
        return

    added_count = 0
    updated_count = 0
    skipped_count = 0

    for item in data:
        try:
            url = item.get("post_url")
            if not url: continue

            # Check for existing
            event = db.query(models.Event).filter(models.Event.source_url == url).first()
            
            # Extract fields
            extracted = item.get("extracted", {})
            title = extracted.get("title") or f"Event by {item.get('username')}"
            desc = extracted.get("description") or item.get("caption", "No description")
            date_str = extracted.get("event_date") or item.get("timestamp")
            venue = extracted.get("venue")
            time_str = extracted.get("event_time")
            category = extracted.get("category")
            reg_link = extracted.get("registration_link")
            
            # Get image path
            image_path = None
            if item.get("images") and len(item["images"]) > 0:
                image_path = item["images"][0].get("local_path")
            elif item.get("image_path"):
                image_path = item.get("image_path")

            # Parse date for reminders
            parsed_date = parse_date_to_datetime(date_str)

            if not event:
                # Create new
                event = models.Event(
                    title=title,
                    description=desc,
                    date_str=str(date_str),
                    event_date=parsed_date,
                    time=time_str,
                    venue=venue,
                    club_name=item.get("username"),
                    profile_pic=item.get("profile_pic_url"),
                    image_path=image_path,
                    source_url=url,
                    category=category,
                    registration_link=reg_link
                )
                db.add(event)
                added_count += 1
            else:
                # Update existing
                event.title = title
                event.description = desc
                event.date_str = str(date_str)
                event.event_date = parsed_date
                event.time = time_str
                event.venue = venue
                event.category = category
                event.registration_link = reg_link
                updated_count += 1
            
            db.commit() # Commit each one to avoid batch IntegrityErrors
        except Exception as e:
            db.rollback()
            print(f"⚠️ Skipped event {item.get('post_url')}: {e}")
            skipped_count += 1

    db.close()
    print(f"✅ Sync Finished: {added_count} added, {updated_count} updated, {skipped_count} skipped.")

if __name__ == "__main__":
    sync_json_to_db()
