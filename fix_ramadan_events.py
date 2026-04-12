
import sqlite3
import os

# Connect to the root database
DB_PATH = r"C:\Users\sanat\OneDrive\Desktop\campus_event_system\campus_events.db"

if not os.path.exists(DB_PATH):
    print(f"Error: {DB_PATH} not found.")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

keywords = ["ramadan", "iftar", "suhoor", "eid"]
# Case insensitive LIKE for SQLite
conditions = " OR ".join([f"description LIKE '%{k}%'" for k in keywords]) + \
             " OR " + " OR ".join([f"title LIKE '%{k}%'" for k in keywords])

query = f"SELECT id, title, description, category FROM events WHERE {conditions}"

print(f"Executing query: {query}")
cursor.execute(query)
rows = cursor.fetchall()

print(f"Found {len(rows)} potential Ramadan events.")

updated_count = 0
for row in rows:
    event_id, title, description, category = row
    
    # We want to force them to Cultural
    new_category = "Cultural"
    
    # Fix Title
    new_title = title
    if "Technical Event" in title:
        new_title = title.replace("Technical Event", "Cultural Event")
    elif "General Event" in title:
        new_title = title.replace("General Event", "Cultural Event")
    elif "Event by" in title and "Cultural" not in title and "Technical" not in title:
        # e.g. "Event by club_optimus" -> "Cultural Event by club_optimus"
        # But wait, logic in nlp_processor is "{category} Event by {username}"
        # So "Event by club..." might be "Technical Event by..."
        pass

    if category != new_category or title != new_title:
        print(f"Updating ID {event_id}:")
        print(f"  Old: {title} ({category})")
        print(f"  New: {new_title} ({new_category})")
        
        cursor.execute("UPDATE events SET category = ?, title = ? WHERE id = ?", (new_category, new_title, event_id))
        updated_count += 1

conn.commit()
conn.close()
print(f"Updated {updated_count} events.")
