import json
import os
import requests
import time

def fetch_channels():
    # Source URL from Gtajisan/Toffee-channel-bypass
    json_url = "https://raw.githubusercontent.com/Gtajisan/Toffee-channel-bypass/main/toffee_channel_data.json"
    print(f"Fetching channels from {json_url}...")
    
    try:
        response = requests.get(json_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def generate_m3u(data):
    if not data or "channels" not in data:
        print("No channel data found.")
        return

    channels = data["channels"]
    print(f"Found {len(channels)} channels.")

    output_dir = "playlist"
    # Handling absolute paths or relative paths based on CWD
    # We will assume CWD is the project root, or we handle path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    playlist_dir = os.path.join(project_root, "playlist")
    
    os.makedirs(playlist_dir, exist_ok=True)
    output_path = os.path.join(playlist_dir, "toffee.m3u")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        for channel in channels:
            name = channel.get("name", "Unknown")
            link = channel.get("link", "")
            logo = channel.get("logo", "")
            category = channel.get("category_name", "Uncategorized")
            headers = channel.get("headers", {})

            if not link:
                continue

            # Write EXTINF
            f.write(f'#EXTINF:-1 group-title="{category}" tvg-logo="{logo}",{name}\n')
            
            # Write Headers for players (VLC/TiviMate/Kodi)
            # User-Agent
            if "user-agent" in headers:
                ua = headers["user-agent"]
                f.write(f'#EXTVLCOPT:http-user-agent={ua}\n')
            
            # Cookie
            if "cookie" in headers:
                cookie = headers["cookie"]
                f.write(f'#EXTVLCOPT:http-cookie={cookie}\n')
            
            # Other Headers (e.g. client-api-header)
            # VLC uses http-header-NAME=VALUE
            for key, value in headers.items():
                if key.lower() not in ["user-agent", "cookie", "host"]:
                    # Capitalize nicely or keep as is? specialized headers usually need exact case.
                    # But keys in this JSON seem lowercase "client-api-header".
                    f.write(f'#EXTVLCOPT:http-header-{key}={value}\n')

            # Host header is usually handled by the URL, but some proxies might need it.
            # Usually strict players manage Host automatically from URL.
            
            # Write URL
            f.write(f'{link}\n')

    print(f"Playlist saved to {output_path}")

def main():
    data = fetch_channels()
    generate_m3u(data)

if __name__ == "__main__":
    main()
