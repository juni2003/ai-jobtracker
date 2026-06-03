"""
scraper.py — Dual-pipeline job scraper.

PAKISTAN PIPELINE  (→ pakistan_jobs collection)
  1. Jooble API    — free, genuinely covers Pakistan, structured data
                     Sign up free at https://jooble.org/api/about
  2. Rozee.pk      — Pakistan #1 job portal  (via pw_scrape.py subprocess + Gemini)
  3. Mustakbil.com — Pakistan #2 job portal  (via pw_scrape.py subprocess + Gemini)

  Playwright runs in pw_scrape.py as a SEPARATE SUBPROCESS to fully
  bypass the Windows asyncio event loop subprocess limitation.

REMOTE PIPELINE  (→ remote_jobs collection)
  1. Remotive.io      — worldwide remote jobs, free JSON API, no key needed
  2. We Work Remotely — RSS feed, no key needed

Public functions:
  run_pakistan_scraper() -> List[dict]   (async)
  run_remote_scraper()   -> List[dict]   (sync)
"""

import os
import re
import sys
import json
import asyncio
import subprocess
import httpx
from datetime              import datetime
from typing                import List
from xml.etree             import ElementTree
from pathlib               import Path

from dotenv                import load_dotenv
import google.generativeai as genai
from bs4                   import BeautifulSoup

# Explicit path — works regardless of which directory Python is launched from
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Path to the standalone Playwright subprocess script
PW_SCRAPE_SCRIPT = Path(__file__).parent / "pw_scrape.py"

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel("gemini-3.1-flash-lite")

MAX_PAGE_CHARS = 100_000   # Massive increase from 10k to 100k for Flash Lite context


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _playwright_get_text_sync(url: str) -> str:
    """
    Scrape a URL by calling pw_scrape.py as a SEPARATE SUBPROCESS.

    Why subprocess? On Windows, Playwright (both sync and async) needs
    to spawn Chromium using asyncio.create_subprocess_exec, which requires
    a ProactorEventLoop. When running inside FastAPI (uvicorn), the event
    loop is a SelectorEventLoop and setting ProactorEventLoop in a thread
    is unreliable due to greenlet context switching.

    subprocess.run() is a plain blocking OS call — no asyncio involved —
    so it works perfectly inside asyncio.to_thread() on Windows.
    """
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"   # ensures pw_scrape.py stdout is UTF-8
        result = subprocess.run(
            [sys.executable, str(PW_SCRAPE_SCRIPT), url],
            capture_output=True,
            timeout=60,
            env=env,
        )
        # Decode as UTF-8 (pw_scrape.py writes UTF-8 bytes)
        stdout_text = result.stdout.decode("utf-8", errors="replace").strip()
        if result.stderr:
            stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
            if stderr_text:
                print(f"    ⚠️  pw_scrape: {stderr_text[:200]}")
        return stdout_text
    except subprocess.TimeoutExpired:
        print(f"    ⏱  Timeout: {url}")
        return ""
    except Exception as exc:
        print(f"    ❌ Playwright error ({url}): {exc}")
        return ""


async def _playwright_get_text(url: str) -> str:
    """
    Async wrapper: runs _playwright_get_text_sync (subprocess call)
    in a thread pool so it doesn't block the FastAPI event loop.
    """
    return await asyncio.to_thread(_playwright_get_text_sync, url)


def _gemini_extract_jobs(page_text: str, company_fallback: str,
                          job_type: str = "pakistan") -> List[dict]:
    """
    Ask Gemini to extract job listings from raw page text.
    Returns a list of dicts or [] on failure.
    """
    if not page_text.strip():
        return []

    location_hint = (
        "Pakistan (city if shown, else 'Pakistan')"
        if job_type == "pakistan"
        else "wherever the job is based or 'Worldwide Remote'"
    )

    prompt = f"""You are a job listing extractor.
Read the text from a careers page and extract every distinct job listing.

Return ONLY a raw JSON array — no markdown, no explanation.
Each object must have exactly these keys:
  "title"               : job title (string)
  "company"             : company name, use "{company_fallback}" if not found (string)
  "location"            : {location_hint} (string)
  "office_city"         : city name only, e.g. "Karachi", or empty string (string)
  "is_remote"           : true if remote/hybrid, false if onsite (boolean)
  "apply_link"          : direct apply URL or empty string (string)
  "contact_email"       : HR email if shown, else empty string (string)
  "salary"              : salary text if shown, else empty string (string)
  "experience_required" : e.g. "Fresh", "0-1 years", "1-2 years", or empty string (string)
  "post_date"           : posting date as text, or empty string (string)
  "description_snippet" : first 200 characters of job description (string)

If no jobs found, return [].

--- PAGE TEXT ---
{page_text}
--- END ---"""

    try:
        response = gemini.generate_content(prompt)
        raw      = response.text.strip()
        raw      = re.sub(r"^```(?:json)?\s*", "", raw)
        raw      = re.sub(r"\s*```$",           "", raw)
        jobs     = json.loads(raw)
        return jobs if isinstance(jobs, list) else []
    except json.JSONDecodeError:
        print("    ⚠️  Gemini returned non-JSON")
        return []
    except Exception as exc:
        print(f"    ❌ Gemini error: {exc}")
        return []


def _stamp(jobs: List[dict], source: str, source_url: str,
           job_type: str) -> List[dict]:
    """Add metadata fields to each job dict."""
    now = datetime.utcnow().isoformat()
    for job in jobs:
        job["source"]     = source
        job["source_url"] = source_url
        job["scraped_at"] = now
        job["job_type"]   = job_type
        job.setdefault("is_remote",            job_type == "remote")
        job.setdefault("office_city",          "")
        job.setdefault("contact_email",        "")
        job.setdefault("salary",               "")
        job.setdefault("experience_required",  "")
        job.setdefault("description_snippet",  "")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
#  PAKISTAN PIPELINE
#
#  All 3 sources use Playwright (subprocess) + Gemini.
#  They run SEQUENTIALLY with 13s gaps to respect the 5 RPM free tier.
#  Gemini quota: 5 RPM / 20 RPD → enough for 1 scheduled scrape/day.
# ══════════════════════════════════════════════════════════════════════════════

# Playwright source definitions: (url, company_fallback, source_name)
PK_PLAYWRIGHT_SOURCES = [
    # Rozee.pk - Software / Dev (Pages 1 & 2)
    (
        "https://rozee.pk/job/jsearch/q/software-developer-engineer-fresh-junior",
        "Unknown",
        "rozee.pk",
    ),
    (
        "https://rozee.pk/job/jsearch/q/software-developer-engineer-fresh-junior/2",
        "Unknown",
        "rozee.pk",
    ),
    # Rozee.pk - Data / Python / React (Pages 1 & 2)
    (
        "https://rozee.pk/job/jsearch/q/react-python-data-analyst-junior",
        "Unknown",
        "rozee.pk",
    ),
    (
        "https://rozee.pk/job/jsearch/q/react-python-data-analyst-junior/2",
        "Unknown",
        "rozee.pk",
    ),
    # Mustakbil
    (
        "https://mustakbil.com/jobs?q=software+developer+it&l=pakistan&sort=date",
        "Unknown",
        "mustakbil",
    ),
    (
        "https://mustakbil.com/jobs?q=software+developer+it&l=pakistan&sort=date&page=2",
        "Unknown",
        "mustakbil",
    ),
]


async def _scrape_pk_source(url: str, company: str, source: str) -> List[dict]:
    """Scrape one Pakistan job page: Playwright → Gemini → stamp."""
    print(f"    🌐 Scraping {source} ({url.split('?')[0].split('/')[-1] or source})…")
    text = await _playwright_get_text(url)
    if not text:
        print(f"    ⚠️  {source}: empty page — skipping Gemini")
        return []
    jobs = _gemini_extract_jobs(text, company, "pakistan")
    jobs = _stamp(jobs, source, url, "pakistan")
    print(f"    ✅ {source}: {len(jobs)} jobs")
    return jobs


async def run_pakistan_scraper() -> List[dict]:
    """
    Main entry point for Pakistan pipeline.
    Async — awaited from FastAPI routes and APScheduler.
    Sources: 2x Rozee.pk + 1x Mustakbil, all via Playwright + Gemini.
    Uses gemini-2.5-flash-lite (15 RPM free tier) — no delays needed.
    Returns combined list of job dicts ready for MongoDB insert.
    """
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    print(f"\n🇵🇰 Pakistan scraper started — {ts} UTC")

    all_jobs: List[dict] = []
    for url, company, source in PK_PLAYWRIGHT_SOURCES:
        jobs = await _scrape_pk_source(url, company, source)
        all_jobs.extend(jobs)

    print(f"🏁 Pakistan scraper done — {len(all_jobs)} total jobs\n")
    return all_jobs



# ══════════════════════════════════════════════════════════════════════════════
#  REMOTE PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

REMOTIVE_CATEGORIES = [
    "software-dev",
    "data",
    "devops-sysadmin",
    "product",
]

WWR_RSS_FEEDS = [
    ("https://weworkremotely.com/remote-jobs.rss",               "We Work Remotely"),
    ("https://weworkremotely.com/categories/remote-programming-jobs.rss", "We Work Remotely"),
]


def _remotive() -> List[dict]:
    """Fetch jobs from Remotive.io free JSON API (no key needed)."""
    all_jobs: List[dict] = []
    base = "https://remotive.com/api/remote-jobs"

    for cat in REMOTIVE_CATEGORIES:
        try:
            resp = httpx.get(base, params={"category": cat, "limit": 100}, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for r in data.get("jobs", []):
                desc = BeautifulSoup(r.get("description", ""), "html.parser").get_text()
                job  = {
                    "title"              : r.get("title", "").strip(),
                    "company"            : r.get("company_name", "Unknown"),
                    "location"           : r.get("candidate_required_location") or "Worldwide",
                    "office_city"        : "",
                    "is_remote"          : True,
                    "apply_link"         : r.get("url", ""),
                    "contact_email"      : "",
                    "salary"             : r.get("salary", ""),
                    "experience_required": "",
                    "post_date"          : r.get("publication_date", "")[:10],
                    "description_snippet": desc[:300],
                    "source"             : "remotive",
                    "source_url"         : base,
                    "job_type"           : "remote",
                    "scraped_at"         : datetime.utcnow().isoformat(),
                }
                all_jobs.append(job)

            print(f"    ✅ Remotive [{cat}]: {len(data.get('jobs', []))} jobs")

        except Exception as exc:
            print(f"    ❌ Remotive error [{cat}]: {exc}")

    return all_jobs


def _weworkremotely() -> List[dict]:
    """Parse We Work Remotely RSS feeds (no key needed)."""
    all_jobs: List[dict] = []

    for feed_url, source_name in WWR_RSS_FEEDS:
        try:
            resp = httpx.get(feed_url, timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            root = ElementTree.fromstring(resp.content)

            for item in root.findall(".//item"):
                def _t(tag):
                    el = item.find(tag)
                    return el.text.strip() if el is not None and el.text else ""

                title   = _t("title")
                company = ""
                if ": " in title:
                    parts   = title.split(": ", 1)
                    company = parts[0].strip()
                    title   = parts[1].strip()

                desc = BeautifulSoup(_t("description"), "html.parser").get_text()
                job  = {
                    "title"              : title,
                    "company"            : company or "Unknown",
                    "location"           : "Worldwide Remote",
                    "office_city"        : "",
                    "is_remote"          : True,
                    "apply_link"         : _t("link"),
                    "contact_email"      : "",
                    "salary"             : "",
                    "experience_required": "",
                    "post_date"          : _t("pubDate")[:16],
                    "description_snippet": desc[:300],
                    "source"             : "weworkremotely",
                    "source_url"         : feed_url,
                    "job_type"           : "remote",
                    "scraped_at"         : datetime.utcnow().isoformat(),
                }
                all_jobs.append(job)

            print(f"    ✅ WWR [{feed_url.split('/')[-1]}]: {len(all_jobs)} jobs total so far")

        except Exception as exc:
            print(f"    ❌ WWR error: {exc}")

    return all_jobs


def run_remote_scraper() -> List[dict]:
    """
    Main entry point for Remote pipeline.
    Returns combined list of job dicts ready for MongoDB insert.
    """
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    print(f"\n🌍 Remote scraper started — {ts} UTC")

    remotive_jobs = _remotive()
    wwr_jobs      = _weworkremotely()
    all_jobs      = remotive_jobs + wwr_jobs

    print(f"🏁 Remote scraper done — {len(all_jobs)} total jobs\n")
    return all_jobs


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    if mode in ("pakistan", "both"):
        pk = asyncio.run(run_pakistan_scraper())
        print(json.dumps(pk[:3], indent=2, default=str))

    if mode in ("remote", "both"):
        rm = run_remote_scraper()
        print(json.dumps(rm[:3], indent=2, default=str))
