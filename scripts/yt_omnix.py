import os
import json
import concurrent.futures
import yt_dlp
from datetime import datetime, timedelta, timezone

# Categories to search for
CATEGORIES = [
    "Kids",
    "News",
    "Movie",
    "Gaming",
    "Music",
    "Program",
    "Space",
    "Sports",
    "Cricket",
    "Football"
]

# Common User-Agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Output files
PLAYLIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "playlist")
M3U_FILE = os.path.join(PLAYLIST_DIR, "yt_omnix.m3u")
JSON_FILE = os.path.join(PLAYLIST_DIR, "yt_omnix.json")
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

# Ensure playlist directory exists
os.makedirs(PLAYLIST_DIR, exist_ok=True)

# Clients to try for fetching data
CLIENTS = ['android', 'ios', 'tv', 'web']

def get_live_streams(category):
    """
    Fetches live streams for a given category using yt-dlp with client fallback strategies.
    """
    print(f"Fetching live streams for category: {category}...")
    
    results = []
    query = f"{category} live"
    
    for client in CLIENTS:
        print(f"  Trying client: {client}...")
        
        # yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'ignoreerrors': True,
            # 'user_agent': USER_AGENT, # Do NOT set user_agent when using player_client
            'extractor_args': {'youtube': {'player_client': [client]}},
        }
        
        # Add cookies if available
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE
            # Enable verbose logging if using cookies to debug potential issues, or if explicitly needed
            # ydl_opts['verbose'] = True 

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # INCREASED: Search for 60 entries to get "big data"
                search_results = ydl.extract_info(f"ytsearch60:{query}", download=False)
                
                if 'entries' in search_results:
                    entries = [e for e in search_results['entries'] if e]
                    print(f"    Found {len(entries)} raw entries with {client}.")
                    
                    if not entries:
                        print(f"    No entries found with {client}, trying next...")
                        continue

                    valid_count = 0
                    for entry in entries:
                        video_url = entry.get('url')
                        if not video_url:
                            # Construct URL if missing
                            video_id = entry.get('id')
                            if video_id:
                                video_url = f"https://www.youtube.com/watch?v={video_id}"
                            else:
                                continue
                        
                        # Resolve stream info using the SAME client that worked for listing
                        stream_info = resolve_stream_info(video_url, category, client_type=client)
                        if stream_info:
                            results.append(stream_info)
                            valid_count += 1
                            # INCREASED: Limit to 30 valid streams per category
                            if len(results) >= 30: 
                                break
                    
                    if valid_count > 0:
                        print(f"    Successfully extracted {valid_count} valid streams with {client}.")
                        # If we found data, stop trying other clients for this category
                        break
                    else:
                         print(f"    Found entries but failed to resolve streams with {client}. Trying next...")

            except Exception as e:
                print(f"    Error searching with {client}: {e}")
                
        if results:
            break
            
    if not results:
        print(f"Warning: Could not find any streams for {category} with any client.")

    return results

def resolve_stream_info(video_url, category, client_type='android', retries=2):
    """
    Resolves the M3U8 stream URL and other details for a specific video.
    Includes simple retry logic and client consistency.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best', 
        'ignoreerrors': True,
        # 'user_agent': USER_AGENT, # Do NOT set user_agent when using player_client
        'extractor_args': {'youtube': {'player_client': [client_type]}},
    }
    
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE
    
    for attempt in range(retries + 1):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    return None
                
                # Check if it is actually live
                if not info.get('is_live'):
                    return None
                    
                return {
                    "name": info.get('title', 'Unknown Title'),
                    "logo": info.get('thumbnail', ''),
                    "url": info.get('url', ''), 
                    "category": category,
                    "channel": info.get('uploader', 'Unknown Channel')
                }
            except Exception as e:
                if attempt == retries:
                    # Only print on final failure to reduce noise
                    # print(f"Error resolving {video_url} after retries: {e}")
                    pass
                # Backoff slightly if needed, but keeping it fast for now
                continue
    return None

def generate_m3u(streams):
    print(f"Generating M3U playlist with {len(streams)} streams...")
    # BD Time (UTC + 6)
    utc_now = datetime.now(timezone.utc)
    bd_time = utc_now + timedelta(hours=6)
    formatted_time = bd_time.strftime("%Y-%m-%d %I:%M %p")

    m3u_header = f"""#EXTM3U
#=================================
# Developed By: OMNIX EMPIRE
# Source: YouTube Live API
# Last Updated: {formatted_time} (BD Time)
# Total Channels: {len(streams)}
#================================="""
    
    # Calculate file write manually without join to ensure line control
    with open(M3U_FILE, 'w', encoding='utf-8') as f:
        f.write(m3u_header + '\n')
        
        for stream in streams:
            name = stream.get('name', 'Unknown')
            logo = stream.get('logo', '')
            url = stream.get('url', '')
            group = stream.get('category', 'Uncategorized')
            channel_name = stream.get('channel', '')
            
            # Write #EXTINF line
            f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{name} ({channel_name})\n')
            # Write User-Agent headers
            f.write(f'#EXTVLCOPT:http-user-agent={USER_AGENT}\n')
            f.write(f'#EXTHTTP:{{"User-Agent": "{USER_AGENT}"}}\n')
            # Write URL
            f.write(f'{url}\n')

    print(f"Saved M3U to {M3U_FILE}")

def generate_json(streams):
    print(f"Saving JSON to {JSON_FILE}...")
    data = {
        "updated": datetime.now().isoformat(),
        "total": len(streams),
        "streams": streams
    }
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print("Saved JSON.")

def main():
    print("Starting YouTube Live Playlist Generator...")
    all_streams = []
    
    # Use ThreadPoolExecutor to fetch categories in parallel
    # Increased workers slightly to speed up since we are processing more
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_category = {executor.submit(get_live_streams, cat): cat for cat in CATEGORIES}
        for future in concurrent.futures.as_completed(future_to_category):
            category = future_to_category[future]
            try:
                streams = future.result()
                all_streams.extend(streams)
                print(f"Found {len(streams)} streams for {category}")
            except Exception as e:
                print(f"Exception for category {category}: {e}")
    
    print(f"Total streams found: {len(all_streams)}")
    
    # Always generate, even if empty, to update timestamp/show state
    generate_m3u(all_streams)
    generate_json(all_streams)
    print("Done!")

if __name__ == "__main__":
    main()
