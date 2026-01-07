import requests
import datetime
import os

# Source URL
SOURCE_URL = "https://raw.githubusercontent.com/bugsfreeweb/LiveTVCollector/refs/heads/main/Movies/Private/Movies.m3u"

# Determine directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYLIST_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'playlist')
os.makedirs(PLAYLIST_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(PLAYLIST_DIR, "adult_omnix.m3u")

def fetch_playlist():
    try:
        print(f"Fetching playlist from: {SOURCE_URL}")
        response = requests.get(SOURCE_URL, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        # Add a custom header with update time
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header_info = f"#EXTINF:-1, Updated: {current_time}\n"
        
        # If the downloaded content has #EXTM3U, insert our header after it
        if "#EXTM3U" in content:
            lines = content.splitlines()
            if lines[0].startswith("#EXTM3U"):
                lines.insert(1, header_info)
                final_content = "\n".join(lines)
            else:
                final_content = "#EXTM3U\n" + header_info + content
        else:
            final_content = "#EXTM3U\n" + header_info + content
            
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        print(f"Playlist saved to: {OUTPUT_FILE}")
        print(f"Total size: {len(final_content)} bytes")
        
    except Exception as e:
        print(f"Error fetching playlist: {e}")

if __name__ == "__main__":
    fetch_playlist()
