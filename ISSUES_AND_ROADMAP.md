# 🔧 Issues, Fixes & Feature Roadmap

**Campus Event System - Problems, Solutions & Enhancements**

---

## 🐛 CURRENT PROBLEMS

### **Critical Issues** 🔴

#### 1. Instagram Scraping Reliability
**Problem:**
- Instagram frequently blocks automated scraping
- Rate limiting and soft bans occur
- Manual login required every time
- Scraper breaks when Instagram updates HTML structure

**Impact:** High - Core functionality affected
**Status:** Ongoing issue

#### 2. QR Code to Registration Link Flow
**Status:** ⚡ Code Implemented (Awaiting Test)
- Added OpenCV pre-processing (grayscale + thresholding) to improve QR detection on noisy posters.
- Logic passes QR link as a "hint" to Gemini.
- **Fix Needed:** Ensure Gemini always prioritizes the QR link for the `registration_link` field.

#### 3. Duplicate Event Detection
**Problem:**
- No mechanism to prevent duplicate events
- Same event may be posted multiple times by different clubs
- No fuzzy matching for similar event titles

**Impact:** Medium - Database bloat and user confusion
**Status:** Not implemented

#### 3. Database Constraints Missing
**Problem:**
- No foreign key relationships defined
- No cascade delete for related records
- Feedback table doesn't enforce event_id existence

**Impact:** Medium - Data integrity issues
**Status:** Needs fix

#### 4. Hardcoded API URL
**Problem:**
```javascript
const API_URL = 'http://127.0.0.1:8000'; // Hardcoded in frontend
```
- Not configurable for production
- Requires manual edit for deployment

**Impact:** Medium - Deployment blocker
**Status:** Needs environment variable

#### 5. No Rate Limiting on Feedback
**Problem:**
- Users can spam reviews
- No restrictions on feedback submission
- Potential for abuse

**Impact:** Medium - Data quality concern
**Status:** Partially implemented (slowapi imported but not configured)

---

### **Major Issues** 🟡

#### 6. Error Handling Incomplete
**Problem:**
- Frontend shows generic "Failed to load" messages
- No retry mechanism for failed API calls
- No user-friendly error messages
- Backend exceptions not logged properly

**Impact:** Medium - Poor user experience
**Status:** Needs improvement

#### 7. Image Loading Performance
**Problem:**
- Large event poster images not optimized
- No lazy loading implemented
- All images load simultaneously
- Slow initial page load

**Impact:** Medium - Performance degradation
**Status:** Not optimized

#### 8. Search Functionality Limited
**Problem:**
- Only searches in title (not description)
- No fuzzy search or typo tolerance
- Case-sensitive in some cases

**Impact:** Low-Medium - User experience
**Status:** Basic implementation only

#### 9. No Pagination
**Problem:**
- All events loaded at once
- Performance issues with 100+ events
- DOM becomes heavy

**Impact:** Medium - Scalability concern
**Status:** Not implemented

#### 10. Mobile Responsiveness Issues
**Problem:**
- Admin panel not fully responsive
- Edit forms may overflow on small screens
- Touch interactions not optimized

**Impact:** Medium - Mobile user experience
**Status:** Partially responsive

---

### **Minor Issues** 🟢

#### 11. No Event Expiry
**Problem:**
- Past events remain visible
- No automatic archiving
- Clutters the dashboard

**Impact:** Low - UI clutter
**Status:** Not implemented

#### 12. Profile Pictures Not Working
**Problem:**
- Instagram profile pics may fail to load
- Fallback to initials-based avatars
- Canvas-generated DPs used

**Impact:** Low - Aesthetic issue
**Status:** Workaround in place

#### 13. No Email Notifications
**Problem:**
- Users don't get event reminders
- No confirmation emails for registration
- No feedback notifications

**Impact:** Low - Feature gap
**Status:** Not implemented

#### 14. Admin Access Not Secured
**Problem:**
- Any logged-in user can access admin panel
- No role-based access control
- Admin button visible to all authenticated users

**Impact:** Medium-High - Security concern
**Status:** Needs RBAC implementation

#### 15. Secret Key Hardcoded
**Problem:**
```python
SECRET_KEY = "supersecretkeyshouldbeinchangedinproduction"
```
- JWT secret is hardcoded
- Should be in environment variable

**Impact:** High - Security vulnerability
**Status:** Critical fix needed

---

## 🛠️ REQUIRED FIXES

### **Priority 1: Security Fixes** ⚡

1. **Move Secrets to Environment Variables**
```python
# backend/auth.py - CURRENT
SECRET_KEY = "supersecretkeyshouldbeinchangedinproduction"

# SHOULD BE
import os
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-dev-key")
```

2. **Implement Role-Based Access Control**
```python
# Add to User model
is_admin = Column(Boolean, default=False)

# Protect admin endpoints
@app.get("/admin/events")
def admin_only(current_user: User = Depends(get_current_admin)):
    pass
```

3. **Add HTTPS Enforcement**
```python
# For production
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
app.add_middleware(HTTPSRedirectMiddleware)
```

4. **Implement CSRF Protection**
- Add CSRF tokens for state-changing operations
- Use double-submit cookie pattern

---

### **Priority 2: Data Integrity & Maintenance** ✅
*Updated Feb 21, 2026*

1. **Implement Bulk Deletion of Past Events** ⚡
- Added `/admin/events/delete-past` endpoint.
- Added "🧹 Delete All Past" button to Admin Panel.

2. **AI-Powered Event Refinement** ⚡
- Added "✨ Refine" button in Admin Panel.
- Integrated `gemini-1.5-flash` to manually re-process specific events.

---

### **Priority 2: Data Integrity Fixes** ⚡

1. **Add Database Constraints**
```python
# models.py
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Feedback(Base):
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'))
    event = relationship("Event", back_populates="feedbacks")
```

2. **Implement Duplicate Detection**
```python
# Before inserting event
from difflib import SequenceMatcher

def is_duplicate(new_title, existing_titles, threshold=0.85):
    for title in existing_titles:
        ratio = SequenceMatcher(None, new_title.lower(), title.lower()).ratio()
        if ratio > threshold:
            return True
    return False
```

3. **Add Input Validation**
```python
from pydantic import BaseModel, validator

class EventCreate(BaseModel):
    title: str
    
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v
```

---

### **Priority 3: Performance Fixes** ⚡

1. **Implement Pagination**
```python
# backend/main.py
@app.get("/events/")
def get_events(skip: int = 0, limit: int = 20):
    events = db.query(Event).offset(skip).limit(limit).all()
    return events
```

2. **Add Image Optimization**
```python
from PIL import Image

def compress_image(image_path, max_size=(800, 600)):
    img = Image.open(image_path)
    img.thumbnail(max_size, Image.LANCZOS)
    img.save(image_path, optimize=True, quality=85)
```

3. **Implement Lazy Loading**
```javascript
// Frontend
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            observer.unobserve(img);
        }
    });
});
```

---

### **Priority 4: Functionality Fixes** ⚡

1. **Make API URL Configurable**
```javascript
// frontend/app.html
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://127.0.0.1:8000'
    : 'https://api.campusevents.com';
```

2. **Implement Rate Limiting**
```python
# backend/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/events/{event_id}/feedback")
@limiter.limit("3/minute")
def create_feedback(...):
    pass
```

3. **Add Event Archiving**
```python
from datetime import datetime, timedelta

def archive_past_events():
    cutoff = datetime.now() - timedelta(days=30)
    db.query(Event).filter(Event.created_at < cutoff).update({"archived": True})
```

---

## ✨ NEW FEATURES REQUIRED

### **Phase 1: Essential Features** 🌟

#### 1. **In-App Notification Center** 🔔
**Description:** A dedicated notification bell/panel within the app to show upcoming event alerts.
**Features:**
- Real-time "Toast" alerts for upcoming events.
- Persistence: A list of recent notifications accessible via a bell icon.
- Unread count badge.

**Implementation:**
```javascript
// Simple Frontend Polling or WebSockets
setInterval(async () => {
    const res = await fetch('/api/my-reminders');
    const alerts = await res.json();
    alerts.forEach(a => showNotification(a.title));
}, 60000);
```

**Benefits:**
- High visibility within the app context.
- Zero external dependency (no email/SMS costs).
- Immediate user action.

---

#### 4. **Advanced Search & Filters**
**Features:**
- Full-text search (title + description)
- Date range filtering
- Venue-based search
- Multi-category selection
- Sort by popularity/date

**Implementation:**
```python
from sqlalchemy import or_

@app.get("/events/search")
def search_events(
    q: str = None,
    category: List[str] = None,
    date_from: str = None,
    date_to: str = None
):
    query = db.query(Event)
    
    if q:
        query = query.filter(or_(
            Event.title.ilike(f'%{q}%'),
            Event.description.ilike(f'%{q}%')
        ))
    
    if category:
        query = query.filter(Event.category.in_(category))
    
    return query.all()
```

---

#### 5. **User Dashboard & Personalization**
**Features:**
- Saved/bookmarked events
- Event history
- Personalized recommendations
- Follow favorite clubs

**Database Schema:**
```python
class UserEventInteraction(Base):
    __tablename__ = "user_events"
    user_id = Column(Integer, ForeignKey('users.id'))
    event_id = Column(Integer, ForeignKey('events.id'))
    action = Column(String)  # 'saved', 'attended', 'interested'
```

---

### **Phase 2: Advanced Features** 🚀

#### 6. **AI-Powered Recommendations**
**Description:** ML-based event suggestions
**Algorithm:** Collaborative filtering + Content-based
**Features:**
- "Events you might like"
- Similar event suggestions
- Trending events

**Implementation:**
```python
from sklearn.metrics.pairwise import cosine_similarity

def recommend_events(user_id):
    user_history = get_user_interactions(user_id)
    similar_users = find_similar_users(user_id)
    recommended = get_events_liked_by_similar_users(similar_users)
    return recommended[:5]
```

---

#### 6. **Club Subscription ("Follow Club")** 🆕
**Description:** Users can follow specific clubs to get notified of new events automatically.
**Features:**
- "Follow" button on Event Details and Club filters.
- Automatic email/push notification when a followed club posts a new event.
- Subscription management in User Dashboard.

**Database Schema:**
```python
class ClubSubscription(Base):
    __tablename__ = "club_subscriptions"
    user_id = Column(Integer, ForeignKey('users.id'))
    club_name = Column(String)
```

---

#### 7. **The Reminder System (In-App Only)** 🔔
**Vision:** Keep users engaged without leaving the platform.
1. **Event Reminders:** (User clicks 'Set Reminder' on a specific event)
   - Background task flags reminders due soon.
   - App shows a slide-in "Upcoming Event" alert while the user is browsing.
2. **Subscription Alerts:** (User follows a club)
   - New events from followed clubs appear in the Notification bell area instantly.

---

#### 8. **Real-Time Updates**
**Description:** WebSocket-based live updates
**Technology:** FastAPI WebSockets
**Features:**
- Live event additions
- Real-time feedback updates
- Attendance counters

**Implementation:**
```python
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Event updated: {data}")
```

---

#### 8. **QR Code Check-In System**
**Description:** Generate QR codes for event attendance
**Features:**
- Unique QR per event
- Scan to mark attendance
- Analytics on attendance

**Implementation:**
```python
import qrcode

@app.get("/events/{id}/qr")
def generate_qr(id: int):
    qr = qrcode.make(f"https://campusevents.com/checkin/{id}")
    qr.save(f"qr_{id}.png")
    return FileResponse(f"qr_{id}.png")
```

---

#### 9. **Gamification System**
**Description:** Points, badges, leaderboards
**Features:**
- Points for attendance
- Badges for achievements
- Leaderboard for top attendees
- Rewards and incentives

**Database Schema:**
```python
class UserPoints(Base):
    user_id = Column(Integer, ForeignKey('users.id'))
    points = Column(Integer, default=0)
    badges = Column(JSON)  # List of earned badges
```

---

#### 10. **Enhanced Analytics Dashboard**
**Features:**
- Club-wise analytics
- Attendance trends over time
- Category popularity
- Peak event times
- Geographic heatmaps

**Metrics to Track:**
- Event views
- Click-through rates
- Registration conversions
- Feedback scores
- Engagement rates

---

### **Phase 3: Enterprise Features** 💼

#### 11. **Multi-Campus Support**
**Description:** Support multiple universities
**Features:**
- Campus selection on homepage
- Campus-specific events
- Cross-campus events

---

#### 12. **Event Ticketing System**
**Description:** Integrated ticket booking
**Features:**
- Paid event support
- Payment gateway (Razorpay/Stripe)
- E-ticket generation
- Refund management

---

#### 13. **Sponsor Management**
**Description:** Track event sponsors
**Features:**
- Sponsor profiles
- Sponsorship tiers
- ROI analytics for sponsors

---

#### 14. **Mobile App**
**Technology:** React Native or Flutter
**Features:**
- Native push notifications
- Offline mode
- Camera integration for QR scanning

---

## 📊 FEATURE PRIORITY MATRIX

| Feature | Priority | Effort | Impact | Timeline |
|---------|----------|--------|--------|----------|
| Secret Key Fix | Critical | Low | High | 1 day |
| RBAC Implementation | High | Medium | High | 3 days |
| Rate Limiting | High | Low | Medium | 1 day |
| Pagination | High | Low | High | 2 days |
| Image Optimization | Medium | Medium | Medium | 3 days |
| In-App Notifications| High | Medium | High | 4 days |
| Pagination | High | Low | High | 2 days |
| Image Optimization | Medium | Medium | Medium | 3 days |
| Club Following | Medium | High | High | 1 week |
| Advanced Search | Medium | Medium | High | 5 days |
| Advanced Search | Medium | Medium | High | 5 days |
| AI Recommendations | Low | Very High | Medium | 3 weeks |
| Mobile App | Low | Very High | High | 2 months |

---

## 🎯 RECOMMENDED ACTION PLAN

### **Week 1: Critical Fixes**
- [ ] Move secrets to .env file
- [ ] Implement RBAC for admin
- [ ] Add database constraints
- [ ] Configure rate limiting
- [ ] Fix API URL hardcoding

### **Week 2: Performance**
- [ ] Implement pagination
- [ ] Optimize images
- [ ] Add lazy loading
- [ ] Improve error handling

### **Week 3: Essential Features**
- [ ] Email notification system
- [ ] Calendar integration
- [ ] Advanced search
- [ ] Event archiving

### **Week 5: Sync & Optimization**
- [ ] Implement scheduled Task (Cron) for Scraper
- [ ] Add "Sync Now" button to Admin UI
- [ ] Optimize images on download
- [ ] Finalize RBAC for multiple admin roles

---

**Last Updated:** February 21, 2026
**Status:** AI-Refinement & Social Sharing Features Live
