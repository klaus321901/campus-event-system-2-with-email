import time
import json
import os
import requests
import random
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pyzbar.pyzbar import decode
import cv2
import numpy as np

# Adjust path to import from ml
# The scraper folder is a sibling of ml
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.gemini_refiner import refine_event_with_gemini, transcribe_audio
import yt_dlp

# ---------------- CONFIGURATION ---------------- #
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
JSON_FILE = os.path.join(DATA_DIR, "scraped_data.json")
# NEW: Path for saving Chrome profile (sessions/cookies)
CHROME_PROFILE_DIR = os.path.join(DATA_DIR, "chrome_profile")

# Create directories if they don't exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)

# --- LOGGING SETUP ---
# Mirrored log so Antigravity can read the current status directly
LOG_FILE = os.path.join(DATA_DIR, "scraper.log")

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        # Overwrite file each run to save disk space
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger(LOG_FILE)

# PART 2: Remaining Clubs (Horizon, IEEE, AWS, ACM)
TARGET_ACCOUNTS = [
    "horizon.mjcet", "ieeemjcet_cis", "ieeecsmjcet", 
    "ieee.wie.mjcet", "ieeesmcmjcet", "awsclub.mjcet", "mjcet_acm"
]

# Keywords to SKIP (Non-event posts)
SKIP_KEYWORDS = [
    "thank you", "farewell", "happy birthday", "hb ", "congratulations",
    "achievement", "alumni", "gb meeting", "general body",
    "execom", "portfolio", "core member", "core team", "recruitment",
    "welcome to the club", "induction", "member spotlight",
    "volunteer", "recognition", "felicitation", "certificates", "certificate distribution",
    "meet the team", "introducing", "our team", "team reveal", 
    "glimpse", "highlights", "recap", "concluded", "success of", "memories", "throwback"
]

# Keywords that POSITIVELY identify an event
EVENT_INDICATORS = [
    "register", "link in bio", "join us", "venue", "date:", "workshop", 
    "session", "contest", "hackathon", "competition", "seminar", 
    "registration", "webinar", "bootcamp", "hack", "fest", "symposium",
    "conference", "meetup", "event", "summit", "challenge", "hack", "grand prize",
    "prize pool", "cash prize", "orientation"
]

def setup_driver():
    # Create directories if they don't exist
    os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
    
    # NEW: Clear Lock files to prevent "SessionNotCreated" error
    lock_files = ["SingletonLock", "Lock"]
    for lock in lock_files:
        lock_path = os.path.join(CHROME_PROFILE_DIR, lock)
        if os.path.exists(lock_path):
            try: os.remove(lock_path)
            except: pass

    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Enable Persistent Session
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    
    # Stability Flags
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-extensions")
    options.add_argument("--proxy-server='direct://'")
    options.add_argument("--proxy-bypass-list=*")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    
    # Anti-detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Stealth mechanism
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Could not start Chrome: {e}")
        print("💡 TIP: Make sure ALL Chrome windows are closed before running the scraper.")
        sys.exit(1)

def load_existing_data():
    """Load existing scraped data from JSON."""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_data(data):
    """Save scraped data to JSON."""
    try:
        with open(JSON_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Failed to save JSON: {e}")

def download_image(url, username, timestamp, index):
    """Download image and return local path."""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            ts_numeric = int(time.time())
            filename = f"{username}_{ts_numeric}_{index}.jpg"
            filepath = os.path.join(IMAGES_DIR, filename)
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return filepath
    except Exception as e:
        print(f"[ERROR] Failed to download image: {e}")
    return None

def download_reel_audio(reel_url, username, timestamp):
    """Download audio from a reel using yt-dlp."""
    try:
        audio_dir = os.path.join(DATA_DIR, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        safe_ts = timestamp.replace(":", "-").split(".")[0]
        output_filename = f"{username}_{safe_ts}_audio"
        output_path = os.path.join(audio_dir, output_filename)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([reel_url])
            
        final_path = output_path + ".mp3"
        if os.path.exists(final_path):
            return final_path
    except Exception as e:
        print(f"  [DEBUG] Audio download skipped/failed: {str(e)[:100]}")
    return None

def extract_qr_link(image_path):
    """Scan image for QR codes with pre-processing for better detection."""
    try:
        if not image_path or not os.path.exists(image_path):
            return None
        
        img = cv2.imread(image_path)
        if img is None: return None
        
        # 1. Try standard scan
        decoded_objects = decode(img)
        
        # 2. If fail, try Grayscale + Thresholding (boosts detection for noisy posters)
        if not decoded_objects:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            decoded_objects = decode(thresh)
            
        for obj in decoded_objects:
            qr_data = obj.data.decode("utf-8")
            if "http" in qr_data:
                return qr_data
    except Exception as e:
        print(f"  [DEBUG] QR Scan error: {e}")
    return None

def is_event_post(caption, is_reel=False):
    """Filter out noise, but be more lenient for Reels since they have audio cues."""
    if not caption or caption == "No Caption":
        return is_reel # For reels, process anyway even if caption fails
    
    caption_lower = caption.lower()
    
    # 1. Check for Skip Keywords (but allow recruitment/hiring if it's an event too)
    for kw in SKIP_KEYWORDS:
        if kw in caption_lower:
            return False
            
    # 2. If it's a Reel, we lean towards YES (they usually have dates spoken)
    if is_reel and len(caption_lower) > 5:
        return True

    # 3. Check for positive indicators
    return any(indicator in caption_lower for indicator in EVENT_INDICATORS)

def scrape_instagram():
    """Main scraping process."""
    driver = setup_driver()
    
    try:
        driver.get("https://www.instagram.com/")
        print("\n" + "="*50)
        print("LOGIN MODE: Please log in to Instagram in the browser window.")
        print("Note: Your login will be SAVED to 'data/chrome_profile'.")
        print("Once you are fully logged in and see your feed,")
        print("press ENTER in this terminal to start scraping...")
        print("="*50 + "\n")
        input() 

        scraped_data = load_existing_data()  # kept only for JSON backup logging

        for username in TARGET_ACCOUNTS:
            # --- SELF-HEALING: Check if browser is still alive ---
            try:
                _ = driver.current_url
            except:
                print("  [SYSTEM] Browser lost connection. Re-initializing...")
                try: driver.quit()
                except: pass
                driver = setup_driver()
                driver.get("https://www.instagram.com/")
                time.sleep(5)
            
            # REST PERIOD: Long sleep between clubs to look human
            wait_time = random.uniform(15, 30)
            print(f"  [STEALTH] Resting for {wait_time:.1f}s before next club...")
            time.sleep(wait_time)
            
            print(f"\n--- Scraping @{username} ---")
            try:
                driver.get(f"https://www.instagram.com/{username}/")
                time.sleep(random.uniform(7, 12))

                # Get profile pic
                try:
                    profile_pic = driver.find_element(By.CSS_SELECTOR, "header img")
                    profile_pic_url = profile_pic.get_attribute("src")
                except:
                    profile_pic_url = None

                # Find post links - target the main grid area specifically
                try:
                    # Wait for the grid to appear
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//main"))
                    )
                    main_grid = driver.find_element(By.TAG_NAME, "main")
                    links = main_grid.find_elements(By.TAG_NAME, "a")
                except:
                    links = driver.find_elements(By.TAG_NAME, "a")

                post_links = []
                for a in links:
                    href = a.get_attribute("href")
                    # Only capture posts/reels that belong to THIS club's account
                    if href and ("/p/" in href or "/reel/" in href) and f"/{username}/" in href:
                        post_links.append(href)
                
                # Top 6 (More efficient - catches current & last week's events)
                post_links = list(dict.fromkeys(post_links))[:6]

                for post_url in post_links:
                    try:
                        from backend.database import SessionLocal
                        from backend import models
                        db_check = SessionLocal()
                        
                        is_retry = False
                        # 1. Check by exact URL
                        exists = db_check.query(models.Event).filter(models.Event.source_url == post_url).first()
                        
                        # 2. If not found, check if this club already had an event with 'TBA' date (Smart Repair)
                        if not exists:
                            # event_date is DateTime, date_str is String. Check both appropriately.
                            exists = db_check.query(models.Event).filter(
                                models.Event.club_name == username,
                                (models.Event.event_date == None) | (models.Event.date_str == "TBA")
                            ).first()

                        if exists:
                            if exists.event_date is None or exists.event_date == "TBA":
                                print(f"  [🛠️ REPAIR RUN] Found existing event with missing date: {exists.title}. Re-scanning...")
                                is_retry = True 
                            else:
                                print(f"  [SKIP] Already in DB: {exists.title}")
                                db_check.close()
                                continue
                        db_check.close()
                    except Exception as de:
                        print(f"  [DEBUG] DB Check Error: {de}")
                        is_retry = False
                        # If DB fails, assume we keep going to avoid stopping the whole script

                    print(f"  [NEW] Found new post: {post_url}")
                    
                    try:
                        driver.get(post_url)
                        time.sleep(random.uniform(4, 6))
                    except Exception as ge:
                        print(f"  [ERROR] Could not load post URL: {ge}")
                        continue
                    
                    # Extract FULL Caption (More resilient "more" button click)
                    try:
                        more_found = False
                        # Try multiple times to click 'more' as it can be flaky
                        for attempt in range(2):
                            more_selectors = [
                                "//span[text()='more']",
                                "//div[text()='more']",
                                "//button[text()='more']",
                                "//span[contains(text(), '... more')]",
                                "//div[contains(@class, 'more-button')]",
                                "//span[contains(@class, 'x1lliihq x1plvlek xry7m6i x1n2onr6 x193iq5w xeuugli x1fj9vxn x1q0g3np x168nmei x13lgm6o x1qs7sk7 x17zs8z x1al4hlz x1pq812k x1xx24z5 x1yc453h x126k92a')]" # Generic IG 'more' span class
                            ]
                            for selector in more_selectors:
                                buttons = driver.find_elements(By.XPATH, selector)
                                if buttons:
                                    for btn in buttons:
                                        try:
                                            if btn.is_displayed():
                                                driver.execute_script("arguments[0].click();", btn)
                                                time.sleep(1.0)
                                                more_found = True
                                                break
                                        except: continue
                                if more_found: break
                            if more_found: break
                            time.sleep(1) # Wait and try again if not found
                    except Exception as me: 
                        print(f"  [DEBUG] More button issue: {me}")

                    caption = "No Caption"
                    try:
                        # Try to find the container (article, main div, or specific classes)
                        container = None
                        selectors = [
                            (By.TAG_NAME, "article"),
                            (By.XPATH, "//div[@role='main']"),
                            (By.XPATH, "//section"),
                            (By.XPATH, "//div[contains(@class, '_aa-h')]")
                        ]
                        
                        for by, val in selectors:
                            try:
                                container = driver.find_element(by, val)
                                if container: break
                            except: continue
                            
                        if not container:
                            print("  [DEBUG] Standard containers not found, using driver root.")
                            container = driver
                        
                        # Strategy 1: The standard H1 (Accessibility best practice for IG)
                        h1_elements = container.find_elements(By.TAG_NAME, "h1")
                        if h1_elements:
                            caption = h1_elements[0].text.strip()
                        
                        # Strategy 2: Largest Text Span (For when H1 is missing)
                        if caption == "No Caption" or len(caption) < 20:
                            # Search for spans with auto direction inside the container
                            spans = container.find_elements(By.XPATH, ".//span[@dir='auto']")
                            for s in spans:
                                text = s.text.strip()
                                # Ignore small meta-data or navigation text
                                if len(text) > len(caption) and "View all" not in text and "likes" not in text:
                                    caption = text
                        
                        # Strategy 3: Image Alt Text (Instagram generates this from the caption)
                        if caption == "No Caption" or len(caption) < 10:
                            img_elems = container.find_elements(By.TAG_NAME, "img")
                            for img in img_elems:
                                alt = img.get_attribute("alt")
                                if alt and len(alt) > 50:
                                    # Alt text often starts with the caption and ends with "Photo by..."
                                    clean_alt = alt.split("Photo by")[0].strip() if "Photo by" in alt else alt
                                    if len(clean_alt) > len(caption):
                                        caption = clean_alt
                                        break

                        # Strategy 4: Fallback to Page Title (Often contains the truncated caption)
                        if caption == "No Caption":
                            page_title = driver.title
                            if page_title and "on Instagram:" in page_title:
                                caption = page_title.split("on Instagram:")[1].split("|")[0].strip()

                    except Exception as ce:
                        print(f"  [ERROR] Caption extraction failure: {ce}")
                    
                    # For reels or RETRIES, we ALWAYS proceed.
                    is_reel = ("/reel/" in post_url)
                    if not is_retry and not is_reel and not is_event_post(caption):
                        print(f"  [SKIP] Not an event (Caption: {caption[:50]}...)")
                        continue

                    # Extract timestamp
                    try:
                        time_elem = driver.find_element(By.TAG_NAME, "time")
                        post_timestamp = time_elem.get_attribute("datetime")
                    except:
                        post_timestamp = datetime.now().isoformat()

                    # Download Image (Using container logic)
                    # Download Image — handles both single posts and carousels
                    img_path = None
                    try:
                        # Try finding the main event image
                        img_elem = container.find_element(By.CSS_SELECTOR, "img[style*='object-fit: cover'], img[class*='_aagv'], img[src*='fbcdn']")
                        src = img_elem.get_attribute("src")
                        img_path = download_image(src, username, post_timestamp, 0)
                    except:
                        try:
                            img_elem = container.find_element(By.TAG_NAME, "img")
                            src = img_elem.get_attribute("src")
                            img_path = download_image(src, username, post_timestamp, 0)
                        except: pass

                    # Carousel support: try next image if first image seems like a photo (not a poster)
                    # Event posters are often image #2 or #3 in carousel posts
                    if img_path:
                        try:
                            next_btns = driver.find_elements(By.CSS_SELECTOR,
                                "button[aria-label='Next'], button[aria-label='next']")
                            if next_btns:
                                # There IS a carousel — try next image too
                                for carousel_idx in range(1, 3):  # Check up to 3 images
                                    next_btns[0].click()
                                    time.sleep(1.2)
                                    try:
                                        next_img = container.find_element(By.CSS_SELECTOR, "img[src*='fbcdn']")
                                        next_src = next_img.get_attribute("src")
                                        next_path = download_image(next_src, username, post_timestamp, carousel_idx)
                                        if next_path:
                                            # Prefer the carousel image for QR scanning (event poster is often slide 2)
                                            img_path = next_path
                                        next_btns = driver.find_elements(By.CSS_SELECTOR,
                                            "button[aria-label='Next'], button[aria-label='next']")
                                        if not next_btns:
                                            break
                                    except: break
                        except: pass

                    if not img_path:
                        print("  [ERROR] Could not find event image, skipping.")
                        continue

                    # Attempt QR Scan
                    qr_link = extract_qr_link(img_path)
                    if qr_link: print(f"  [QR] Found: {qr_link}")

                    # --- REEL AUDIO TRANSCRIPTION ---
                    audio_text = None
                    if "/reel/" in post_url:
                        print(f"  [AUDIO] Processing reel audio...")
                        audio_path = download_reel_audio(post_url, username, post_timestamp)
                        if audio_path:
                            audio_text = transcribe_audio(audio_path)
                            # Cleanup audio file to save space
                            try: os.remove(audio_path)
                            except: pass

                    # --- GEMINI BRAIN ---
                    print(f"  [AI] Refining with Gemini Brain...")
                    refined = refine_event_with_gemini(img_path, caption, qr_hint=qr_link, audio_transcription=audio_text)
                    
                    if refined is None:
                        # Skip quietly
                        continue
                        
                    # Construct Data Object
                    post_data = {
                        "title": refined.get("title", "Upcoming Event"),
                        "description": caption,
                        "event_date": refined.get("event_date"),
                        "event_time": refined.get("event_time"),
                        "venue": refined.get("venue", "MJCET Campus"),
                        "category": refined.get("category", "Other"),
                        "registration_link": refined.get("registration_link") or qr_link,
                        "last_register_date": refined.get("last_register_date"),
                        "post_url": post_url,
                        "username": username,
                        "profile_pic_url": profile_pic_url,
                        "image_path": img_path,
                        "scraped_at": datetime.now().isoformat()
                    }

                    # --- DB SYNC (Smart Merge) ---
                    try:
                        db = SessionLocal()
                        # 1. Try matching by URL (exact same post)
                        existing = db.query(models.Event).filter(models.Event.source_url == post_url).first()
                        
                        # 2. If no URL match, try matching by Title + Club (Same event, different post)
                        title = refined.get("title") if refined else None
                        if not existing and title and title != f"Event by {username}":
                            existing = db.query(models.Event).filter(
                                models.Event.title == title,
                                models.Event.club_name == username
                            ).first()
                            if existing:
                                print(f"  [🤝 SMART MERGE] Matching existing event: {title}")
                        
                        # Prepare event_date (actual DateTime object)
                        actual_date = None
                        if refined and refined.get("event_date"):
                            try:
                                actual_date = datetime.strptime(refined["event_date"], "%Y-%m-%d")
                            except: pass
                        
                        # 2026 ONLY FILTER: Skip events from 2025 or earlier
                        if actual_date and actual_date.year < 2026:
                            print(f"  [SKIP] Skipping past event from {actual_date.year}: {post_url}")
                            db.close()
                            continue

                        event_fields = {
                            "title": title or f"Event by {username}",
                            "description": caption,
                            "club_name": username,
                            "source_type": "instagram",
                            "profile_pic": profile_pic_url,
                            "source_url": post_url,
                            "image_path": img_path,
                            "registration_link": refined.get("registration_link") if refined else None,
                            "date_str": refined.get("event_date") or "TBA",
                            "event_date": actual_date,
                            "time": refined.get("event_time"),
                            "venue": refined.get("venue") if refined else "MJCET Campus",
                            "category": refined.get("category") if refined else "General",
                            "last_register_date": refined.get("last_register_date") or "TBA",
                            "is_published": False
                        }

                        if not existing:
                            new_event = models.Event(**event_fields)
                            db.add(new_event)
                            db.commit()
                            print(f"  [✅ SYNC] Success: {new_event.title}")
                        else:
                            # SMART UPDATE: Only overwrite if new data is better (e.g. not null/TBA)
                            for key, value in event_fields.items():
                                current_val = getattr(existing, key)
                                # If existing is TBA/null but new is real, update it
                                if (not current_val or current_val == "TBA") and value and value != "TBA":
                                    setattr(existing, key, value)
                                # Always update image and description to latest
                                elif key in ["image_path", "description", "source_url"]:
                                    setattr(existing, key, value)
                                    
                            db.commit()
                            print(f"  [✅ MERGE/UPDATE] Success: {existing.title}")
                        db.close()
                    except Exception as dbe:
                        print(f"  [DB ERROR] {dbe}")

                    scraped_data.append(post_data)
                    save_data(scraped_data)
                    print(f"  [JSON SAVE] Success")
            
            except Exception as e:
                print(f"Error scraping {username}: {e}")
                continue

    finally:
        driver.quit()
        print("Scraper finished.")

if __name__ == "__main__":
    scrape_instagram()
