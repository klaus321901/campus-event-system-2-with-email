"""
Script to reset the database with the new schema
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine
from backend import models

# Drop all tables and recreate
print("Dropping all tables...")
models.Base.metadata.drop_all(bind=engine)
print("Creating tables with new schema...")
models.Base.metadata.create_all(bind=engine)
print("Database reset complete!")

# Now run init_db
from backend.init_db import init_db
print("\nPopulating database...")
init_db()
