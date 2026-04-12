from backend import database, models
from sqlalchemy.orm import Session

def publish_all():
    db = database.SessionLocal()
    try:
        # Find all unpublished events
        unpublished = db.query(models.Event).filter(models.Event.is_published == False).all()
        count = len(unpublished)
        
        if count == 0:
            print("[SYNC] 🛡️ No new unpublished events found. Everything is already live!")
        else:
            # Set all to True
            db.query(models.Event).filter(models.Event.is_published == False).update({"is_published": True})
            db.commit()
            print(f"[SYNC] 🚀 SUCCESS: {count} events have been pushed to the frontend!")
            
            # Print the top 5 titles for confirmation
            print("\nFeatured Live Events:")
            for event in unpublished[:5]:
                print(f" - {event.title} ({event.club_name})")
    except Exception as e:
        print(f"[SYNC] ❌ Error during publishing: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    publish_all()
