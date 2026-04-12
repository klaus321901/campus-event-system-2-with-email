
import os
import sys
from datetime import datetime
import re

# Setup path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from backend.database import SessionLocal
from backend import models

def smart_parse_date(text):
    if not text: return None
    text = text.lower()
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    
    # Pattern 1: ISO style (2025-12-18)
    iso_match = re.search(r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})', text)
    if iso_match:
        return datetime(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))

    # Pattern 2: Month Day (March 15 or Mar 15)
    m1 = re.search(r'(\bjan[a-z]*|feb[a-z]*|mar[a-z]*|apr[a-z]*|may|jun[a-z]*|jul[a-z]*|aug[a-z]*|sep[a-z]*|oct[a-z]*|nov[a-z]*|dec[a-z]*)\s*(\d{1,2})', text)
    if m1:
        m_idx = months.index(m1.group(1)[:3]) + 1
        d = int(m1.group(2))
        year = 2026 if m_idx <= 6 else 2025 # Heuristic for MJCET academic year
        return datetime(year, m_idx, d)

    # Pattern 3: Day Month (15th March or 15 Mar)
    m2 = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?(\bjan[a-z]*|feb[a-z]*|mar[a-z]*|apr[a-z]*|may|jun[a-z]*|jul[a-z]*|aug[a-z]*|sep[a-z]*|oct[a-z]*|nov[a-z]*|dec[a-z]*)', text)
    if m2:
        m_idx = months.index(m2.group(2)[:3]) + 1
        d = int(m2.group(1))
        year = 2026 if m_idx <= 6 else 2025
        return datetime(year, m_idx, d)

    return None

def force_verify_offline():
    db = SessionLocal()
    try:
        unverified = db.query(models.Event).filter(models.Event.event_date == None).all()
        print(f"🔍 Found {len(unverified)} events needing verification. Using Offline Heuristics...")
        
        fixed_count = 0
        for event in unverified:
            # Try parsing from both date_str and description
            date_to_fix = smart_parse_date(event.date_str) or smart_parse_date(event.description)
            
            if date_to_fix:
                event.event_date = date_to_fix
                db.commit()
                print(f"✅ Verified: {event.title} -> {date_to_fix.date()}")
                fixed_count += 1
            else:
                print(f"❓ Could not find clear date for: {event.title}")
                
        print(f"\n🎉 Offline process complete! Fixed {fixed_count} events.")
    finally:
        db.close()

if __name__ == "__main__":
    force_verify_offline()
