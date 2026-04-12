
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def patch_db():
    # Remove 'postgresql+psycopg2://' prefix if present for direct psycopg2 use
    conn_str = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        print("Checking for 'role' column in 'users' table...")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'student';")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS club_name VARCHAR;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
        
        conn.commit()
        print("✅ Database patched successfully! 'role' column added.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error patching database: {e}")

if __name__ == "__main__":
    patch_db()
