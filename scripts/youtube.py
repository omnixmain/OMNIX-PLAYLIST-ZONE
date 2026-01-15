import yt_dlp
import os
import datetime
import concurrent.futures
import time

# ==========================================
# OMNIX EMPIRE - YOUTUBE LIVE EXTRACTOR
# ==========================================

M3U_OUTPUT = "playlist/youtube.m3u"
SEARCH_LIMIT = 20  
MAX_WORKERS = 10   

import yt_dlp
import os
import datetime
import concurrent.futures
import time

# ==========================================
# OMNIX EMPIRE - YOUTUBE LIVE EXTRACTOR
# ==========================================

M3U_OUTPUT = "playlist/youtube.m3u"
SEARCH_LIMIT = 20  
MAX_WORKERS = 10   

# The "YouTube Live" Topic Channel (Best source for trending live)
YOUTUBE_LIVE_DESTINATION = "https://www.youtube.com/channel/UC4R8DWoMoI7CAwX8_LjQHig/streams"

CATEGORIES = {
    # (Category Name, Type, Query/URL)
    "Trending Live": ("channel", YOUTUBE_LIVE_DESTINATION), 
    "News": ("search", "live news"),
    "Music": ("search", "live music"),
    "Gaming": ("search", "live gaming"),
    "Sports": ("search", "live sports"),
    "Kids": ("search", "live cartoons for kids"),
    "Movies": ("search", "live movies"),
    "Tech": ("search", "live technology"),
    "Animals": ("search", "live animals"),
}

def get_stream_info(entry, category):
    video_id = entry.get('id')
    title = entry.get('title', 'Unknown Title')
    
    # Robust URL determination
    url = entry.get('url')
    if not url:
        if video_id:
            url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            return None

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
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return None
            
            # Key check: is_live must be True
            if not info.get('is_live'):
                return None
            
            stream_url = info.get('url')
            if not stream_url:
                return None

            thumb = info.get('thumbnail')
            if info.get('thumbnails'):
                thumb = info['thumbnails'][-1].get('url')

            clean_title = title.replace(',', '').replace('"', '').strip()

            print(f"   [+] Found: {clean_title[:30]}", flush=True)

            return {
                "id": video_id,
                "title": clean_title,
                "logo": thumb or "",
                "category": category,
                "url": stream_url
            }

    except Exception:
        return None

def process_source(category, source_type, source_query, existing_ids):
    print(f" > Processing: {category}...", flush=True)
    
    candidates = []
    
    ydl_opts_search = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extract_flat': True,
        'noplaylist': True,
    }

    if source_type == "search":
        ydl_opts_search['default_search'] = f'ytsearch{SEARCH_LIMIT}'
        query = source_query
        # Try to append " live" to ensure we get live results if not present
        if "live" not in query.lower():
            query += " live"
    else:
        # For channels, we just pass the URL
        ydl_opts_search['playlist_items'] = f'1-{SEARCH_LIMIT}' # Limit items
        query = source_query

    with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
        try:
            res = ydl.extract_info(query, download=False)
            if res and 'entries' in res:
                candidates = [e for e in res['entries'] if e]
            elif res:
                candidates = [res]
        except:
            pass
            
    unique_candidates = []
    for c in candidates:
        vid = c.get('id') or c.get('url')
        if vid and vid not in existing_ids:
            unique_candidates.append(c)
            
    if not unique_candidates:
        return []

    valid_streams = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_stream_info, c, category): c for c in unique_candidates}
        
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                if res:
                    valid_streams.append(res)
                    existing_ids.add(res['id'])
            except:
                pass

    return valid_streams

def generate_m3u(streams):
    lines = ["#EXTM3U"]
    lines.append(f"#EXTINF:-1 group-title=\"System\",Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("http://localhost/info")

    for s in streams:
        lines.append(f'#EXTINF:-1 tvg-logo="{s["logo"]}" group-title="{s["category"]}",{s["title"]}')
        lines.append(s["url"])
        
    return "\n".join(lines)

def main():
    print("--- OMNIX YOUTUBE EXTRACTOR STARTING ---", flush=True)
    start_time = time.time()
    
    all_streams = []
    seen_ids = set()

    for cat, (stype, squery) in CATEGORIES.items():
        results = process_source(cat, stype, squery, seen_ids)
        all_streams.extend(results)

    os.makedirs(os.path.dirname(M3U_OUTPUT), exist_ok=True)
    
    content = generate_m3u(all_streams)
    with open(M3U_OUTPUT, "w", encoding="utf-8") as f:
        f.write(content)

    elapsed = time.time() - start_time
    print(f"\n--- COMPLETE ---")
    print(f"Total Streams: {len(all_streams)}")
    print(f"Saved to: {M3U_OUTPUT}")

if __name__ == "__main__":
    main()
