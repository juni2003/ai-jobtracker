"""
pw_scrape.py — Standalone Playwright scraper.

Called as a subprocess by scraper.py to completely bypass the
Windows asyncio event loop limitation. Runs its own fresh event loop
in a completely separate Python process.

Usage:
    python pw_scrape.py <url>

Outputs: UTF-8 encoded plain text of the page to stdout.
"""

import sys
import io
import re

# ── Force UTF-8 stdout on Windows ────────────────────────────────────────────
# Windows console defaults to cp1252 which cannot encode many web characters.
# We reconfigure stdout to use UTF-8 before any output is written.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
from bs4 import BeautifulSoup

MAX_PAGE_CHARS = 10_000


def scrape(url: str) -> str:
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("image", "media", "font", "stylesheet")
                else route.continue_(),
            )
            page.goto(url, wait_until="domcontentloaded", timeout=40_000)
            page.wait_for_timeout(2_500)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav",
                          "footer", "header", "svg", "aside"]):
            tag.decompose()
            
        # VERY IMPORTANT: Preserve URLs so Gemini can extract them!
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Ignore useless relative links like # or /
            if len(href) > 2 and not href.startswith("javascript:"):
                # If it's a relative URL, try to make it absolute if we know the domain, 
                # but Rozee URLs are mostly absolute or root relative. 
                # Gemini is smart enough to handle root relative URLs if told the source.
                a.string = f"{a.get_text(strip=True)} ({href})"

        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:100_000]  # Let scraper.py handle the true max length

    except PwTimeout:
        sys.stderr.write(f"TIMEOUT: {url}\n")
        return ""
    except Exception as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python pw_scrape.py <url>\n")
        sys.exit(1)

    result = scrape(sys.argv[1])
    sys.stdout.write(result)
    sys.stdout.flush()
