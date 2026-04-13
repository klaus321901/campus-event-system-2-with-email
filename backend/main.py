from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import os
import sys
import subprocess
from dotenv import load_dotenv
import os
from pathlib import Path
env_path = Path(__file__).resolve().parent / '.env'
print("[DEBUG] Looking for .env at:", env_path)
print("[DEBUG] .env exists:", env_path.exists())
load_dotenv(dotenv_path=env_path)
print("[DEBUG] GEMINI KEY:", os.getenv("AIzaSyBDBmZYkeGIQkKwXaKG2qNm7VcaSP-KtTw"))
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY1")
GEMINI_API_KEY2 = os.getenv("GEMINI_API_KEY2")
print("[DEBUG] GEMINI KEY:", GEMINI_API_KEY)

from . import models, database, auth
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# Add root to sys.path to import from ml
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Experimental AI refinement module (disabled for final project)
# try:
#     from ml.gemini_refiner import refine_event_with_gemini
# except ImportError:
#     print("[WARNING] Could not import gemini_refiner. 'Refine' functionality will be limited.")
#     refine_event_with_gemini = None
refine_event_with_gemini = None


def normalize_time(time_str: Optional[str]) -> Optional[str]:
    """Normalize mixed time formats (12h/24h) to HH:MM (24h)."""
    if not time_str:
        return None
    time_str = time_str.strip().upper()
    formats = [
        "%I:%M %p", "%I:%M%p", "%I %p", "%I%p", # 12-hour
        "%H:%M", "%H.%M", "%H %M",              # 24-hour
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.strftime("%H:%M")
        except ValueError:
            continue
    return time_str


models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Campus Event System")

# Auth Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount data directory to serve images
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
if os.path.exists(data_dir):
    app.mount("/data", StaticFiles(directory=data_dir), name="data")
    # Also explicitly mount the images folder for easy access if needed
    images_dir = os.path.join(data_dir, "images")
    if os.path.exists(images_dir):
        app.mount("/images", StaticFiles(directory=images_dir), name="images")

# Frontend directory path
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Mount frontend static files (CSS, JS, etc.)
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

class EventUpdate(BaseModel):
    title: Optional[str] = None
    club_name: Optional[str] = None
    category: Optional[str] = None
    event_date: Optional[str] = None
    time: Optional[str] = None
    venue: Optional[str] = None
    source_url: Optional[str] = None
    registration_link: Optional[str] = None
    description: Optional[str] = None
    image_path: Optional[str] = None
    last_register_date: Optional[str] = None
    is_published: Optional[bool] = None

class EventCreate(BaseModel):
    title: str
    club_name: str
    description: Optional[str] = None
    event_date: Optional[str] = None        # YYYY-MM-DD
    event_time: Optional[str] = None        # HH:MM
    venue: Optional[str] = None
    category: Optional[str] = "Other"
    registration_link: Optional[str] = None
    last_register_date: Optional[str] = None
    source_url: Optional[str] = None        # Instagram post URL (optional)
    image_path: Optional[str] = None        # Set after image upload

@app.post("/events/add")
def add_event_manually(event: EventCreate, db: Session = Depends(database.get_db)):
    """Admin: manually add a new event directly to PostgreSQL."""

    # Normalize source_url: "" -> None
    event_source_url = event.source_url.strip() if event.source_url and event.source_url.strip() else None

    # Parse date
    actual_date = None
    if event.event_date:
        try:
            actual_date = datetime.strptime(event.event_date, "%Y-%m-%d")
        except ValueError:
            pass

    # Normalize time
    normalized_time = normalize_time(event.event_time)

    # Always insert new row
    new_event = models.Event(
        title=event.title,
        club_name=event.club_name,
        description=event.description or "",
        event_date=actual_date,
        date_str=event.event_date,
        venue=event.venue or "MJCET Campus",
        category=event.category or "Other",
        registration_link=event.registration_link,
        source_url=event_source_url,
        image_path=event.image_path,
        profile_pic=None,
        is_published=True,
        source_type="manual",
        time=normalized_time,
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return {"message": "Event added successfully", "id": new_event.id}


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Admin: upload a poster image and return its saved path."""
    import shutil, uuid
    images_dir = os.path.join(data_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"manual_{uuid.uuid4().hex[:10]}.{ext}"
    filepath = os.path.join(images_dir, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"path": filepath, "url": f"/data/images/{filename}"}

# Root route - serve index.html (Main Dashboard)
@app.get("/")
def read_root():
    frontend_path = os.path.join(frontend_dir, "index.html")
    return FileResponse(frontend_path)

@app.get("/analysis.html")
def read_analysis():
    from fastapi.responses import FileResponse
    import os
    # Return 404 if file doesn't exist (safety)
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "analysis.html")
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=404, detail="Analysis page not found")
    return FileResponse(frontend_path)

@app.get("/admin_login.html")
def read_admin_login():
    frontend_path = os.path.join(frontend_dir, "admin_login.html")
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=404, detail="Admin login page not found")
    return FileResponse(frontend_path)

@app.get("/admin.html")
def read_admin():
    frontend_path = os.path.join(frontend_dir, "admin.html")
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=404, detail="Admin page not found")
    return FileResponse(frontend_path)

@app.get("/event_details.html")
def read_event_details():
    frontend_path = os.path.join(frontend_dir, "event_details.html")
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=404, detail="Event details page not found")
    return FileResponse(frontend_path)

@app.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(database.get_db)):
    """Public: Fetch a single event with aggregated ratings."""
    # Aggregated rating subquery (simplified for single event)
    stats = db.query(
        func.avg(models.Feedback.rating).label("avg_rating"),
        func.count(models.Feedback.id).label("review_count")
    ).filter(models.Feedback.event_id == event_id).first()

    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    e_dict = {c.name: getattr(event, c.name) for c in event.__table__.columns}
    e_dict["average_rating"] = round(float(stats.avg_rating), 1) if stats.avg_rating else 0
    e_dict["review_count"] = stats.review_count or 0
    
    return e_dict

@app.get("/events/")
def get_events(db: Session = Depends(database.get_db)):
    """Public: only returns published manual events."""
    # Aggregation subquery for ratings
    subquery = db.query(
        models.Feedback.event_id,
        func.avg(models.Feedback.rating).label("avg_rating"),
        func.count(models.Feedback.id).label("review_count")
    ).group_by(models.Feedback.event_id).subquery()

    # Main query with Outer Join
    query_results = db.query(models.Event, subquery.c.avg_rating, subquery.c.review_count).outerjoin(
        subquery, models.Event.id == subquery.c.event_id
    ).filter(
        models.Event.is_published == True,
        models.Event.source_type == "manual"
    ).order_by(models.Event.created_at.desc()).all()

    results = []
    for event_obj, avg_rating, review_count in query_results:
        e_dict = {c.name: getattr(event_obj, c.name) for c in event_obj.__table__.columns}
        e_dict["average_rating"] = round(float(avg_rating), 1) if avg_rating else 0
        e_dict["review_count"] = review_count or 0
        results.append(e_dict)
    
    return results

@app.get("/admin/staging/")
def get_staging_events(db: Session = Depends(database.get_db)):
    """Admin: returns all events with ratings, including staging."""
    subquery = db.query(
        models.Feedback.event_id,
        func.avg(models.Feedback.rating).label("avg_rating"),
        func.count(models.Feedback.id).label("review_count")
    ).group_by(models.Feedback.event_id).subquery()

    query_results = db.query(models.Event, subquery.c.avg_rating, subquery.c.review_count).outerjoin(
        subquery, models.Event.id == subquery.c.event_id
    ).filter(models.Event.source_type == "manual").order_by(models.Event.created_at.desc()).all()

    results = []
    for event_obj, avg_rating, review_count in query_results:
        e_dict = {c.name: getattr(event_obj, c.name) for c in event_obj.__table__.columns}
        e_dict["average_rating"] = round(float(avg_rating), 1) if avg_rating else 0
        e_dict["review_count"] = review_count or 0
        results.append(e_dict)
    return results

@app.post("/events/{event_id}/publish")
def publish_event(event_id: int, db: Session = Depends(database.get_db)):
    """Admin: publish a staging event. Marks it as 'manual' to go live."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.is_published = True
    event.source_type = "manual"  # Promote to manual/verified
    db.commit()
    return {"message": "Event published and verified!", "id": event_id}

@app.post("/events/{event_id}/unpublish")
def unpublish_event(event_id: int, db: Session = Depends(database.get_db)):
    """Admin: unpublish an event (hide from frontend)."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.is_published = False
    db.commit()
    return {"message": "Event unpublished", "id": event_id}

@app.post("/admin/publish-all/")
def publish_all_events(db: Session = Depends(database.get_db)):
    """Admin: publish ALL staging events. Promotes them all to 'manual'."""
    count = db.query(models.Event).filter(
        models.Event.is_published == False,
        models.Event.source_type == "manual"
    ).update({
        "is_published": True,
        "source_type": "manual"
    })
    db.commit()
    return {"message": f"Published {count} events as manual verified."}

@app.put("/events/{event_id}")
def update_event(event_id: int, event_update: EventUpdate, db: Session = Depends(database.get_db)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Normalize source_url: Empty string or whitespace becomes None (NULL in DB)
    if event_update.source_url is not None:
        event_update.source_url = event_update.source_url.strip() if event_update.source_url.strip() else None

    update_data = event_update.dict(exclude_unset=True)
    
    # Handle event_date specially to update both date_str and event_date
    if "event_date" in update_data:
        d_str = update_data.pop("event_date")
        db_event.date_str = d_str
        try:
            db_event.event_date = datetime.strptime(d_str, "%Y-%m-%d")
        except:
            # If invalid format, let event_date be null or keep old
            pass

    # Normalize time if provided
    if "time" in update_data:
        update_data["time"] = normalize_time(update_data["time"])

    for field, value in update_data.items():
        if hasattr(db_event, field):
            setattr(db_event, field, value)
        
    try:
        db.commit()
        db.refresh(db_event)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return db_event


@app.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(database.get_db)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(db_event)
    db.commit()
    return {"message": "Event deleted successfully"}

@app.on_event("startup")
def startup_db_check():
    # Automatically add missing columns 'role' and 'club_name' to users table
    try:
        from .database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            # Check if role column exists
            try:
                conn.execute(text("SELECT role FROM users LIMIT 1"))
            except:
                print("[STARTUP] Adding 'role' column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'student'"))
                conn.commit()
            
            # Check if club_name column exists
            try:
                conn.execute(text("SELECT club_name FROM users LIMIT 1"))
            except:
                print("[STARTUP] Adding 'club_name' column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN club_name VARCHAR"))
                conn.commit()

    except Exception as e:
        print(f"[STARTUP] Migration warning: {e}")

# --- AUTH SYSTEM ---

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    # Determine role (demo simplification: 'admin123' password makes you an admin)
    role = "super_admin" if user.username.lower() == "admin" else "student"
    
    new_user = models.User(username=user.username, hashed_password=hashed_password, email=user.email, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = auth.create_access_token(data={"sub": new_user.username, "role": new_user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    payload = auth.decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/users/me")
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id, "role": current_user.role}

# --- FEEDBACK SYSTEM ---

class FeedbackCreate(BaseModel):
    user_name: str
    rating: int
    comment: Optional[str] = None
    user_id: Optional[str] = None

@app.post("/events/{event_id}/feedback")
def create_feedback(event_id: int, feedback: FeedbackCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    # Verify event exists
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Rate Limit: Max 3 reviews per user per event
    existing_count = db.query(models.Feedback).filter(
        models.Feedback.event_id == event_id,
        models.Feedback.user_id == str(current_user.id)
    ).count()

    if existing_count >= 1:
        raise HTTPException(status_code=400, detail="You have already reviewed this event.")

    db_feedback = models.Feedback(
        event_id=event_id,
        user_name=current_user.username,
        rating=feedback.rating,
        comment=feedback.comment,
        sentiment="Pending",
        user_id=str(current_user.id)
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@app.delete("/feedback/{feedback_id}")
def delete_feedback(feedback_id: int, user_id: str, db: Session = Depends(database.get_db)):
    """Delete feedback if the user_id matches."""
    db_feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Check ownership
    if db_feedback.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this feedback")

    db.delete(db_feedback)
    db.commit()
    return {"message": "Feedback deleted successfully"}

@app.get("/events/{event_id}/feedback")
def get_feedback(event_id: int, db: Session = Depends(database.get_db)):
    # Verify event exists
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    feedbacks = db.query(models.Feedback).filter(models.Feedback.event_id == event_id).order_by(models.Feedback.id.desc()).all()
    return feedbacks

# --- CLUB SUBSCRIPTION SYSTEM ---

@app.post("/clubs/{club_name}/follow")
def follow_club(club_name: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    # Check if already following
    existing = db.query(models.ClubSubscription).filter(
        models.ClubSubscription.user_id == current_user.id,
        models.ClubSubscription.club_name == club_name
    ).first()
    
    if existing:
        # Unfollow if exists (toggle)
        db.delete(existing)
        db.commit()
        return {"message": f"Unfollowed {club_name}", "following": False}
    
    new_sub = models.ClubSubscription(user_id=current_user.id, club_name=club_name)
    db.add(new_sub)
    db.commit()
    return {"message": f"Following {club_name}", "following": True}

@app.get("/users/me/following")
def get_followed_clubs(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    subs = db.query(models.ClubSubscription).filter(models.ClubSubscription.user_id == current_user.id).all()
    return [s.club_name for s in subs]

# --- ANALYSIS SYSTEM ---

# --- REMINDER SYSTEM ---

class ReminderCreate(BaseModel):
    reminder_type: str # "2h", "6h", "24h"

@app.post("/events/{event_id}/remind")
async def create_reminder(event_id: int, reminder_data: ReminderCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Issue 4: Reminder validation
    if not event.event_date or not event.time:
        raise HTTPException(status_code=400, detail="Reminders require both event date and time.")

    # Calculate reminder time based on event_date + time
    try:
        event_start = datetime.combine(event.event_date, datetime.min.time())
        if event.time:
            # Time is stored as HH:MM
            h, m = map(int, event.time.split(':'))
            event_start = event_start.replace(hour=h, minute=m)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid event time format: {event.time}")

    # PREVENT reminders for past events
    now_time = datetime.utcnow()
    if event_start < now_time:
        raise HTTPException(status_code=400, detail="This event has already passed. Cannot set reminders.")

    delta = timedelta(hours=1) # default 1h
    if reminder_data.reminder_type == "30m":
        delta = timedelta(minutes=30)
    elif reminder_data.reminder_type == "3h":
        delta = timedelta(hours=3)
    elif reminder_data.reminder_type == "24h":
        delta = timedelta(days=1)
        
    # Issue 3: Reminder calculation bug
    target_time = event_start - delta
    
    # Also check if the TARGET logic time is already in the past
    if target_time < now_time:
        raise HTTPException(status_code=400, detail="The reminder time is already in the past!")
    
    new_reminder = models.Reminder(
        user_id=current_user.id,
        event_id=event.id,
        reminder_type=reminder_data.reminder_type,
        reminder_time=target_time
    )
    db.add(new_reminder)
    db.commit()
    return {"message": f"Reminder set for {reminder_data.reminder_type} before the event!"}


@app.get("/users/me/reminders")
async def get_my_reminders(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    # Get reminders that haven't been "sent" (shown) yet and are due
    now_time = datetime.utcnow()
    reminders = db.query(models.Reminder).filter(
        models.Reminder.user_id == current_user.id,
        models.Reminder.reminder_time <= now_time,
        models.Reminder.is_sent == False
    ).all()
    
    results = []
    for r in reminders:
        if r.event:
            results.append({
                "id": r.id,
                "event_title": r.event.title,
                "type": r.reminder_type,
                "event_id": r.event_id
            })
        # Mark as sent once fetched
        r.is_sent = True
    
    db.commit()
    return results

@app.post("/events/{event_id}/analyze")
def analyze_event(event_id: int, db: Session = Depends(database.get_db)):
    import google.generativeai as genai
    from collections import Counter

    feedbacks = db.query(models.Feedback).filter(models.Feedback.event_id == event_id).all()
    
    if not feedbacks:
        return {
            "total": 0,
            "average_rating": 0,
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
            "keywords": [],
            "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "comments": [],
            "gemini": {
                "summary": "No reviews yet.",
                "improvement_suggestions": [],
                "attendance_prediction": "Not enough data.",
                "club_reputation": "Not enough data."
            }
        }

    total = len(feedbacks)
    average_rating = round(sum(f.rating for f in feedbacks) / total, 1)

    # Rating distribution
    rating_dist = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for f in feedbacks:
        key = str(f.rating)
        if key in rating_dist:
            rating_dist[key] += 1

    # Comments list
    comments = [
        {"user": f.user_name, "rating": f.rating, "comment": f.comment or ""}
        for f in feedbacks
    ]

    # Keywords (simple word frequency for word cloud)
    ignore_words = {
        "the", "and", "was", "is", "it", "to", "in", "of", "a", "very",
        "good", "bad", "event", "this", "that", "with", "for", "are", "were",
        "had", "have", "has", "but", "not", "from", "they", "their", "been",
        "would", "could", "should", "really", "also", "just", "more", "than",
        "then", "when", "which", "there", "about", "will", "your", "was"
    }
    words = []
    for f in feedbacks:
        if f.comment:
            for word in f.comment.lower().split():
                clean_word = "".join(c for c in word if c.isalnum())
                if len(clean_word) > 3 and clean_word not in ignore_words:
                    words.append(clean_word)
    keyword_counts = [{"word": w, "count": c} for w, c in Counter(words).most_common(15)]

    # Gemini Analysis
    gemini_result = {
        "summary": "Analysis unavailable.",
        "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
        "improvement_suggestions": [],
        "attendance_prediction": "Not enough data.",
        "club_reputation": "Not enough data."
    }

    # Get club name for reputation score
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    club_name = event.club_name if event else "Unknown"

    # Get all events by same club with their average ratings for reputation
    club_events = db.query(models.Event).filter(
        models.Event.club_name == club_name,
        models.Event.source_type == "manual"
    ).all()

    club_ratings = []
    for ce in club_events:
        feedbacks_for_event = db.query(models.Feedback).filter(models.Feedback.event_id == ce.id).all()
        if feedbacks_for_event:
            avg = sum(f.rating for f in feedbacks_for_event) / len(feedbacks_for_event)
            club_ratings.append({"event": ce.title, "avg_rating": round(avg, 1), "reviews": len(feedbacks_for_event)})

    try:
        api_key = GEMINI_API_KEY or GEMINI_API_KEY2
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        # Build prompt
        reviews_text = "\n".join([
            f"- Rating: {f.rating}/5, Comment: '{f.comment}'" if f.comment else f"- Rating: {f.rating}/5 (no comment)"
            for f in feedbacks
        ])

        club_history = "\n".join([
            f"- {r['event']}: {r['avg_rating']}/5 ({r['reviews']} reviews)"
            for r in club_ratings
        ]) if club_ratings else "No historical data available."

        prompt = f"""You are analyzing student feedback for a college campus event.

Event: {event.title if event else 'Unknown'}
Club: {club_name}
Total Reviews: {total}
Average Rating: {average_rating}/5

Reviews:
{reviews_text}

Club's event history:
{club_history}

Please respond ONLY with a valid JSON object in this exact format:
{{
    "summary": "One sentence overall summary of the event feedback",
    "sentiment": {{
        "positive": <percentage as integer 0-100>,
        "neutral": <percentage as integer 0-100>,
        "negative": <percentage as integer 0-100>
    }},
    "improvement_suggestions": [
        "Suggestion 1",
        "Suggestion 2",
        "Suggestion 3"
    ],
    "attendance_prediction": "One sentence prediction about future attendance based on feedback",
    "club_reputation": "One sentence assessment of the club's reputation based on all their events"
}}

Important: 
- Sentiment percentages must add up to 100.
- Be specific and based only on the actual reviews provided.
- If there are fewer than 2 comments with actual text, set improvement_suggestions to ["Not enough comment data to generate specific suggestions."] only.
- Never generate generic suggestions like 'encourage reviewers to comment' or 'investigate lower ratings'.
- Only generate improvement suggestions if the same theme or issue is mentioned by at least 3 different reviewers. If no theme repeats across 3+ reviews, set improvement_suggestions to ["Not enough repeated feedback to generate specific suggestions."].
- - Keep all text responses under 100 characters each. Be concise."""
        response = model.generate_content(
             prompt,
             generation_config={"max_output_tokens": 1024, "temperature": 0.3}
        )
        raw = response.text.strip()

        # Clean up markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        print("[GEMINI RAW]", raw[:500])

        import re
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
        import json
        try:
             gemini_result = json.loads(raw)
        except json.JSONDecodeError as je:
            print("[JSON ERROR]", je)
            print("[RAW THAT FAILED]", repr(raw))
            raise
               
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        # Fallback to rating-based sentiment
        positive = sum(1 for f in feedbacks if f.rating >= 4)
        negative = sum(1 for f in feedbacks if f.rating <= 2)
        neutral = total - positive - negative
        gemini_result["sentiment"] = {
            "positive": round((positive / total) * 100),
            "neutral": round((neutral / total) * 100),
            "negative": round((negative / total) * 100)
        }
        gemini_result["summary"] = "AI analysis unavailable. Showing rating-based sentiment."

    return {
        "event_id": event_id,
        "total": total,
        "average_rating": average_rating,
        "sentiment": gemini_result.get("sentiment", {"positive": 0, "neutral": 0, "negative": 0}),
        "keywords": keyword_counts,
        "rating_distribution": rating_dist,
        "comments": comments,
        "gemini": {
            "summary": gemini_result.get("summary", ""),
            "improvement_suggestions": gemini_result.get("improvement_suggestions", []),
            "attendance_prediction": gemini_result.get("attendance_prediction", ""),
            "club_reputation": gemini_result.get("club_reputation", "")
        }
    }

# --- ADMIN POWER TOOLS ---

# Experimental AI refinement module (disabled for final project)
# @app.post("/admin/events/{event_id}/refine")
# def refine_event(event_id: int, db: Session = Depends(database.get_db)):
#     """Manually trigger Gemini AI to refine event details from image/caption."""
#     if not refine_event_with_gemini:
#         raise HTTPException(status_code=500, detail="Gemini refiner not available")
# 
#     db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
#     if not db_event:
#         raise HTTPException(status_code=404, detail="Event not found")
#         
#     # Get image path and description
#     image_path = db_event.image_path
#     if not image_path or not os.path.exists(image_path):
#         # Try finding it in data/images if absolute path fails
#         alt_path = os.path.join(root_dir, image_path) if image_path else ""
#         if os.path.exists(alt_path):
#             image_path = alt_path
#         else:
#             raise HTTPException(status_code=400, detail=f"Image file not found: {image_path}")
# 
#     print(f"[ADMIN] Refining event {event_id} with Gemini...")
#     refined_data = refine_event_with_gemini(image_path, db_event.description)
#     
#     if not refined_data:
#         raise HTTPException(status_code=500, detail="Gemini failed to refine event")
#         
#     # Update fields
#     if refined_data.get("title"): db_event.title = refined_data["title"]
#     if refined_data.get("event_date"):
#         try:
#             db_event.event_date = datetime.strptime(refined_data["event_date"], "%Y-%m-%d")
#             db_event.date_str = refined_data["event_date"]
#         except:
#             pass
#     if refined_data.get("event_time"): db_event.time = refined_data["event_time"]
#     if refined_data.get("venue"): db_event.venue = refined_data["venue"]
#     if refined_data.get("category"): db_event.category = refined_data["category"]
#     if refined_data.get("registration_link"): db_event.registration_link = refined_data["registration_link"]
#     
#     db.commit()
#     db.refresh(db_event)
#     return {"message": "Event refined successfully!", "data": refined_data}


@app.delete("/admin/events/delete-past")
def delete_past_events(db: Session = Depends(database.get_db)):
    """Delete all events whose event_date is in the past."""
    now = datetime.now()
    # Find events with event_date < now
    past_events = db.query(models.Event).filter(models.Event.event_date < now).all()
    count = len(past_events)
    
    for event in past_events:
        db.delete(event)
        
    db.commit()
    return {"message": f"Deleted {count} past events successfully."}
