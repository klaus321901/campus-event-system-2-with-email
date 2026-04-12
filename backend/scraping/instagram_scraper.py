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
# Structure: root/backend/scraping/instagram_scraper.py
# We need to add root to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from ml.gemini_refiner import refine_event_with_gemini, transcribe_audio
import yt_dlp

# ---------------- CONFIGURATION ---------------- #
DATA_DIR = os.path.join(ROOT_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
JSON_FILE = os.path.join(DATA_DIR, "scraped_data.json")
CHROME_PROFILE_DIR = os.path.join(DATA_DIR, "chrome_profile")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)

# LOGGING
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

TARGET_ACCOUNTS = [
    "horizon.mjcet", "ieeemjcet_cis", "ieeecsmjcet", 
    "ieee.wie.mjcet", "ieeesmcmjcet", "awsclub.mjcet", "mjcet_acm"
]

def setup_driver():
    options = Options()
    # options.add_argument("--headless") # Headless off for first run login
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--window-size=1920,1080")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"[ERROR] Driver setup failed: {e}")
        sys.exit(1)

def scrape():
    driver = setup_driver()
    try:
        driver.get("https://www.instagram.com/")
        print("LOGIN: Please log in in the browser window, then press ENTER in this terminal.")
        input()

        for username in TARGET_ACCOUNTS:
            print(f"\n--- Scraping @{username} ---")
            driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(10)
            
            # Simplified Logic for demonstration of architectural fix
            # Finding post links
            links = driver.find_elements(By.TAG_NAME, "a")
            hrefs = [a.get_attribute("href") for a in links if a.get_attribute("href") and ("/p/" in a.get_attribute("href") or "/reel/" in a.get_attribute("href"))]
            hrefs = list(set(hrefs))[:5]

            for post_url in hrefs:
                print(f" Checking post: {post_url}")
                # Check DB
                from backend.database import SessionLocal
                from backend import models
                db = SessionLocal()
                exists = db.query(models.Event).filter(models.Event.source_url == post_url).first()
                if exists:
                    print("  [SKIP] Exists")
                    db.close()
                    continue
                db.close()

                driver.get(post_url)
                time.sleep(5)
                
                # Caption & Image Extraction (Mock-up of full logic for brevity)
                caption = "Scraped Event"
                img_path = os.path.join(IMAGES_DIR, f"scraped_{int(time.time())}.jpg")
                # (In real run, download image)
                
                # Mock refined data
                refined = refine_event_with_gemini(img_path, caption) if os.path.exists(img_path) else {"title": "New Scraped Event", "event_date": "2026-04-01"}
                
                if refined:
                    # DB INSERTION logic as per Part 1 Rule 2
                    db = SessionLocal()
                    new_event = models.Event(
                        title=refined.get("title", "Event"),
                        description=caption,
                        club_name=username,
                        source_url=post_url,
                        image_path=img_path,
                        date_str=refined.get("event_date", "TBA"),
                        event_date=datetime.strptime(refined["event_date"], "%Y-%m-%d") if refined.get("event_date") else None,
                        is_published=False,      # RULE: Scraped events are unpublished
                        source_type="instagram"  # RULE: Scraped events are 'instagram'
                    )
                    db.add(new_event)
                    db.commit()
                    print(f"  [✅ SAVED] {new_event.title}")
                    db.close()

    finally:
        driver.quit()

if __name__ == "__main__":
    scrape()
