import yt_dlp
import os
import datetime

# Output Files
M3U_OUTPUT = "playlist/youtube.m3u"

# Categories and their search queries
# We search for "live [topic]" to find relevant streams
CATEGORIES = {
    "News": "live news india",
    "Gaming": "live gaming stream",
    "Music": "lofi hip hop radio - beats to relax/study to", # Specific queries often yield better results
    "Sports": "live cricket match",
    "Devotional": "live darshan aarti",
    "Technology": "live technology event",
    "Cartoons": "live cartoons for kids",
    "Animals": "live wildlife cam",
    "Space": "nasa live stream"
}

# Number of search results to check per category
SEARCH_LIMIT = 15

def get_live_streams_from_search(query, category):
    streams = []
    
    ydl_opts = {
        'format': 'best[protocol^=m3u8]/best', # Prefer HLS
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extract_flat': False, # Force full extraction to get accurate live status
        'default_search': f'ytsearch{SEARCH_LIMIT}',
        'noplaylist': True, 
    }
    
    print(f"Searching category: {category} ('{query}')...")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # ytsearch returns a payload that looks like a playlist
            result = ydl.extract_info(query, download=False)
            
            if not result:
                return []
                
            entries = []
            if 'entries' in result:
                entries = result['entries']
            else:
                entries = [result]

            for entry in entries:
                if not entry: continue
                
                # STRICT Live Filter
                # live_status can be 'is_live', 'is_upcoming', 'was_live', 'not_live', or None
                if entry.get('live_status') != 'is_live' and not entry.get('is_live'):
                    continue

                url = entry.get('url')
                title = entry.get('title', 'Unknown Title')
                
                # Improved Logo/Thumbnail finding
                thumb = entry.get('thumbnail')
                if not thumb and entry.get('thumbnails'):
                    # Try to get the last (usually highest quality) thumbnail
                    thumb = entry['thumbnails'][-1].get('url')
                
                # Fallback if no thumb
                if not thumb:
                    thumb = ""
                
                if url:
                    # Sanitize title for console
                    try:
                        safe_title = title.encode('utf-8', 'ignore').decode('utf-8')
                        print(f"  -> Found LIVE: {safe_title}")
                    except:
                        print("  -> Found LIVE: (Title hidden)")
                        
                    streams.append({
                        "title": title,
                        "logo": thumb,
                        "category": category,
                        "stream_url": url,
                        "source_url": entry.get('webpage_url')
                    })
                    
        except Exception as e:
            # print(f"Error searching {category}: {e}")
            pass
            
    return streams

def generate_m3u(events):
    content = "#EXTM3U\n"
    for event in events:
        title = event.get("title", "Unknown")
        logo = event.get("logo", "")
        category = event.get("category", "Uncategorized")
        url = event.get("stream_url", "")
        
        # Clean specific characters from title for M3U safety
        safe_title = title.replace(",", " ").replace('"', '')
        
        if url:
            content += f'#EXTINF:-1 tvg-logo="{logo}" group-title="{category}",{safe_title}\n'
            content += f'{url}\n'
    return content

def main():
    final_events = []
    
    print("Starting Dynamic YouTube Live Extraction...")
    
    for cat, query in CATEGORIES.items():
        results = get_live_streams_from_search(query, cat)
        final_events.extend(results)
        print(f"  > Added {len(results)} streams for {cat}")

    # Ensure output dir exists
    output_dir = os.path.dirname(M3U_OUTPUT)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Write M3U
    m3u_content = generate_m3u(final_events)
    with open(M3U_OUTPUT, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"Generated {M3U_OUTPUT} with {len(final_events)} total streams.")

if __name__ == "__main__":
    main()

