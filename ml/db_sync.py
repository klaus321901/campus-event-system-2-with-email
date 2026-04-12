import os
import json
import sqlite3
from datetime import datetime

# Configure Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "campus_events.db")
INPUT_FILE = os.path.join(BASE_DIR, "data", "processed_events.json")

def sync_to_db():
    """Move processed events from JSON to SQLite database."""
    if not os.path.exists(INPUT_FILE):
        print("[ERROR] No processed data found at", INPUT_FILE)
        return

    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure table exists (Auto-Fix for "no such table" error)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR,
            description TEXT,
            date VARCHAR,
            time VARCHAR,
            venue VARCHAR,
            club_name VARCHAR,
            profile_pic VARCHAR,
            image_path VARCHAR,
            source_url VARCHAR,
            category VARCHAR,
            registration_link VARCHAR,
            last_register_date VARCHAR,
            created_at DATETIME
        );
    """)
    conn.commit()

    with open(INPUT_FILE, "r") as f:
        events = json.load(f)

    print(f"[DB] Found {len(events)} events to sync. Updating database...")
    
    success_count = 0
    
    for event in events:
        details = event.get("extracted", {})
        if not details:
            continue
            
        # Check if event already exists (based on source_url)
        cursor.execute("SELECT id FROM events WHERE source_url = ?", (event["post_url"],))
        existing = cursor.fetchone()
        
        # Get first image local path if available
        image_path = None
        if event.get("images") and len(event["images"]) > 0:
            image_path = event["images"][0].get("local_path")
        elif event.get("image_path"): # Old format compatibility
            image_path = event.get("image_path")

        if existing:
            # Update existing event
            cursor.execute("""
                UPDATE events SET
                    title = ?,
                    description = ?,
                    date = ?,
                    time = ?,
                    venue = ?,
                    category = ?,
                    registration_link = ?,
                    last_register_date = ?,
                    image_path = ?
                WHERE source_url = ?
            """, (
                details.get("title"),
                details.get("description"),
                details.get("event_date"),
                details.get("event_time"),
                details.get("venue"),
                details.get("category"),
                details.get("registration_link"),
                details.get("last_register_date"),
                image_path,
                event["post_url"]
            ))
        else:
            # Insert new event
            cursor.execute("""
                INSERT INTO events (
                    title, description, date, time, venue, 
                    club_name, profile_pic, image_path, 
                    source_url, category, registration_link, 
                    last_register_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                details.get("title"),
                details.get("description"),
                details.get("event_date"),
                details.get("event_time"),
                details.get("venue"),
                event["username"],
                event.get("profile_pic_url"),
                image_path,
                event["post_url"],
                details.get("category"),
                details.get("registration_link"),
                details.get("last_register_date"),
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        success_count += 1

    conn.commit()
    conn.close()
    
    print(f"\n[SUCCESS] Sync complete! {success_count} events added/updated in the database.")

if __name__ == "__main__":
    sync_to_db()
