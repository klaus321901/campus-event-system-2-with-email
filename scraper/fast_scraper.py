import instaloader
import os
import json
import time
import sys
from datetime import datetime

# Adjust path to import from ml
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.gemini_refiner import refine_event_with_gemini

# Note: Using instaloader to fetch latest posts without a browser
L = instaloader.Instaloader(
    download_pictures=True,
    download_videos=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    dirname_pattern="data/images/{target}" # Organize images
)

TARGET_ACCOUNTS = [
    "csi_mjcet",
    "ecellmjcet",
    "lords_insta",
    "mvsr_engineering_college",
    "vce_official"
]

SCRAPED_DATA_PATH = "data/scraped_data.json"

def load_scraped_data():
    if os.path.exists(SCRAPED_DATA_PATH):
        try:
            with open(SCRAPED_DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_scraped_data(data):
    os.makedirs("data", exist_ok=True)
    with open(SCRAPED_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def run_fast_scrape_with_gemini():
    print(f"🚀 [{datetime.now()}] Starting Gemini-Enhanced Scrape...")
    
    scraped_data = load_scraped_data()
    existing_urls = {item.get("post_url") for item in scraped_data}
    
    new_events_count = 0
    
    for username in TARGET_ACCOUNTS:
        print(f"\n--- Checking @{username} ---")
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            
            # Get only the top 3 most recent posts per account for speed
            posts = profile.get_posts()
            
            count = 0
            for post in posts:
                if count >= 3: break
                
                post_url = f"https://www.instagram.com/p/{post.shortcode}/"
                if post_url in existing_urls:
                    print(f"  Skipping existing: {post.shortcode}")
                    count += 1
                    continue
                
                print(f"  ✨ Processing New Post: {post.shortcode}")
                
                # 1. Download the post (image + metadata)
                L.download_post(post, target=username)
                
                # 2. Find the downloaded image
                # Instaloader saves with various extensions, we look for the .jpg
                image_folder = f"data/images/{username}"
                image_path = None
                for file in os.listdir(image_folder):
                    if post.shortcode in file and file.endswith(".jpg"):
                        image_path = os.path.join(image_folder, file)
                        break
                
                if not image_path:
                    print(f"  [WARN] Image not found for {post.shortcode}")
                    count += 1
                    continue

                # 3. Use Gemini to refine data
                print(f"  [AI] Refining with Gemini (Full Caption + Image)...")
                # post.caption is the FULL text (no '...')
                refined_details = refine_event_with_gemini(image_path, post.caption)
                
                if refined_details:
                    event_entry = {
                        "title": refined_details.get("title", f"Event by {username}"),
                        "club_name": username,
                        "description": post.caption, # Store full original caption
                        "date_str": refined_details.get("event_date", str(post.date_local)),
                        "venue": refined_details.get("venue", "MJCET Campus"),
                        "category": refined_details.get("category", "General"),
                        "registration_link": refined_details.get("registration_link"),
                        "post_url": post_url,
                        "image_path": image_path,
                        "scraped_at": datetime.now().isoformat()
                    }
                    scraped_data.append(event_entry)
                    save_scraped_data(scraped_data)
                    print(f"  ✅ Added: {event_entry['title']}")
                    new_events_count += 1
                
                count += 1
                time.sleep(2) # Prevent small rate limits
                
        except Exception as e:
            print(f"  [ERROR] Failed to scrape {username}: {e}")
            
    print(f"\n✅ Finished! Added {new_events_count} new events with AI verification.")

if __name__ == "__main__":
    run_fast_scrape_with_gemini()
