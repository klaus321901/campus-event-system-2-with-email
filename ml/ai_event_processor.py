import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env")
load_dotenv(dotenv_path)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("[ERROR] GEMINI_API_KEY not found in .env file.")
else:
    genai.configure(api_key=api_key)

# Configure Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_FILE = os.path.join(DATA_DIR, "scraped_data.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "processed_events.json")

def clean_json_text(text):
    """Remove markdown code blocks from AI response."""
    text = text.replace("```json", "").replace("```", "").strip()
    return text

def extract_event_details(caption, club_name):
    """Use Gemini to extract structured data from Instagram caption."""
    if not api_key:
        return None
        
    # Try models confirmed to be available in the user's region
    model_names = [
        "gemini-2.0-flash", 
        "gemini-2.5-flash", 
        "gemini-flash-latest", 
        "gemini-pro-latest"
    ]
    
    model = None
    for name in model_names:
        try:
            m = genai.GenerativeModel(name)
            # No test call here to save quota
            model = m
            # print(f"  [INFO] Selected Model: {name}")
            break
        except:
            continue
            
    if not model:
        print("[ERROR] No models available.")
        return None

    prompt = f"""
    You are an expert event data analyzer. I have an Instagram caption from a college club called '{club_name}'. 
    Extract the following details in JSON format only. If a detail is missing, put null.
    
    Fields:
    - title: A short, catchy title for the event.
    - event_date: The date of the event in YYYY-MM-DD format. (Infer year 2025/2026 based on context).
    - event_time: The time of the event (e.g., 10:00 AM).
    - venue: The exact location or hall.
    - description: A clear 2-sentence summary of what the event is about.
    - category: Choose one: [Technical, Cultural, Sports, Workshop, Seminar, Other].
    - registration_link: Extract if present.
    - last_register_date: The deadline in YYYY-MM-DD format if present.

    Caption:
    \"\"\"{caption}\"\"\"

    Response Format (JSON only):
    {{
        "title": "...",
        "event_date": "...",
        "event_time": "...",
        "venue": "...",
        "description": "...",
        "category": "...",
        "registration_link": "...",
        "last_register_date": "..."
    }}
    """
    
    retries = 3
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            cleaned_text = clean_json_text(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            if "429" in str(e):
                print(f"  [WAIT] Rate limit hit (429). Sleeping for 30s to cooldown... (Attempt {attempt+1}/{retries})")
                time.sleep(32) # Wait slightly more than 30s
                continue
            else:
                print(f"[ERROR] Extraction failed: {e}")
                return None
    return None

def process_all_posts():
    """Process existing scraped data and save results incrementally."""
    if not os.path.exists(INPUT_FILE):
        print("[ERROR] No scraped data found at", INPUT_FILE)
        return

    with open(INPUT_FILE, "r") as f:
        posts = json.load(f)

    # Load existing processed events to prevent re-processing
    processed_events = []
    processed_urls = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                processed_events = json.load(f)
                processed_urls = {p["post_url"] for p in processed_events}
            print(f"[RESUME] Found {len(processed_events)} already processed events. Skipping them.")
        except:
            print("[INFO] Could not read existing output file. Starting fresh.")

    print(f"[AI] Processing remaining posts out of {len(posts)} total...")
    
    count = 0
    for idx, post in enumerate(posts):
        if post["post_url"] in processed_urls:
            continue
            
        print(f"[{idx+1}/{len(posts)}] Extracting details for @{post['username']}...")
        
        # Call Gemini
        details = extract_event_details(post['caption'], post['username'])
        
        if details:
            # Combine raw data with AI results
            event_entry = {
                **post,
                "extracted": details
            }
            processed_events.append(event_entry)
            processed_urls.add(post["post_url"])
            count += 1
            
            # Save every 5 posts to avoid data loss
            if count % 5 == 0:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(processed_events, f, indent=4)
                print(f"  [SAVE] Progress saved ({len(processed_events)} total).")
                
        else:
            print(f"  [SKIPPED] AI failed for {post['post_url']}")
            
        # Pacing to avoid hitting rate limits too fast
        time.sleep(4) 

    # Final Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(processed_events, f, indent=4)
        
    print(f"\n[SUCCESS] AI Extraction complete! Total processed: {len(processed_events)}")
    print(f"[SUCCESS] Results saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    process_all_posts()
