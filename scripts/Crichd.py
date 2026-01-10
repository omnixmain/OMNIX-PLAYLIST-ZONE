import requests
import re
import json
import os
import time
import concurrent.futures
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)

TARGET_URL = "http://xown.site/web/crichd"
OUTPUT_FILE = "Crichd.m3u"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "http://xown.site/web/crichd/index.php"
}

def get_stream_url(channel_info):
    """Fetches the actual stream URL from the play.php page."""
    play_url = f"{TARGET_URL}/play.php?id={channel_info['id']}"
    try:
        response = requests.get(play_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            # Extract video URL
            match = re.search(r"const videoUrl = '(.*?)';", response.text)
            if match:
                channel_info['stream_url'] = match.group(1)
                return channel_info
    except Exception as e:
        print(f"{Fore.RED}[!] Failed to fetch stream for {channel_info['name']}: {e}")
    
    return None

def fetch_and_refresh():
    print(f"{Fore.CYAN}[*] Fetching live data from: {TARGET_URL}...")
    
    # Determine directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    playlist_dir = os.path.join(os.path.dirname(script_dir), 'playlist')
    os.makedirs(playlist_dir, exist_ok=True)
    
    output_path = os.path.join(playlist_dir, OUTPUT_FILE)
    
    try:
        response = requests.get(TARGET_URL + "/index.php", headers=HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
        
        # Regex to extract channel details
        # Looking for: <a href="play.php?id=..." ... <img src="..." ... <h6 class="card-title">...</h6>
        channel_pattern = re.compile(
            r'<a href="play\.php\?id=(?P<id>[a-f0-9]+)"[^>]*>.*?<img src="(?P<logo>[^"]+)"[^>]*>.*?<h6 class="card-title">(?P<name>.*?)</h6>',
            re.DOTALL
        )
        
        matches = channel_pattern.finditer(html)
        channels_to_fetch = []
        
        for match in matches:
            channels_to_fetch.append({
                'id': match.group('id'),
                'logo': match.group('logo'),
                'name': match.group('name').strip(),
                'group': 'Sports' # Default group
            })
            
        if not channels_to_fetch:
            print(f"{Fore.RED}[!] Error: Could not find any channels in the main page.")
            return

        print(f"{Fore.YELLOW}[*] Found {len(channels_to_fetch)} channels. Fetching stream links concurrently...")

        valid_channels = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_channel = {executor.submit(get_stream_url, channel): channel for channel in channels_to_fetch}
            for future in concurrent.futures.as_completed(future_to_channel):
                result = future.result()
                if result and result.get('stream_url'):
                    valid_channels.append(result)
                    print(f"{Fore.GREEN}[+] Processed: {result['name']}")

        print(f"{Fore.GREEN}[+] Successfully extracted {len(valid_channels)} valid streams.")
        
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
# TV channel counts :- {len(valid_channels)}
# Disclaimer:
# This tool does NOT host any content.
# It aggregates publicly available data for informational purposes only.
# For any issues or concerns, please contact the developer.
#==================================  """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(m3u_header + "\n")
            
            # Sort or keep order? 'as_completed' messes up order. Let's restore parsing order if possible, 
            # but simple append is fine for now or we can sort by name.
            valid_channels.sort(key=lambda x: x['name'])

            for channel in valid_channels:
                f.write(f'#EXTINF:-1 tvg-id="{channel["name"]}" tvg-logo="{channel["logo"]}" group-title="{channel["group"]}", {channel["name"]}\n')
                f.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
                f.write(f"{channel['stream_url']}\n")
        
        print(f"{Fore.GREEN}[SUCCESS] Playlist updated: {output_path}")
        print(f"{Fore.YELLOW}[INFO] Run this script anytime to refresh links!")

    except Exception as e:
        print(f"{Fore.RED}[!] Failed to refresh playlist: {e}")

if __name__ == "__main__":
    print(f"{Fore.MAGENTA}=== OMNIX REFRESHER TOOL ==={Style.RESET_ALL}")
    fetch_and_refresh()
