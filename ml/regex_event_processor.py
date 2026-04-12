import json
import re
import os
from datetime import datetime

# Configure Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_FILE = os.path.join(DATA_DIR, "scraped_data.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "processed_events.json")

# Keywords to filter out (non-events)
FILTER_OUT_KEYWORDS = [
    "new gb", "new execom", "new core", "new members", "new team",
    "welcome team", "meet the team", "introducing", "core members",
    "executive committee", "governing body", "new leads", "team announcement",
    "vice chair", "secretary", "treasurer", "president", "recruitment", "hiring"
]

def is_member_announcement(text):
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
            # Normalize to YYYY-MM-DD (simulated for now)
            found = match.group(0)
            return found # Return raw string for now
    return None

def extract_venue(text):
    venue_keywords = {
        "auditorium": "Auditorium", "seminar hall": "Seminar Hall", "lab": "Computer Lab",
        "online": "Online", "zoom": "Online (Zoom)", "meet": "Online (Google Meet)"
    }
    text_lower = text.lower()
    for keyword, venue_name in venue_keywords.items():
        if keyword in text_lower:
            return venue_name
    return "MJCET Campus"

def extract_category(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["hackathon", "coding", "workshop", "ai", "tech"]): return "Technical"
    if any(w in text_lower for w in ["dance", "music", "fest", "dj"]): return "Cultural"
    if any(w in text_lower for w in ["cricket", "sports", "game"]): return "Sports"
    return "General"

def process_regex():
    if not os.path.exists(INPUT_FILE):
        print("[ERROR] No scraped data found.")
        return

    with open(INPUT_FILE, "r") as f:
        posts = json.load(f)

    print(f"[NLP] Processing {len(posts)} posts using Local Regex (No AI)...")
    processed_events = []

    for post in posts:
        caption = post.get("caption", "")
        
        if is_member_announcement(caption):
            continue

        # Extract details locally
        event_date = extract_date(caption)
        venue = extract_venue(caption)
        category = extract_category(caption)
        
        # Extract QR Code Link if available
        qr_link = None
        if "images" in post:
            for img in post["images"]:
                if img.get("qr_link"):
                    qr_link = img["qr_link"]
                    break

        # Structure matches what db_sync.py expects in "extracted"
        details = {
            "title": f"{category} Event by @{post['username']}",
            "event_date": event_date if event_date else "TBA",
            "event_time": "10:00 AM",
            "venue": venue,
            "description": caption[:150] + "...",
            "category": category,
            "registration_link": qr_link,
            "last_register_date": None
        }

        processed_events.append({
            **post,
            "extracted": details
        })

    with open(OUTPUT_FILE, "w") as f:
        json.dump(processed_events, f, indent=4)
        
    print(f"\n[SUCCESS] Regex Processing complete! {len(processed_events)} events ready for DB.")

if __name__ == "__main__":
    process_regex()
