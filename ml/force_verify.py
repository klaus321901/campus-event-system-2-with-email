
import os
import sys
from datetime import datetime

# Setup path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from backend.database import SessionLocal
from backend import models
from ml.gemini_refiner import refine_event_with_gemini

def fix_all_dates():
    db = SessionLocal()
    try:
        # Find events where event_date is missing but we have an image
        unverified_events = db.query(models.Event).filter(
            (models.Event.event_date == None) | (models.Event.venue == None)
        ).all()
        
        print(f"🔍 Found {len(unverified_events)} events that need date/venue verification.")
        
        # Flag to stop trying AI if we hit a quota limit
        ai_blocked = False
        
        for event in unverified_events:
            print(f"✨ Verifying: {event.title}...")
            
            # STEP 1: Try offline parsing first
            parsed_locally = False
            
            # Sub-Step A: Existing ISO strings
            if event.date_str:
                try:
                    raw_str = event.date_str.split('.')[0] if '.' in event.date_str else event.date_str
                    clean_date = datetime.strptime(raw_str, "%Y-%m-%d %H:%M:%S")
                    event.event_date = clean_date
                    parsed_locally = True
                    print(f"✅ Success (Offline): Fixed via ISO string.")
                except: pass

            # Sub-Step B: Enhanced Heuristics (Regex for many patterns)
            if not parsed_locally and event.description:
                import re
                desc = event.description.lower()
                
                # Pattern 1: Month Day (March 15)
                m1 = re.search(r'(\bjan[a-z]*|feb[a-z]*|mar[a-z]*|apr[a-z]*|may|jun[a-z]*|jul[a-z]*|aug[a-z]*|sep[a-z]*|oct[a-z]*|nov[a-z]*|dec[a-z]*)\s*(\d{1,2})', desc)
                # Pattern 2: Day Month (15th March, 15 March)
                m2 = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?(\bjan[a-z]*|feb[a-z]*|mar[a-z]*|apr[a-z]*|may|jun[a-z]*|jul[a-z]*|aug[a-z]*|sep[a-z]*|oct[a-z]*|nov[a-z]*|dec[a-z]*)', desc)
                # Pattern 3: DD/MM (15/03 or 15-03)
                m3 = re.search(r'(\d{1,2})[/\-](\d{1,2})', desc)

                res = m1 or m2 or m3
                if res:
                    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
                    try:
                        if m1:
                            m_idx = months.index(m1.group(1)[:3]) + 1
                            d = int(m1.group(2))
                        elif m2:
                            m_idx = months.index(m2.group(2)[:3]) + 1
                            d = int(m2.group(1))
                        else: # m3
                            d = int(m3.group(1))
                            m_idx = int(m3.group(2))
                            if m_idx > 12: # Swap if it looks like MM/DD
                                d, m_idx = m_idx, d
                        
                        year = 2026 if m_idx >= 1 else 2025 # Heuristic: default 2026 for upcoming
                        event.event_date = datetime(year, m_idx, d)
                        parsed_locally = True
                        print(f"✅ Success (Heuristic): Extracted {year}-{m_idx}-{d}")
                    except: pass

            if parsed_locally:
                db.commit()
                continue

            # STEP 2: Use AI ONLY if quota is healthy and local failed
            # ALSO: Skip AI for simple date events to save your key's quota
            if not ai_blocked:
                # If heuristic found it was 2025, we don't need AI verification to unlock it
                if parsed_locally: 
                    continue
                    
                print(f"🤖 Calling AI for legacy check...")
                try:
                    refined = refine_event_with_gemini(event.image_path, event.description)
                    if refined and refined.get("event_date"):
                        event.event_date = datetime.strptime(refined["event_date"], "%Y-%m-%d")
                        db.commit()
                        print(f"✅ Success: AI verified.")
                    else:
                        print(f"❌ Gemini couldn't find a date.")
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        print(f"🛑 Quota Blocked. Switching to Offline-Only mode.")
                        ai_blocked = True
                    else:
                        print(f"❌ Gemini failed: {e}")
            else:
                if not parsed_locally:
                    print(f"⏭️ Skipping AI (Blocked). Event remains unverified.")
                
        print("\n🎉 Verification process complete!")
    finally:
        db.close()

if __name__ == "__main__":
    fix_all_dates()
