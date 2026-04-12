# 💻 Complete Code Reference Guide

**Campus Event System - All Code Files Documentation**

---

## 📂 Project File Structure

```
campus_event_system/
├── 📁 backend/              # Backend API (FastAPI)
│   ├── main.py              # 277 lines - Main FastAPI application
│   ├── models.py            # 43 lines - Database models
│   ├── database.py          # 27 lines - Database configuration
│   ├── auth.py              # 37 lines - Authentication logic
│   └── init_db.py           # Small - Database initialization
│
├── 📁 frontend/             # Frontend UI (Vanilla JS)
│   ├── app.html             # 1173 lines - Main dashboard
│   ├── analysis.html        # 344 lines - Analytics page
│   ├── event_details.html   # ~300 lines - Event details
│   └── style.css            # ~150 lines - Styling
│
├── 📁 ml/                   # Machine Learning & Processing
│   ├── ocr_extractor.py     # 176 lines - PaddleOCR + QR detection
│   ├── nlp_processor.py     # 173 lines - NLP entity extraction
│   ├── ai_event_processor.py # AI-powered processing
│   └── db_sync.py           # Database synchronization
│
├── 📁 scraper/              # Instagram Scraping
│   └── instagram_scraper.py # 295 lines - Selenium scraper
│
├── 📁 data/                 # Data Storage
│   ├── scraped_data.json    # Raw Instagram data
│   ├── extracted_events.json # OCR results
│   ├── final_events.json    # Processed events
│   └── images/              # Downloaded posters
│
├── 📄 requirements.txt      # Python dependencies
├── 📄 reset_db.py           # Database reset utility
├── 📄 campus_events.db      # SQLite database
├── 📄 README.md             # Project documentation
└── 📄 SETUP_GUIDE.md        # Setup instructions
```

**Total Lines of Code: ~3000+**

---

## 🔧 BACKEND FILES

### **1. backend/main.py** (277 lines)
**Purpose:** FastAPI application with all API endpoints

#### **Key Imports:**
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
```

#### **Main Components:**

**App Initialization:**
```python
app = FastAPI(title="Campus Event System")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Static File Serving:**
```python
# Serve event poster images
app.mount("/data", StaticFiles(directory=data_dir), name="data")

# Serve frontend HTML
@app.get("/")
def read_root():
    return FileResponse("frontend/app.html")
```

#### **API Endpoints:**

**Events Management:**
```python
@app.get("/events/")
def get_events(db: Session = Depends(database.get_db)):
    # Returns all events with average ratings
    # Aggregates feedback for each event
    
@app.put("/events/{event_id}")
def update_event(event_id: int, event_update: EventUpdate):
    # Allows updating event details
    
@app.delete("/events/{event_id}")
def delete_event(event_id: int):
    # Deletes an event and related data
```

**Authentication:**
```python
@app.post("/register")
def register(user: UserCreate):
    # User registration with password hashing
    # Returns JWT token
    
@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm):
    # User login with OAuth2 flow
    # Returns access token
    
@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    # Get current authenticated user
```

**Feedback System:**
```python
@app.post("/events/{event_id}/feedback")
def create_feedback(event_id: int, feedback: FeedbackCreate):
    # Submit event review
    
@app.get("/events/{event_id}/feedback")
def get_feedback(event_id: int):
    # Get all feedback for an event
    
@app.delete("/feedback/{feedback_id}")
def delete_feedback(feedback_id: int, user_id: str):
    # Delete own feedback (ownership check)
```

**Analytics:**
```python
@app.post("/events/{event_id}/analyze")
def analyze_event(event_id: int):
    # Returns sentiment analysis, keywords, statistics
    # Calculates positive/neutral/negative percentages
```

---

### **2. backend/models.py** (43 lines)
**Purpose:** SQLAlchemy database models

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    date = Column(String, nullable=True)
    time = Column(String, nullable=True)
    venue = Column(String, nullable=True)
    club_name = Column(String, index=True)
    profile_pic = Column(String, nullable=True)
    image_path = Column(String)
    source_url = Column(String)
    category = Column(String, nullable=True)
    registration_link = Column(String, nullable=True)
    last_register_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    user_name = Column(String)
    rating = Column(Integer)  # 1-5 stars
    comment = Column(String, nullable=True)
    sentiment = Column(String, default="Pending")
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

---

### **3. backend/database.py** (27 lines)
**Purpose:** Database connection and session management

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite for development, PostgreSQL for production
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./campus_events.db"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### **4. backend/auth.py** (37 lines)
**Purpose:** JWT authentication and password hashing

```python
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "supersecretkeyshouldbeinchangedinproduction"  # ⚠️ NEEDS FIX
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

---

## 🎨 FRONTEND FILES

### **5. frontend/app.html** (1173 lines)
**Purpose:** Main dashboard with event grid, filters, admin panel

#### **Key Sections:**

**HTML Structure:**
```html
<header>
    <h1>Campus Events 🚀</h1>
    <div class="search-bar">
        <input id="searchInput" placeholder="Search events...">
    </div>
    <div class="filters">
        <button class="filter-btn active" data-filter="all">All</button>
        <button class="filter-btn" data-filter="Technical">Technical</button>
        <!-- More category filters -->
        <select id="clubFilter"><!-- Club dropdown --></select>
        <button id="authBtn">Login / Register</button>
        <button id="adminBtn">🔐 Admin</button>
    </div>
</header>

<main id="eventsGrid" class="events-grid">
    <!-- Event cards generated by JavaScript -->
</main>
```

**CSS Styling:**
```css
/* Glassmorphic Design */
body {
    background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
}

.event-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(15px);
    border-radius: 20px;
    transition: all 0.3s;
}

.event-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
}
```

**JavaScript Functionality:**
```javascript
const API_URL = 'http://127.0.0.1:8000';
let allEvents = [];
let authToken = localStorage.getItem('access_token');

// Load events from API
async function loadEvents() {
    const response = await fetch(`${API_URL}/events/`);
    allEvents = await response.json();
    renderEvents(allEvents);
}

// Render event cards
function renderEvents(events) {
    const grid = document.getElementById('eventsGrid');
    grid.innerHTML = '';
    
    events.forEach(event => {
        const card = createEventCard(event);
        grid.appendChild(card);
    });
}

// Event filtering
function filterEvents(category) {
    if (category === 'all') {
        renderEvents(allEvents);
    } else {
        const filtered = allEvents.filter(e => e.category === category);
        renderEvents(filtered);
    }
}

// Search functionality
document.getElementById('searchInput').addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    const filtered = allEvents.filter(event =>
        event.title.toLowerCase().includes(query)
    );
    renderEvents(filtered);
});
```

**Authentication:**
```javascript
// Login/Register Modal
async function login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const res = await fetch(`${API_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
    });
    
    const data = await res.json();
    if (res.ok) {
        authToken = data.access_token;
        localStorage.setItem('access_token', authToken);
        await checkAuth();
    }
}
```

**Admin Panel:**
```javascript
// Edit Event
async function editEvent(eventId) {
    const event = allEvents.find(e => e.id === eventId);
    
    // Populate form
    document.getElementById('editTitle').value = event.title;
    document.getElementById('editDescription').value = event.description;
    // ... more fields
    
    // Show modal
    document.getElementById('editForm').classList.add('active');
}

// Save Changes
async function saveEvent(eventId, updatedData) {
    await fetch(`${API_URL}/events/${eventId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedData)
    });
    
    await loadEvents(); // Refresh
}
```

---

### **6. frontend/analysis.html** (344 lines)
**Purpose:** Event analytics dashboard with charts

```javascript
// Fetch analytics data
async function loadAnalytics(eventId) {
    const response = await fetch(`${API_URL}/events/${eventId}/analyze`, {
        method: 'POST'
    });
    const data = await response.json();
    
    renderSentimentChart(data.sentiment);
    renderKeywordChart(data.keywords);
    generateInsights(data);
}

// Chart.js Visualization
function renderSentimentChart(sentiment) {
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Positive', 'Neutral', 'Negative'],
            datasets: [{
                data: [sentiment.positive, sentiment.neutral, sentiment.negative],
                backgroundColor: ['#2ecc71', '#f1c40f', '#e74c3c']
            }]
        }
    });
}

// AI Insights Generation
function generateInsights(data) {
    let suggestions = [];
    
    if (data.sentiment.positive > 70) {
        suggestions.push("Focus on retention: Send a 'Thank You' email");
    }
    
    if (keywords.includes('food')) {
        suggestions.push("Catering was a major talking point");
    }
    
    return suggestions;
}
```

---

## 🤖 MACHINE LEARNING FILES

### **7. ml/ocr_extractor.py** (176 lines)
**Purpose:** Extract text from event posters using PaddleOCR

```python
from paddleocr import PaddleOCR
from pyzbar import pyzbar
import cv2

class AdvancedEventExtractor:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
    
    def preprocess_image(self, image_path):
        """Enhance image quality for better OCR"""
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # CLAHE contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        return enhanced
    
    def detect_qr_codes(self, image_path):
        """Find and decode QR codes"""
        image = cv2.imread(image_path)
        qr_codes = pyzbar.decode(image)
        
        urls = []
        for qr in qr_codes:
            data = qr.data.decode('utf-8')
            if data.startswith('http'):
                urls.append(data)
        return urls
    
    def extract_text(self, image_path):
        """Run OCR on image"""
        processed_path = self.preprocess_image(image_path)
        result = self.ocr.ocr(processed_path, cls=True)
        
        text_lines = [line[1][0] for line in result[0]]
        full_text = " ".join(text_lines)
        return full_text

# Main processing function
def process_scraped_images():
    extractor = AdvancedEventExtractor()
    
    for post in scraped_data:
        image_path = post['image_path']
        
        # Extract QR registration links
        qr_urls = extractor.detect_qr_codes(image_path)
        
        # Extract text via OCR
        ocr_text = extractor.extract_text(image_path)
        
        # Combine with caption
        full_content = f"{caption}\n{ocr_text}"
        
        extracted_events.append({
            'full_content': full_content,
            'registration_link': qr_urls[0] if qr_urls else None
        })
```

---

### **8. ml/nlp_processor.py** (173 lines)
**Purpose:** Extract event details using NLP and regex

```python
import re

# Date extraction
def extract_date(text):
    patterns = [
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None

# Venue extraction
def extract_venue(text):
    venue_keywords = {
        "auditorium": "Auditorium",
        "seminar hall": "Seminar Hall",
        "online": "Online",
        "zoom": "Online (Zoom)"
    }
    
    for keyword, venue_name in venue_keywords.items():
        if keyword in text.lower():
            return venue_name
    
    return "MJCET Campus"  # Default

# Event categorization
def classify_event(text):
    if any(word in text.lower() for word in ["hackathon", "coding", "tech", "ai"]):
        return "Technical"
    elif any(word in text.lower() for word in ["dance", "music", "fest"]):
        return "Cultural"
    elif any(word in text.lower() for word in ["cricket", "sports"]):
        return "Sports"
    elif any(word in text.lower() for word in ["seminar", "talk"]):
        return "Seminar"
    return "General"

# Filter member announcements
def is_member_announcement(text):
    filter_keywords = ["new gb", "core team", "welcome team", "recruitment"]
    return any(keyword in text.lower() for keyword in filter_keywords)

# Main processing
def process_events():
    for event in extracted_events:
        text = event['full_content']
        
        # Filter unwanted posts
        if is_member_announcement(text):
            continue
        
        # Extract details
        processed_events.append({
            'title': f"{classify_event(text)} Event",
            'date': extract_date(text),
            'venue': extract_venue(text),
            'category': classify_event(text),
            'description': text,
            'registration_link': event.get('registration_link')
        })
```

---

## 🕷️ SCRAPER FILES

### **9. scraper/instagram_scraper.py** (295 lines)
**Purpose:** Scrape Instagram posts using Selenium

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time, random

TARGET_ACCOUNTS = [
    "csi_mjcet", "ecellmjcet", "gdgc.mjcet", 
    "saemjcet", "ieeesmcmjcet", "mjcet_acm"
]

def setup_driver():
    """Setup Chrome with anti-detection"""
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Stealth mode
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def scrape_instagram():
    driver = setup_driver()
    
    # Manual login
    driver.get("https://www.instagram.com/accounts/login/")
    input("Press Enter after you've logged in...")
    
    for username in TARGET_ACCOUNTS:
        driver.get(f"https://www.instagram.com/{username}/")
        time.sleep(random.uniform(5, 8))
        
        # Get profile pic
        profile_pic = driver.find_element(By.CSS_SELECTOR, "header img").get_attribute("src")
        
        # Get post links
        links = driver.find_elements(By.TAG_NAME, "a")
        post_links = [a.get_attribute("href") for a in links if "/p/" in a.get_attribute("href")]
        
        for post_url in post_links[:6]:  # Limit to 6 recent posts
            driver.get(post_url)
            time.sleep(random.uniform(2, 4))
            
            # Extract caption
            caption = driver.find_element(By.CSS_SELECTOR, "h1").text
            
            # Extract images
            images = driver.find_elements(By.CSS_SELECTOR, "article img")
            for img in images:
                src = img.get_attribute("src")
                download_image(src, username)
            
            scraped_data.append({
                'post_url': post_url,
                'username': username,
                'caption': caption,
                'images': images
            })
```

---

## 📊 DATA FILES

### **10. data/scraped_data.json**
**Purpose:** Raw Instagram data
```json
[
    {
        "post_url": "https://instagram.com/p/ABC123",
        "username": "csi_mjcet",
        "profile_pic_url": "https://...",
        "caption": "Join us for Hackathon 2024!",
        "timestamp": "2024-11-15T10:00:00",
        "images": [
            {
                "src": "https://...",
                "local_path": "data/images/csi_mjcet_1234.jpg",
                "qr_link": "https://forms.gle/abc123"
            }
        ],
        "status": "downloaded_v3"
    }
]
```

### **11. data/extracted_events.json**
**Purpose:** OCR extracted text
```json
[
    {
        "username": "csi_mjcet",
        "post_url": "https://...",
        "image_path": "data/images/csi_mjcet_1234.jpg",
        "caption": "Join us for Hackathon!",
        "ocr_text": "HACKATHON 2024 25th Nov Auditorium Register Now",
        "full_content": "Join us for Hackathon!\nHACKATHON 2024 25th Nov...",
        "registration_link": "https://forms.gle/abc123",
        "qr_urls": ["https://forms.gle/abc123"]
    }
]
```

### **12. data/final_events.json**
**Purpose:** Processed and structured data
```json
[
    {
        "title": "Technical Event by csi_mjcet",
        "club": "csi_mjcet",
        "date": "25th Nov",
        "time": "10:00 AM",
        "venue": "Auditorium",
        "category": "Technical",
        "description": "Join us for the biggest coding competition...",
        "image_url": "data/images/csi_mjcet_1234.jpg",
        "profile_pic": "https://...",
        "original_link": "https://instagram.com/p/ABC123",
        "registration_link": "https://forms.gle/abc123",
        "last_register_date": "23rd Nov"
    }
]
```

---

## 🔄 UTILITY FILES

### **13. reset_db.py**
**Purpose:** Load JSON data into database
```python
import json
from backend.database import SessionLocal, engine
from backend.models import Base, Event

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Clear existing events
db.query(Event).delete()

# Load from JSON
with open('data/final_events.json', 'r') as f:
    events = json.load(f)

for event_data in events:
    event = Event(
        title=event_data['title'],
        club_name=event_data['club'],
        date=event_data['date'],
        # ... more fields
    )
    db.add(event)

db.commit()
print("Database reset complete!")
```

---

## 📦 CONFIGURATION FILES

### **14. requirements.txt**
```txt
fastapi
uvicorn
sqlalchemy
psycopg2-binary
selenium
webdriver-manager
beautifulsoup4
requests
python-multipart
python-dotenv
paddlepaddle
paddleocr
pyzbar
opencv-python
Pillow
passlib[bcrypt]
python-jose[cryptography]
slowapi
```

---

## 🚀 RUNNING THE APPLICATION

### **Step-by-Step Execution:**

1. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run Scraper (Optional):**
```bash
python -m scraper.instagram_scraper
```

3. **Run OCR Extraction:**
```bash
python -m ml.ocr_extractor
```

4. **Run NLP Processing:**
```bash
python -m ml.nlp_processor
```

5. **Load Database:**
```bash
python reset_db.py
```

6. **Start Backend:**
```bash
python -m uvicorn backend.main:app --reload
```

7. **Open Browser:**
```
http://localhost:8000
```

---

## 📈 CODE STATISTICS

| Component | Files | Lines | Languages |
|-----------|-------|-------|-----------|
| Backend | 4 | ~400 | Python |
| Frontend | 3 | ~1800 | HTML/CSS/JS |
| ML/Processing | 4 | ~600 | Python |
| Scraper | 1 | ~300 | Python |
| **TOTAL** | **12** | **~3100** | **Python, JS, HTML, CSS** |

---

**Last Updated:** February 17, 2026
**Total Project Size:** ~3100 lines of code across 12+ files
