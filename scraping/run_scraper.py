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

# Adjust path to import from backend and ml
# The scraping folder is a child of the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.gemini_refiner import refine_event_with_gemini, transcribe_audio
import yt_dlp

# ---------------- CONFIGURATION ---------------- #
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
JSON_FILE = os.path.join(DATA_DIR, "scraped_data.json")
CHROME_PROFILE_DIR = os.path.join(DATA_DIR, "chrome_profile")

# Create directories if they don't exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)

# --- LOGGING SETUP ---
LOG_FILE = os.path.join(DATA_DIR, "scraper.log")

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger(LOG_FILE)

# TARGET CLUBS
TARGET_ACCOUNTS = [
    "horizon.mjcet", "ieeemjcet_cis", "ieeecsmjcet", 
    "ieee.wie.mjcet", "ieeesmcmjcet", "awsclub.mjcet", "mjcet_acm"
]

# Keywords to SKIP
SKIP_KEYWORDS = [
    "thank you", "farewell", "happy birthday", "hb ", "congratulations",
    "achievement", "alumni", "gb meeting", "general body",
    "execom", "portfolio", "core member", "core team", "recruitment",
    "welcome to the club", "induction", "member spotlight",
    "volunteer", "recognition", "felicitation", "certificates", "certificate distribution",
    "meet the team", "introducing", "our team", "team reveal", 
    "glimpse", "highlights", "recap", "concluded", "success of", "memories", "throwback"
]

# Keywords for event identification
EVENT_INDICATORS = [
    "register", "link in bio", "join us", "venue", "date:", "workshop", 
    "session", "contest", "hackathon", "competition", "seminar", 
    "registration", "webinar", "bootcamp", "hack", "fest", "symposium",
    "conference", "meetup", "event", "summit", "challenge", "hack", "grand prize",
    "prize pool", "cash prize", "orientation"
]

def setup_driver():
    os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
    lock_files = ["SingletonLock", "Lock"]
    for lock in lock_files:
        lock_path = os.path.join(CHROME_PROFILE_DIR, lock)
        if os.path.exists(lock_path):
            try: os.remove(lock_path)
            except: pass

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-extensions")
    options.add_argument("--proxy-server='direct://'")
    options.add_argument("--proxy-bypass-list=*")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Could not start Chrome: {e}")
        sys.exit(1)

def load_existing_data():
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    try:
        with open(JSON_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Failed to save JSON: {e}")

def download_image(url, username, timestamp, index):
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
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([reel_url])
        final_path = output_path + ".mp3"
        return final_path if os.path.exists(final_path) else None
    except:
        return None

def extract_qr_link(image_path):
    try:
        if not image_path or not os.path.exists(image_path): return None
        img = cv2.imread(image_path)
        if img is None: return None
        decoded_objects = decode(img)
        if not decoded_objects:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            decoded_objects = decode(thresh)
        for obj in decoded_objects:
            qr_data = obj.data.decode("utf-8")
            if "http" in qr_data: return qr_data
    except: pass
    return None

def is_event_post(caption, is_reel=False):
    if not caption or caption == "No Caption": return is_reel
    caption_lower = caption.lower()
    for kw in SKIP_KEYWORDS:
        if kw in caption_lower: return False
    if is_reel and len(caption_lower) > 5: return True
    return any(indicator in caption_lower for indicator in EVENT_INDICATORS)

def run_scraper():
    """Main standalone scraping process."""
    driver = setup_driver()
    
    try:
        driver.get("https://www.instagram.com/")
        print("\n" + "="*50)
        print("LOGIN MODE: Please log in to Instagram in the browser window.")
        print("Once logged in, press ENTER here to start...")
        print("="*50 + "\n")
        input() 

        scraped_data = load_existing_data()

        for username in TARGET_ACCOUNTS:
            try:
                # Basic health check
                _ = driver.current_url
            except:
                driver = setup_driver()
                driver.get("https://www.instagram.com/")
                time.sleep(5)
            
            time.sleep(random.uniform(5, 10))
            print(f"\n--- Scraping @{username} ---")
            
            try:
                driver.get(f"https://www.instagram.com/{username}/")
                time.sleep(random.uniform(7, 12))

                try:
                    profile_pic = driver.find_element(By.CSS_SELECTOR, "header img")
                    profile_pic_url = profile_pic.get_attribute("src")
                except: profile_pic_url = None

                links = driver.find_elements(By.TAG_NAME, "a")
                post_links = []
                for a in links:
                    href = a.get_attribute("href")
                    if href and ("/p/" in href or "/reel/" in href) and f"/{username}/" in href:
                        post_links.append(href)
                
                post_links = list(dict.fromkeys(post_links))[:6]

                for post_url in post_links:
                    try:
                        from backend.database import SessionLocal
                        from backend import models
                        db = SessionLocal()
                        
                        exists = db.query(models.Event).filter(models.Event.source_url == post_url).first()
                        if exists and exists.event_date:
                            print(f"  [SKIP] Already in DB: {exists.title}")
                            db.close()
                            continue
                        db.close()
                    except: pass

                    print(f"  [NEW] Found post: {post_url}")
                    driver.get(post_url)
                    time.sleep(random.uniform(4, 6))
                    
                    # Expand caption
                    try:
                        more_btns = driver.find_elements(By.XPATH, "//span[text()='more'] | //div[text()='more']")
                        for btn in more_btns:
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                time.sleep(1)
                                break
                    except: pass

                    caption = "No Caption"
                    try:
                        h1_elems = driver.find_elements(By.TAG_NAME, "h1")
                        if h1_elems: caption = h1_elems[0].text.strip()
                    except: pass
                    
                    is_reel = ("/reel/" in post_url)
                    if not is_reel and not is_event_post(caption):
                        print(f"  [SKIP] Not an event")
                        continue

                    try:
                        time_elem = driver.find_element(By.TAG_NAME, "time")
                        post_timestamp = time_elem.get_attribute("datetime")
                    except: post_timestamp = datetime.now().isoformat()

                    # Download Image
                    img_path = None
                    try:
                        img_elem = driver.find_element(By.CSS_SELECTOR, "img[src*='fbcdn']")
                        src = img_elem.get_attribute("src")
                        img_path = download_image(src, username, post_timestamp, 0)
                    except: pass

                    if not img_path:
                        print("  [ERROR] Image not found, skipping.")
                        continue

                    qr_link = extract_qr_link(img_path)
                    
                    audio_text = None
                    if is_reel:
                        audio_path = download_reel_audio(post_url, username, post_timestamp)
                        if audio_path:
                            audio_text = transcribe_audio(audio_path)
                            try: os.remove(audio_path)
                            except: pass

                    print(f"  [AI] Refining...")
                    refined = refine_event_with_gemini(img_path, caption, qr_hint=qr_link, audio_transcription=audio_text)
                    
                    if refined:
                        actual_date = None
                        if refined.get("event_date"):
                            try: actual_date = datetime.strptime(refined["event_date"], "%Y-%m-%d")
                            except: pass
                        
                        # Filter past events
                        if actual_date and actual_date.year < 2026:
                            print(f"  [SKIP] Past event")
                            continue

                        # Prepare DB Entry
                        event_fields = {
                            "title": refined.get("title") or f"Event by {username}",
                            "description": caption,
                            "club_name": username,
                            "profile_pic": profile_pic_url,
                            "source_url": post_url,
                            "image_path": img_path,
                            "registration_link": refined.get("registration_link") or qr_link,
                            "date_str": refined.get("event_date") or "TBA",
                            "event_date": actual_date,
                            "venue": refined.get("venue") or "MJCET Campus",
                            "category": refined.get("category") or "Other",
                            "last_register_date": refined.get("last_register_date") or "TBA",
                            "is_published": False,  # STAGING BY DEFAULT (Objective 5)
                            "source_type": "instagram" # Differentiate from manual (Objective 4)
                        }

                        try:
                            db = SessionLocal()
                            existing = db.query(models.Event).filter(models.Event.source_url == post_url).first()
                            
                            if not existing:
                                new_event = models.Event(**event_fields)
                                db.add(new_event)
                                print(f"  [✅ SYNC] New: {new_event.title}")
                            else:
                                for k, v in event_fields.items():
                                    setattr(existing, k, v)
                                print(f"  [✅ UPDATE] Existing: {existing.title}")
                            
                            db.commit()
                            db.close()
                        except Exception as dbe:
                            print(f"  [DB ERROR] {dbe}")

            except Exception as e:
                print(f"Error @{username}: {e}")
                continue

    finally:
        driver.quit()
        print("Scraper finished.")

if __name__ == "__main__":
    run_scraper()
