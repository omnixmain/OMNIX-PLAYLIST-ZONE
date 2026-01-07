import requests
import re
import json
import os
import time
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)

TARGET_URL = "https://crichd.xfireflix.workers.dev"
OUTPUT_FILE = "Crichd.m3u"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_and_refresh():
    print(f"{Fore.CYAN}[*] Fetching live data from: {TARGET_URL}...")
    
    # Determine directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    playlist_dir = os.path.join(os.path.dirname(script_dir), 'playlist')
    os.makedirs(playlist_dir, exist_ok=True)
    
    output_path = os.path.join(playlist_dir, OUTPUT_FILE)
    
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
        
        # Extract channels JSON
        match = re.search(r'let channels = (\[.*?\]);', html, re.DOTALL)
        if not match:
            print(f"{Fore.RED}[!] Error: Could not find channels data in page source.")
            return

        json_str = match.group(1)
        channels = json.loads(json_str)
        
        print(f"{Fore.GREEN}[+] Successfully extracted {len(channels)} channels.")
        
        # Calculate BD Time (UTC + 6)
        import datetime
        utc_now = datetime.datetime.utcnow()
        bd_time = utc_now + datetime.timedelta(hours=6)
        formatted_time = bd_time.strftime("%Y-%m-%d %I:%M %p")

        m3u_header = f"""#EXTM3U
#=================================
# Developed By: OMNIX EMPIER
# IPTV Telegram Channels: https://t.me/omnix_Empire
# Last Updated: {formatted_time} (BD Time)
# Disclaimer:
# This tool does NOT host any content.
# It aggregates publicly available data for informational purposes only.
# For any issues or concerns, please contact the developer.
#=================================="""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(m3u_header + "\n")
            
            for channel in channels:
                name = channel.get('name', 'Unknown Channel')
                logo = channel.get('logo', '')
                url = channel.get('link', '')
                
                # Critical Headers for Playback
                referer = channel.get('referer', 'https://profamouslife.com/')
                origin = channel.get('origin', 'https://profamouslife.com')
                ua = HEADERS["User-Agent"]
                
                # Category (default to Sports)
                group = "Sports"
                
                # Write EXTINF metadata
                f.write(f'#EXTINF:-1 tvg-id="{channel.get("id", "")}" tvg-logo="{logo}" group-title="{group}", {name}\n')
                
                # VLC Headers (Standard)
                f.write(f'#EXTVLCOPT:http-referrer={referer}\n')
                f.write(f'#EXTVLCOPT:http-user-agent={ua}\n')
                
                # TiviMate / Kodi / Smarters Headers (Appended to URL)
                # Syntax: |User-Agent=...&Referer=...
                params = [f'User-Agent={ua}', f'Referer={referer}']
                if origin:
                     params.append(f'Origin={origin}')
                
                final_url = f"{url}|{'&'.join(params)}"
                
                f.write(f"{final_url}\n")
        
        print(f"{Fore.GREEN}[SUCCESS] Playlist updated: {output_path}")
        print(f"{Fore.YELLOW}[INFO] Run this script anytime to refresh links!")

    except Exception as e:
        print(f"{Fore.RED}[!] Failed to refresh playlist: {e}")

if __name__ == "__main__":
    print(f"{Fore.MAGENTA}=== OMNIX REFRESHER TOOL ==={Style.RESET_ALL}")
    fetch_and_refresh()
