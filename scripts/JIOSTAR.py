#!/usr/bin/env python3
# scripts/JIOSTAR.py
# Robust playlist fetcher:
# 1) Try multiple User-Agents with requests
# 2) If response not M3U, save debug HTML and run Playwright to capture .m3u/.m3u8 network requests
# 3) Save playlist to playlist/JIOSTAR.m3u (and response-debug.html for debugging)

import os
import re
import sys
import time
import requests

from pathlib import Path

# Configuration
# Allow environment variables to override, but default to the known working values for this repo
TOKEN = os.environ.get("HOTSTAR_TOKEN")
URL_ENV = os.environ.get("HOTSTAR_URL")
# Preserving the original token/URL as fallback
DEFAULT_URL = "https://hotstarlive.delta-cloud.workers.dev/?token=240bb9-374e2e-3c13f0-4a7xz5"

OUT_PLAYLIST = "playlist/JIOSTAR.m3u"
DEBUG_HTML = "response-debug.html"

USER_AGENTS = [
    "TiviMate/4.7.0",
    "ExoPlayer/2.14.1",
    "okhttp/3.12.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
]

HEADERS_BASE = {
    "Accept": "application/vnd.apple.mpegurl,application/x-mpegURL,*/*",
    "Referer": "https://www.hotstar.com"
}

def build_url():
    if URL_ENV:
        return URL_ENV
    if TOKEN:
        return f"https://hotstarlive.delta-cloud.workers.dev/?token={TOKEN}"
    
    # Fallback to the known default if no env vars are set
    print(f"[config] Using default hardcoded URL as no HOTSTAR_TOKEN/URL env var found.")
    return DEFAULT_URL

def looks_like_m3u(text, content_type):
    if not text:
        return False
    # Check for common M3U markers
    if "EXTM3U" in text[:1024].upper():
        return True
    if content_type:
        ct = content_type.lower()
        if "mpegurl" in ct or "application/x-mpegurl" in ct or "audio/x-mpegurl" in ct:
            return True
    # also check for .m3u8 fragment (some servers return short content)
    if ".m3u8" in text[:2048]:
        return True
    return False

def try_requests_fetch(url, timeout=15):
    last_resp = None
    for ua in USER_AGENTS:
        headers = HEADERS_BASE.copy()
        headers["User-Agent"] = ua
        try:
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            last_resp = r
            ct = r.headers.get("Content-Type", "")
            snippet = r.text[:2048] if r.text else ""
            print(f"[requests] UA={ua} STATUS={r.status_code} CT={ct}")
            if looks_like_m3u(snippet, ct):
                print("[requests] Looks like M3U; saving.")
                return r.text
            # else continue trying other UAs
        except Exception as e:
            print(f"[requests] Exception with UA={ua}: {e}")
        time.sleep(0.3)
    return last_resp

def save_debug_response(resp):
    try:
        if hasattr(resp, "text"):
            Path(DEBUG_HTML).write_text(resp.text, encoding="utf-8")
            print(f"[debug] Saved HTML response to {DEBUG_HTML}")
        else:
            Path(DEBUG_HTML).write_text(str(resp), encoding="utf-8")
            print(f"[debug] Saved debug info to {DEBUG_HTML}")
    except Exception as e:
        print(f"[debug] Failed to write debug file: {e}")

def playwright_fallback(url, timeout_ms=30000):
    """
    Uses Playwright to open the page and capture responses whose URL or content-type
    indicate an m3u/m3u8. Returns the bytes of the first playlist found and its URL.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[playwright] Playwright not installed. Install with `pip install playwright` and run `playwright install`.", file=sys.stderr)
        return None, None

    candidates = []

    with sync_playwright() as p:
        # Launch with some args to allow running in container environments if needed
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(user_agent=USER_AGENTS[3]) # Use Chrome UA
        page = context.new_page()

        def on_response(response):
            try:
                urlr = response.url
                ct = response.headers.get("content-type", "") or ""
                # quick heuristic
                if ".m3u" in urlr.lower() or "mpegurl" in ct.lower() or "application/x-mpegurl" in ct.lower() or "audio/x-mpegurl" in ct.lower():
                    print(f"[playwright] Candidate response URL={urlr} CT={ct}")
                    try:
                        body = response.body()
                        candidates.append((urlr, body, ct))
                    except Exception as e:
                        print(f"[playwright] Couldn't read body for {urlr}: {e}")
            except Exception as e:
                print(f"[playwright] on_response error: {e}")

        page.on("response", on_response)

        try:
            print(f"[playwright] Navigating to {url}")
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        except Exception as e:
            print(f"[playwright] page.goto exception (continuing): {e}")

        # wait a bit for late requests
        time.sleep(2)

        # If we already captured candidates, return first valid
        if candidates:
            urlr, body, ct = candidates[0]
            print(f"[playwright] Found playlist via network: {urlr} (CT={ct})")
            browser.close()
            return body, urlr

        # If not found in responses, scan page content for .m3u/.m3u8 urls
        content = page.content()
        browser_captured = context.cookies()
        browser.close()

    # regex find URLs that end with .m3u or .m3u8 or contain m3u8 query
    url_pattern = re.compile(r"""https?://[^\s"'<>]+(?:\.m3u8?|m3u8?[^"'<>]*)""", re.IGNORECASE)
    found = url_pattern.findall(content)
    if found:
        candidate_url = found[0]
        print(f"[playwright-fallback] Found playlist URL in page content: {candidate_url}")
        # try to download with requests, using cookies if possible
        try:
            cookies = {}
            # If playwright provided cookies earlier, use them
            for c in browser_captured:
                cookies[c['name']] = c['value']
        except Exception:
            cookies = {}

        headers = HEADERS_BASE.copy()
        headers["User-Agent"] = USER_AGENTS[0]
        try:
            r = requests.get(candidate_url, headers=headers, cookies=cookies, timeout=20, allow_redirects=True)
            if r.status_code == 200 and looks_like_m3u(r.text, r.headers.get("Content-Type", "")):
                print(f"[playwright-fallback] Successfully downloaded playlist from discovered URL.")
                return r.content, candidate_url
            else:
                print(f"[playwright-fallback] Download attempt returned status {r.status_code} CT={r.headers.get('Content-Type')}")
        except Exception as e:
            print(f"[playwright-fallback] Exception downloading discovered URL: {e}")

    print("[playwright-fallback] No playlist found via Playwright.")
    return None, None

def main():
    # Ensure output dir exists
    os.makedirs(os.path.dirname(OUT_PLAYLIST), exist_ok=True)
    
    url = build_url()
    print(f"[main] Fetching URL: {url}")

    resp_or_obj = try_requests_fetch(url)
    # If resp_or_obj is a text (str) that indicates success:
    if isinstance(resp_or_obj, str):
        Path(OUT_PLAYLIST).write_text(resp_or_obj, encoding="utf-8")
        print(f"[main] Playlist saved to {OUT_PLAYLIST}")
        sys.exit(0)

    # Otherwise resp_or_obj likely a Response object or None
    if resp_or_obj is not None:
        save_debug_response(resp_or_obj)

    print("[main] Requests approach failed. Trying Playwright fallback...")
    # Playwright fallback: try capturing actual playlist request
    body, found_url = playwright_fallback(url)
    if body:
        # body may be bytes or str
        if isinstance(body, str):
            (Path(OUT_PLAYLIST)).write_text(body, encoding="utf-8")
            print(f"[main] Playlist saved to {OUT_PLAYLIST} (text)")
        else:
            with open(OUT_PLAYLIST, "wb") as f:
                f.write(body)
            print(f"[main] Playlist saved to {OUT_PLAYLIST} (binary) from {found_url}")
        sys.exit(0)

    print("[main] Failed to fetch playlist. See response-debug.html for page HTML and try manual inspection.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
