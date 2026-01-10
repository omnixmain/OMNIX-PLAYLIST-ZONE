import requests
from bs4 import BeautifulSoup
import datetime
import os
import re
import json
import time

# Source URL
BASE_URL = "https://allinonereborn.xyz/sony"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://allinonereborn.xyz/sony/"
}

# Determine the directory where this script resides
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate up one level to root, then into 'playlist'
PLAYLIST_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'playlist')

# Ensure playlist directory exists
os.makedirs(PLAYLIST_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(PLAYLIST_DIR, "sony_liv.m3u")

def get_channel_links():
    try:
        print(f"Fetching main page: {BASE_URL}")
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        channel_pages = []
        
        for link in links:
            href = link['href']
            name = link.get_text(strip=True)
            
            if 'ptest.php' in href:
                if not name:
                    name = "Sony Liv Channel"
                
                # Construct the correct URL.
                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = "https://allinonereborn.xyz/sony/" + href
                
                channel_pages.append({
                    'name': name,
                    'page_url': full_url
                })
        
        print(f"Found {len(channel_pages)} channel pages.")
        return channel_pages
        
    except Exception as e:
        print(f"Error fetching channel list: {e}")
        return []

def extract_stream_url(page_url):
    try:
        print(f"  Fetching detail page: {page_url}")
        time.sleep(0.5) 
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"  Failed to load page: {response.status_code}")
            return None, None
            
        match = re.search(r'const\s+channelData\s*=\s*({.*?});', response.text)
        logo = None
        m3u8 = None
        
        if match:
            json_str = match.group(1)
            try:
                data = json.loads(json_str)
                m3u8 = data.get('m3u8')
                # Try to find logo in common fields
                logo = data.get('logo') or data.get('image') or data.get('poster')
            except json.JSONDecodeError:
                pass
        
        if not m3u8:
            m3u8_match = re.search(r'"m3u8"\s*:\s*"(.*?)"', response.text)
            if m3u8_match:
                m3u8 = m3u8_match.group(1).replace(r'\/', '/')
        
        # Fallback regex for logo if not found in JSON
        if not logo:
             logo_match = re.search(r'"(logo|image|poster)"\s*:\s*"(.*?)"', response.text)
             if logo_match:
                 logo = logo_match.group(2).replace(r'\/', '/')
                 
        if m3u8 and m3u8.startswith('http'):
            return m3u8, logo
            
        return None, None

    except Exception as e:
        print(f"  Error extracting stream: {e}")
        return None, None

def get_channels():
    pages = get_channel_links()
    valid_channels = []
    
    for page in pages:
        stream_url, logo = extract_stream_url(page['page_url'])
        if stream_url:
            print(f"  > Found stream for {page['name']}")
            valid_channels.append({
                'name': page['name'],
                'url': stream_url,
                'logo': logo or ""
            })
        else:
            print(f"  > No stream found for {page['name']}")
            
    return valid_channels

def generate_m3u(channels):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Calculate BD Time (UTC + 6)
        # Note: utcnow is deprecated, using now(datetime.timezone.utc) if possible or adjusting locally
        utc_now = datetime.datetime.utcnow()
        bd_time = utc_now + datetime.timedelta(hours=6)
        formatted_time = bd_time.strftime("%Y-%m-%d %I:%M %p")

        m3u_header = f"""#EXTM3U
#=================================
# Developed By: OMNIX EMPIER
# IPTV Telegram Channels: https://t.me/omnix_Empire
# Last Updated: {formatted_time} (BD Time)
# TV channel counts :- {len(channels)}
# Disclaimer:
# This tool does NOT host any content.
# It aggregates publicly available data for informational purposes only.
# For any issues or concerns, please contact the developer.
#==================================  """
        
        f.write(m3u_header + '\n')
        # f.write(f'#EXTINF:-1, Updated: {current_time}\n') # Removing old updated line to avoid dupes
        # f.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\n') # Header already has user agent later? No, this is global
        # Keeping global UA and status check if they are critical, but user asked for specific header.
        
        # Adding back global tags if needed by player, but standard header often replaces top metadata
        # Let's keep the user agent as it might be useful, but put it after the banner
        f.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\n')
        f.write('http://example.com/status\n\n')
        
        for channel in channels:
            name = channel['name']
            url = channel['url']
            logo = channel['logo']
            
            f.write(f'#EXTINF:-1 group-title="Sony Liv" tvg-logo="{logo}",{name}\n')
            f.write('#EXTVLCOPT:network-caching=1000\n')
            f.write(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n')
            f.write(f'#EXTVLCOPT:http-referrer={HEADERS["Referer"]}\n')
            f.write(f'{url}\n\n')
            
    print(f"Playlist generated: {OUTPUT_FILE} with {len(channels)} channels.")

if __name__ == "__main__":
    print(f"Script executing from: {SCRIPT_DIR}")
    print(f"Output targeted at: {OUTPUT_FILE}")
    channels = get_channels()
    if channels:
        generate_m3u(channels)
    else:
        print("No channels found.")
