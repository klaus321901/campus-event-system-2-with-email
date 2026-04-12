import json
import re
import os

# Keywords to filter out (member announcements, not events)
FILTER_OUT_KEYWORDS = [
    "new gb", "new execom", "new core", "new members", "new team",
    "welcome team", "meet the team", "introducing", "core members",
    "executive committee", "governing body", "new leads", "team announcement",
    "vice chair", "secretary", "treasurer", "president", "professional vice",
    "strategic professional", "our dedicated", "bridges industry", "empowering every member"
]

def is_member_announcement(text):
    """Check if the post is about member announcements (not an event)"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in FILTER_OUT_KEYWORDS)

def extract_date(text):
    """Extract date from text using regex"""
    date_patterns = [
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*",
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})",
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None

def extract_time(text):
    """Extract time from text"""
    time_pattern = r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)"
    match = re.search(time_pattern, text, re.IGNORECASE)
    if match:
        return match.group(0)
    return None

def extract_registration_link(text):
    """Extract registration link from text"""
    link_pattern = r"(https?://[^\s]+)|(bit\.ly/[^\s]+)|(tinyurl\.com/[^\s]+)|(forms\.gle/[^\s]+)"
    match = re.search(link_pattern, text)
    if match:
        return match.group(0)
    return None

def extract_deadline(text):
    """Extract registration deadline"""
    deadline_pattern = r"(?:register by|deadline|last date|before)\s*[:\-]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)"
    match = re.search(deadline_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def extract_venue(text):
    """Extract venue from text"""
    text_lower = text.lower()
    
    # Common venue keywords
    venue_keywords = {
        "auditorium": "Auditorium",
        "audi": "Auditorium",
        "seminar hall": "Seminar Hall",
        "conference hall": "Conference Hall",
        "lab": "Computer Lab",
        "computer lab": "Computer Lab",
        "ground": "Sports Ground",
        "playground": "Sports Ground",
        "cafeteria": "Cafeteria",
        "canteen": "Canteen",
        "library": "Library",
        "classroom": "Classroom",
        "online": "Online",
        "zoom": "Online (Zoom)",
        "google meet": "Online (Google Meet)",
        "teams": "Online (MS Teams)"
    }
    
    # Check for specific venue mentions
    for keyword, venue_name in venue_keywords.items():
        if keyword in text_lower:
            return venue_name
    
    # Try to extract venue with "at" or "venue:" pattern
    venue_pattern = r"(?:at|venue|location)[:\s]+([A-Za-z\s]+?)(?:\.|,|\n|$)"
    match = re.search(venue_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return "MJCET Campus"  # Default

    return "General"

def analyze_sentiment(text):
    """Analyze the 'vibe' of the event text."""
    text_lower = text.lower()
    
    # Hype/Exciting
    hype_words = ["🔥", "🚀", "amazing", "exciting", "grand", "hype", "don't miss", "unforgettable", "ultimate", "win", "prizes"]
    # Professional/Formal
    formal_words = ["seminar", "workshop", "learn", "insightful", "professional", "industry", "certification", "knowledge", "career"]
    
    hype_score = sum(1 for word in hype_words if word in text_lower)
    formal_score = sum(1 for word in formal_words if word in text_lower)
    
    if hype_score > formal_score:
        return "High Energy / Hype"
    elif formal_score > hype_score:
        return "Professional / Informative"
    else:
        return "Casual / Community"

def get_style_suggestion(category, sentiment):
    """Suggest a UI style based on category and sentiment."""
    if "Hype" in sentiment:
        return "Vibrant Gradient / Pulse Animation"
    if "Professional" in sentiment:
        return "Clean Minimalist / Soft Blue Accent"
    if category == "Technical":
        return "Matrix/Cyberpunk Subtle Glow"
    return "Standard Glassmorphism"

def process_events():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    input_file = os.path.join(data_dir, "extracted_events.json")
    output_file = os.path.join(data_dir, "final_events.json")

    if not os.path.exists(input_file):
        print("No extracted text found. Run OCR first!")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    processed_events = []
    filtered_count = 0
    print(f"Processing {len(events)} events for NLP extraction...")

    for event in events:
        full_text = event.get("full_content", "")
        
        # FILTER OUT member announcements
        if is_member_announcement(full_text):
            print(f"  ⚠️  Filtered out member announcement from {event['username']}")
            filtered_count += 1
            continue
        
        # Extract details
        event_date = extract_date(full_text)
        event_time = extract_time(full_text)
        category = classify_event(full_text)
        venue = extract_venue(full_text)
        
        # Use QR code link if available, otherwise try to extract from text
        registration_link = event.get("registration_link") or extract_registration_link(full_text)
        deadline = extract_deadline(full_text)
        
        # Use full text as description (cleaned up)
        description = full_text.replace("\n", " ").strip()
        
        # New: Sentiment and Styling
        sentiment = analyze_sentiment(full_text)
        style_hint = get_style_suggestion(category, sentiment)

        processed_events.append({
            "title": f"{category} Event by {event['username']}",
            "club": event['username'],
            "date": event_date,
            "time": event_date,
            "venue": venue,
            "category": category,
            "description": description,
            "image_url": event.get("image_path"),
            "profile_pic": event.get("profile_pic_url"),
            "original_link": event.get("post_url"),
            "registration_link": registration_link,
            "last_register_date": deadline,
            "sentiment": sentiment,
            "style_hint": style_hint
        })

    # Save final structured data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_events, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ NLP Processing complete!")
    print(f"   Processed: {len(processed_events)} events")
    print(f"   Filtered out: {filtered_count} member announcements")
    print(f"   Saved to: {output_file}")

import datetime

def parse_date_to_datetime(date_str):
    """Helper to convert string date to datetime object."""
    if not date_str:
        return None
    
    current_year = datetime.datetime.now().year
    
    # Try different formats
    formats = [
        "%d %B",       # "20 November"
        "%d %b",       # "20 Nov"
        "%b %d",       # "Nov 20"
        "%B %d",       # "November 20"
        "%d/%m/%Y",    # "20/11/2023"
        "%d-%m-%Y",    # "20-11-2023"
        "%Y-%m-%d"     # "2023-11-20"
    ]
    
    date_str = date_str.strip()
    
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            # If year wasn't in format, it defaults to 1900. Set to current/next year.
            if dt.year == 1900:
                dt = dt.replace(year=current_year)
                # If the date has already passed this year, assume it's for next year (for campus events usually)
                # But let's keep it current year for now as most events are upcoming.
            return dt
        except:
            continue
            
    return None

def process_events_to_db(db):
    """Sync processed events and their parsed dates to the database."""
    from backend import models
    events = db.query(models.Event).filter(models.Event.event_date == None).all()
    
    count = 0
    for event in events:
        if event.date_str:
            # Basic extraction if not already done
            extracted_date = extract_date(event.description) if not event.date_str else event.date_str
            dt = parse_date_to_datetime(extracted_date)
            if dt:
                event.event_date = dt
                count += 1
    
    db.commit()
    print(f"Updated {count} events with verified dates.")
