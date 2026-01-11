#!/usr/bin/env python3
# scripts/JIOSTAR.py
# Robust playlist fetcher:
# 1) Try multiple User-Agents with requests
# 2) If response not M3U, save debug HTML and run Playwright to capture .m3u/.m3u8 network requests
# 3) Save playlist to playlist.m3u (and response-debug.html for debugging)

import os
import re
import sys
import time
import requests
from pathlib import Path

TOKEN = os.environ.get("HOTSTAR_TOKEN")
URL_ENV = os.environ.get("HOTSTAR_URL")
OUT_PLAYLIST = "playlist.m3u"
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
    print("ERROR: No HOTSTAR_TOKEN or HOTSTAR_URL provided. Set HOTSTAR_URL env or HOTSTAR_TOKEN secret.", file=sys.stderr)
    sys.exit(2)

def looks_like_m3u(text, content_type):
    if not text:
        return False
    # first chunk check
    if "EXTM3U" in text[:1024].upper():
        return True
    if content_type:
        ct = content_type.lower()
        if "mpegurl" in ct or "application/x-mpegurl" in ct or "audio/x-mpegurl" in ct:
            return True
    if ".m3u8" in text[:2048] or ".m3u" in text[:2048]:
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
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[playwright] Playwright not installed. Install with `pip install playwright` and run `playwright install`.", file=sys.stderr)
        return None, None

    candidates = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_response(response):
            try:
                urlr = response.url
                ct = response.headers.get("content-type", "") or ""
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

        time.sleep(2)

        if candidates:
            urlr, body, ct = candidates[0]
            print(f"[playwright] Found playlist via network: {urlr} (CT={ct})")
            browser.close()
            return body, urlr

        content = page.content()
        browser_captured = context.cookies()
        browser.close()

    url_pattern = re.compile(r"""https?://[^\s"'<>]+(?:\.m3u8?|m3u8?[^"'<>]*)""", re.IGNORECASE)
    found = url_pattern.findall(content)
    if found:
        candidate_url = found[0]
        print(f"[playwright-fallback] Found playlist URL in page content: {candidate_url}")
        try:
            cookies = {}
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
    url = build_url()
    print(f"[main] Fetching URL: {url}")

    resp_or_obj = try_requests_fetch(url)
    if isinstance(resp_or_obj, str):
        Path(OUT_PLAYLIST).write_text(resp_or_obj, encoding="utf-8")
        print(f"[main] Playlist saved to {OUT_PLAYLIST}")
        sys.exit(0)

    if resp_or_obj is not None:
        save_debug_response(resp_or_obj)

    body, found_url = playwright_fallback(url)
    if body:
        if isinstance(body, str):
            Path(OUT_PLAYLIST).write_text(body, encoding="utf-8")
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
