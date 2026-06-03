"""
database.py — Motor async MongoDB connection.
Manages two separate collections:
  • pakistan_jobs  — jobs scraped from Pakistan sources
  • remote_jobs    — worldwide remote jobs
"""

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME     = os.getenv("DB_NAME",     "job_portal")

client          : AsyncIOMotorClient = None
db              = None
pakistan_jobs   = None   # collection handle
remote_jobs     = None   # collection handle


async def connect_db():
    """Call on FastAPI startup — connects and sets up indexes."""
    global client, db, pakistan_jobs, remote_jobs

    client        = AsyncIOMotorClient(MONGODB_URL)
    db            = client[DB_NAME]
    pakistan_jobs = db["pakistan_jobs"]
    remote_jobs   = db["remote_jobs"]

    # Compound indexes for fast duplicate checking
    await pakistan_jobs.create_index([("title", 1), ("company", 1)])
    await remote_jobs.create_index(  [("title", 1), ("company", 1)])

    # Index on status for Kanban column queries
    await pakistan_jobs.create_index([("status", 1)])
    await remote_jobs.create_index(  [("status", 1)])

    print(f"✅ MongoDB connected  →  {DB_NAME}")
    print(f"   Collections: pakistan_jobs, remote_jobs")


async def close_db():
    """Call on FastAPI shutdown."""
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


def get_pakistan_col():
    """Return the pakistan_jobs collection handle."""
    return pakistan_jobs


def get_remote_col():
    """Return the remote_jobs collection handle."""
    return remote_jobs
