import os
import json
import concurrent.futures
import yt_dlp
from datetime import datetime

# Categories to search for
CATEGORIES = [
    "Kids",
    "News",
    "Movie",
    "Gaming",
    "Music",
    "Program",
    "Space"
]

# Output files
PLAYLIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "playlist")
M3U_FILE = os.path.join(PLAYLIST_DIR, "yt_omnix.m3u")
JSON_FILE = os.path.join(PLAYLIST_DIR, "yt_omnix.json")

# Ensure playlist directory exists
os.makedirs(PLAYLIST_DIR, exist_ok=True)

def get_live_streams(category):
    """
    Fetches live streams for a given category using yt-dlp.
    """
    print(f"Fetching live streams for category: {category}...")
    
    # yt-dlp options
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'ignoreerrors': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    results = []
    
    query = f"{category} live"
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Search for 10 entries to increase chances of finding valid ones
            search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)
            
            if 'entries' in search_results:
                for entry in search_results['entries']:
                    if not entry:
                        continue
                        
                    video_url = entry.get('url')
                    if not video_url:
                        video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                    
                    # Add a small delay/sleep here if needed, but we are doing serial processing inside the category loop now? 
                    # No, it's parallel categories. 
                    
                    # We will try to resolve. if 403, we skip.
                    stream_info = resolve_stream_info(video_url, category)
                    if stream_info:
                        results.append(stream_info)
                        if len(results) >= 5: # Limit to 5 valid streams per category
                            break
                        
        except Exception as e:
            print(f"Error searching for {category}: {e}")
            
    return results

def resolve_stream_info(video_url, category):
    """
    Resolves the M3U8 stream URL and other details for a specific video.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best', 
        'ignoreerrors': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
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
            # print(f"Error resolving {video_url}: {e}")
            return None

def main():
    print("Starting YouTube Live Playlist Generator...")
    all_streams = []
    
    # Run sequentially debugging to avoid massive rate limits if that's the cause, 
    # or reduce workers. Let's try 3 workers.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
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
    
    if all_streams:
        generate_m3u(all_streams)
        generate_json(all_streams)
        print("Done!")
    else:
        print("No streams found. Check network or yt-dlp status.")

if __name__ == "__main__":
    main()
