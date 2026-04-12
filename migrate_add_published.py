"""
Migration: Add is_published column to events table.
All existing events → is_published = FALSE (hidden from frontend).
Run once: python migrate_add_published.py
"""
import psycopg2
from dotenv import load_dotenv
import os

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', '.env')
load_dotenv(env_path)

db_url = os.getenv("DATABASE_URL")
# Parse: postgresql://user:pass@host:port/dbname
import re
m = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
user, password, host, port, dbname = m.groups()

conn = psycopg2.connect(host=host, port=int(port), dbname=dbname, user=user, password=password)
cur = conn.cursor()

# Add column if not exists
cur.execute("""
    ALTER TABLE events 
    ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT FALSE;
""")
conn.commit()

# Count how many events are now hidden
cur.execute("SELECT COUNT(*) FROM events WHERE is_published = FALSE;")
count = cur.fetchone()[0]
print(f"✅ Migration done. {count} existing events are now in staging (hidden from frontend).")
print("   Run the scraper → new events also go to staging.")
print("   Use Admin → Staging panel to publish the good ones.")

cur.close()
conn.close()
