import sys
import os

# Root structure for backend/scraping/run_scraper.py
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.scraping.instagram_scraper import scrape

if __name__ == "__main__":
    print("🚀 Starting Campus Event System Scraper...")
    print("Note: This will insert events as 'source_type=instagram' and 'is_published=False'.")
    try:
        scrape()
    except KeyboardInterrupt:
        print("\n⏹️ Stopped by user.")
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
    finally:
        print("🏁 Scraper finished.")
