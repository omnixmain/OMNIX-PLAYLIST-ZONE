import yt_dlp
import os
import datetime
import concurrent.futures
import time

# ==========================================
# OMNIX EMPIRE - YOUTUBE LIVE EXTRACTOR
# ==========================================

M3U_OUTPUT = "playlist/youtube.m3u"
SEARCH_LIMIT = 20  # Increased for better yield
MAX_WORKERS = 10   # Parallel workers

# Categories and Queries
# "Category Name": "Search Query"
CATEGORIES = {
    "News": "live news 24x7",
    "Music": "live music radio 24/7",
    "Gaming": "live gaming stream",
    "Sports": "live sports match",
    "Live Events": "live event stream",  # Requested specifically
    "Technology": "live technology launch",
    "Devotional": "live darshan",
    "Space": "live space station earth",
    "Animals": "live wildlife camera",
    "Entertainment": "live entertainment channel"
}

def get_stream_info(entry, category):
    """
    Extracts stream URL and details for a single video.
    Returns a dictionary or None.
    """
    video_id = entry.get('id')
    title = entry.get('title', 'Unknown Title')
    
    # Robust URL determination
    url = entry.get('url')
    if not url:
        if video_id:
            url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            # Cannot find a valid URL or ID
            return None
    
    # Options for extracting the stream url
    ydl_opts = {
        'format': 'best[protocol^=m3u8]/best',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
            }
        },
        # Standard Browser User-Agent to avoid 403s on most IPs
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.youtube.com/',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Fast extraction
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return None
            
            # 1. Verify it is actually LIVE
            if not info.get('is_live'):
                return None
            
            # 2. Get m3u8 url
            stream_url = info.get('url')
            if not stream_url:
                return None

            # 3. Get best thumbnail
            thumb = info.get('thumbnail')
            if info.get('thumbnails'):
                thumb = info['thumbnails'][-1].get('url')

            # 4. Clean Title
            clean_title = title.replace(',', '').replace('"', '').strip()

            return {
                "id": video_id,
                "title": clean_title,
                "logo": thumb or "",
                "category": category,
                "url": stream_url
            }

    except Exception:
        return None

def process_category(category, query, existing_ids):
    """
    Searches a category and returns valid live streams.
    """
    print(f" > Searching: {category}...")
    
    # 1. Search for candidates (IDs only first for speed)
    ydl_opts_search = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extract_flat': True,
        'default_search': f'ytsearch{SEARCH_LIMIT}',
        'noplaylist': True,
    }

    candidates = []
    with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
        try:
            res = ydl.extract_info(query, download=False)
            if res and 'entries' in res:
                candidates = [e for e in res['entries'] if e]
            elif res:
                candidates = [res]
        except:
            pass
            
    # Filter duplicates immediately
    unique_candidates = []
    for c in candidates:
        vid = c.get('id') or c.get('url')
        if vid and vid not in existing_ids:
            unique_candidates.append(c)
            
    if not unique_candidates:
        return []

    # 2. Validate and Extract in Parallel
    valid_streams = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_stream_info, c, category): c for c in unique_candidates}
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                valid_streams.append(res)
                existing_ids.add(res['id'])
                print(f"   [+] Added: {res['title'][:40]}...")

    return valid_streams

def generate_m3u(streams):
    """
    Generates the M3U content string.
    """
    lines = ["#EXTM3U"]
    lines.append(f"#EXTINF:-1 group-title=\"System\",Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("http://localhost/info")

    for s in streams:
        lines.append(f'#EXTINF:-1 tvg-logo="{s["logo"]}" group-title="{s["category"]}",{s["title"]}')
        lines.append(s["url"])
        
    return "\n".join(lines)

def main():
    print("--- OMNIX YOUTUBE EXTRACTOR STARTING ---")
    start_time = time.time()
    
    all_streams = []
    seen_ids = set()

    # Process all categories
    for cat, query in CATEGORIES.items():
        results = process_category(cat, query, seen_ids)
        all_streams.extend(results)

    # Save to File
    os.makedirs(os.path.dirname(M3U_OUTPUT), exist_ok=True)
    
    content = generate_m3u(all_streams)
    with open(M3U_OUTPUT, "w", encoding="utf-8") as f:
        f.write(content)

    elapsed = time.time() - start_time
    print(f"\n--- COMPLETE ---")
    print(f"Total Streams: {len(all_streams)}")
    print(f"Time Taken: {elapsed:.2f}s")
    print(f"Saved to: {M3U_OUTPUT}")

if __name__ == "__main__":
    main()
