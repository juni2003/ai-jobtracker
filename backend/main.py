"""
main.py — FastAPI application with dual-pipeline support.

Pakistan endpoints  →  /api/pakistan/*
Remote endpoints    →  /api/remote/*

Both share the same JobOut schema and Kanban statuses.
Data is stored in separate MongoDB collections.
"""

from __future__ import annotations

import os
from contextlib       import asynccontextmanager
from datetime         import datetime
from typing           import List, Optional

from fastapi           import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from bson              import ObjectId
from dotenv            import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron      import CronTrigger

from database import connect_db, close_db, get_pakistan_col, get_remote_col
from models   import JobOut, StatusUpdate, JobStatus
from scraper  import run_pakistan_scraper, run_remote_scraper

load_dotenv()

SCRAPE_TIME = os.getenv("SCRAPE_TIME", "08:00")


# ── APScheduler ───────────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler()


async def _save_jobs(jobs: list, collection) -> dict:
    """
    Deduplicate and insert jobs into the given collection.
    Returns a summary dict.
    """
    inserted = skipped = 0
    for job in jobs:
        exists = await collection.find_one(
            {"title": job.get("title"), "company": job.get("company")}
        )
        if not exists:
            job["status"]     = JobStatus.inbox
            job["scraped_at"] = datetime.utcnow()
            await collection.insert_one(job)
            inserted += 1
        else:
            skipped += 1
    return {"total": len(jobs), "inserted": inserted, "skipped": skipped}


async def scheduled_pakistan_scrape():
    jobs   = await run_pakistan_scraper()
    result = await _save_jobs(jobs, get_pakistan_col())
    print(f"📥 Pakistan scheduled: {result['inserted']} new, {result['skipped']} skipped")


async def scheduled_remote_scrape():
    jobs   = run_remote_scraper()
    result = await _save_jobs(jobs, get_remote_col())
    print(f"📥 Remote scheduled: {result['inserted']} new, {result['skipped']} skipped")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()

    hour, minute = SCRAPE_TIME.split(":")
    scheduler.add_job(
        scheduled_pakistan_scrape,
        CronTrigger(hour=int(hour), minute=int(minute)),
        id="daily_pakistan", replace_existing=True,
    )
    scheduler.add_job(
        scheduled_remote_scrape,
        CronTrigger(hour=int(hour), minute=int(minute) + 10),   # 10 min offset
        id="daily_remote", replace_existing=True,
    )
    scheduler.start()
    print(f"⏰ Scheduler: Pakistan @ {SCRAPE_TIME}, Remote @ {hour}:{int(minute)+10:02d}")
    yield

    scheduler.shutdown()
    await close_db()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "AI JobTracker API",
    description = "Dual-pipeline job tracker — Pakistan + Worldwide Remote",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ── Shared helpers ────────────────────────────────────────────────────────────
def _to_out(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


def _build_filter(status: Optional[str], search: Optional[str],
                  city: Optional[str], is_remote: Optional[bool]) -> dict:
    f: dict = {}
    if status:
        f["status"] = status
    if search:
        f["$or"] = [
            {"title"  : {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
        ]
    if city:
        f["office_city"] = {"$regex": city, "$options": "i"}
    if is_remote is not None:
        f["is_remote"] = is_remote
    return f


# ══════════════════════════════════════════════════════════════════════════════
#  PAKISTAN ROUTES   /api/pakistan/*
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/pakistan/jobs", response_model=List[JobOut], tags=["🇵🇰 Pakistan Jobs"])
async def list_pakistan_jobs(
    status   : Optional[str]  = Query(None, description="Filter by Kanban status"),
    search   : Optional[str]  = Query(None, description="Search title / company"),
    city     : Optional[str]  = Query(None, description="Filter by city, e.g. Karachi"),
    is_remote: Optional[bool] = Query(None, description="true=Remote, false=Onsite"),
    skip     : int            = Query(0,    ge=0),
    limit    : int            = Query(100,  ge=1, le=500),
):
    col  = get_pakistan_col()
    filt = _build_filter(status, search, city, is_remote)
    docs = await col.find(filt).sort("scraped_at", -1).skip(skip).limit(limit).to_list(limit)
    return [_to_out(d) for d in docs]


@app.get("/api/pakistan/jobs/{job_id}", response_model=JobOut, tags=["🇵🇰 Pakistan Jobs"])
async def get_pakistan_job(job_id: str):
    doc = await get_pakistan_col().find_one({"_id": ObjectId(job_id)})
    if not doc:
        raise HTTPException(404, "Job not found")
    return _to_out(doc)


@app.patch("/api/pakistan/jobs/{job_id}/status", response_model=JobOut, tags=["🇵🇰 Pakistan Jobs"])
async def update_pakistan_status(job_id: str, body: StatusUpdate):
    doc = await get_pakistan_col().find_one_and_update(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": body.status}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(404, "Job not found")
    return _to_out(doc)


@app.delete("/api/pakistan/jobs/{job_id}", tags=["🇵🇰 Pakistan Jobs"])
async def delete_pakistan_job(job_id: str):
    result = await get_pakistan_col().delete_one({"_id": ObjectId(job_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Job not found")
    return {"message": "Deleted"}


@app.post("/api/pakistan/scrape", tags=["🇵🇰 Pakistan Jobs"])
async def trigger_pakistan_scrape():
    """Manually trigger the Pakistan scrape pipeline."""
    jobs   = await run_pakistan_scraper()
    result = await _save_jobs(jobs, get_pakistan_col())
    return result


@app.get("/api/pakistan/stats", tags=["🇵🇰 Pakistan Jobs"])
async def pakistan_stats():
    """Job counts per Kanban column + city breakdown."""
    col      = get_pakistan_col()
    status_p = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    city_p   = [
        {"$match": {"office_city": {"$nin": ["", None]}}},
        {"$group": {"_id": "$office_city", "count": {"$sum": 1}}},
        {"$sort" : {"count": -1}},
        {"$limit": 10},
    ]
    status_docs = await col.aggregate(status_p).to_list(20)
    city_docs   = await col.aggregate(city_p).to_list(10)
    return {
        "by_status": {d["_id"]: d["count"] for d in status_docs},
        "by_city"  : {d["_id"]: d["count"] for d in city_docs},
        "total"    : await col.count_documents({}),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  REMOTE ROUTES   /api/remote/*
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/remote/jobs", response_model=List[JobOut], tags=["🌍 Remote Jobs"])
async def list_remote_jobs(
    status  : Optional[str] = Query(None),
    search  : Optional[str] = Query(None),
    skip    : int           = Query(0,   ge=0),
    limit   : int           = Query(100, ge=1, le=500),
):
    col  = get_remote_col()
    filt = _build_filter(status, search, None, None)
    docs = await col.find(filt).sort("scraped_at", -1).skip(skip).limit(limit).to_list(limit)
    return [_to_out(d) for d in docs]


@app.get("/api/remote/jobs/{job_id}", response_model=JobOut, tags=["🌍 Remote Jobs"])
async def get_remote_job(job_id: str):
    doc = await get_remote_col().find_one({"_id": ObjectId(job_id)})
    if not doc:
        raise HTTPException(404, "Job not found")
    return _to_out(doc)


@app.patch("/api/remote/jobs/{job_id}/status", response_model=JobOut, tags=["🌍 Remote Jobs"])
async def update_remote_status(job_id: str, body: StatusUpdate):
    doc = await get_remote_col().find_one_and_update(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": body.status}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(404, "Job not found")
    return _to_out(doc)


@app.delete("/api/remote/jobs/{job_id}", tags=["🌍 Remote Jobs"])
async def delete_remote_job(job_id: str):
    result = await get_remote_col().delete_one({"_id": ObjectId(job_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Job not found")
    return {"message": "Deleted"}


@app.post("/api/remote/scrape", tags=["🌍 Remote Jobs"])
async def trigger_remote_scrape():
    """Manually trigger the Remote scrape pipeline."""
    jobs   = run_remote_scraper()
    result = await _save_jobs(jobs, get_remote_col())
    return result


@app.get("/api/remote/stats", tags=["🌍 Remote Jobs"])
async def remote_stats():
    col = get_remote_col()
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    docs     = await col.aggregate(pipeline).to_list(20)
    return {
        "by_status": {d["_id"]: d["count"] for d in docs},
        "total"    : await col.count_documents({}),
    }


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status"    : "running 🚀",
        "endpoints" : {
            "pakistan" : "/api/pakistan/jobs",
            "remote"   : "/api/remote/jobs",
            "docs"     : "/docs",
        },
    }
