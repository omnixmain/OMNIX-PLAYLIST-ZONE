import yt_dlp
import os
import datetime
import concurrent.futures

# Output Files
M3U_OUTPUT = "playlist/youtube.m3u"

# Categories and their search queries
# We search for "live [topic]" to find relevant streams
CATEGORIES = {
    "News": "live news india",
    "Gaming": "live gaming stream",
    "Music": "lofi hip hop radio - beats to relax/study to",
    "Sports": "live cricket match",
    "Devotional": "live darshan aarti",
    "Technology": "live technology event",
    "Cartoons": "live cartoons for kids",
    "Animals": "live wildlife cam",
    "Space": "nasa live stream"
}

# Number of search results to check per category
SEARCH_LIMIT = 15
# Number of concurrent checks
MAX_WORKERS = 10

def get_stream_details(entry, category):
    """
    Worker function to process a single video entry.
    """
    video_id = entry.get('id')
    title = entry.get('title', 'Unknown Title')
    url = entry.get('url') or f"https://www.youtube.com/watch?v={video_id}"
    
    # We need to resolve the direct stream URL efficiently
    # We only want live streams
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
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We explicitly check this video now
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return None
                
            # STRICT Live Check
            if info.get('live_status') != 'is_live' and not info.get('is_live'):
                return None
                
            stream_url = info.get('url')
            
            # Thumbnails
            thumb = info.get('thumbnail')
            if not thumb and info.get('thumbnails'):
                thumb = info['thumbnails'][-1].get('url') # Best quality
            
            # Print success (sanitized)
            try:
                safe_title = title.encode('utf-8', 'ignore').decode('utf-8')
                print(f"  [+] Found LIVE: {safe_title}")
            except:
                print(f"  [+] Found LIVE: {video_id}")

            return {
                "title": title,
                "logo": thumb or "",
                "category": category,
                "stream_url": stream_url,
                "source_url": info.get('webpage_url')
            }

    except Exception as e:
        # print(f"  [-] Error checking {video_id}: {e}")
        return None

def get_live_streams_for_category(category, query):
    """
    Searches for videos in a category and validates them in parallel.
    """
    print(f"Searching category: {category} ('{query}')...")
    
    # 1. FAST SEARCH: Get list of candidates
    ydl_opts_search = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extract_flat': True, # KEY: Don't extract details, just IDs
        'default_search': f'ytsearch{SEARCH_LIMIT}',
        'noplaylist': True, 
    }
    
    candidates = []
    with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
        try:
            result = ydl.extract_info(query, download=False)
            if result:
                if 'entries' in result:
                    candidates = [e for e in result['entries'] if e]
                else:
                    candidates = [result]
        except Exception as e:
            print(f"Error checking category {category}: {e}")
            return []
            
    if not candidates:
        return []

    print(f"  -> Found {len(candidates)} candidates. Validating...")

    # 2. PARALLEL VALIDATION
    valid_streams = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit tasks
        future_to_entry = {
            executor.submit(get_stream_details, entry, category): entry 
            for entry in candidates
        }
        
        for future in concurrent.futures.as_completed(future_to_entry):
            result = future.result()
            if result:
                valid_streams.append(result)
                
    return valid_streams

def generate_m3u(events):
    content = "#EXTM3U\n"
    for event in events:
        title = event.get("title", "Unknown")
        logo = event.get("logo", "")
        category = event.get("category", "Uncategorized")
        url = event.get("stream_url", "")
        
        # Clean specific characters from title for M3U safety
        safe_title = title.replace(",", " ").replace('"', '').strip()
        
        if url:
            content += f'#EXTINF:-1 tvg-logo="{logo}" group-title="{category}",{safe_title}\n'
            content += f'{url}\n'
    return content

def main():
    final_events = []
    
    print("Starting Dynamic YouTube Live Extraction (Optimized)...")
    start_time = datetime.datetime.now()
    
    for cat, query in CATEGORIES.items():
        results = get_live_streams_for_category(cat, query)
        final_events.extend(results)
        print(f"  > Added {len(results)} confirmed streams for {cat}")

    # Ensure output dir exists
    output_dir = os.path.dirname(M3U_OUTPUT)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Write M3U
    m3u_content = generate_m3u(final_events)
    with open(M3U_OUTPUT, "w", encoding="utf-8") as f:
        f.write(m3u_content)
        
    duration = datetime.datetime.now() - start_time
    print(f"Generated {M3U_OUTPUT} with {len(final_events)} streams in {duration}.")

if __name__ == "__main__":
    main()
