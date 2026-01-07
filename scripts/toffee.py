import json
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

def get_fresh_cookies():
    print("Launching Selenium to fetch fresh cookies...")
    driver = get_driver()
    cookies = {}
    try:
        # Visit a video page to ensure video-specific cookies are generated if needed, 
        # or just the home page. Toffee usually sets Edge-Cache-Cookie on global hit.
        url = "https://toffeelive.com/"
        print(f"Visiting {url}...")
        driver.get(url)
        
        print("Waiting for page load and cookie generation...")
        time.sleep(10) # Give it time to load and set cookies
        
        selenium_cookies = driver.get_cookies()
        for cookie in selenium_cookies:
            # We are specifically looking for Edge-Cache-Cookie but capturing all is safer
            cookies[cookie['name']] = cookie['value']
            if cookie['name'] == 'Edge-Cache-Cookie':
                print(f"Found Edge-Cache-Cookie: {cookie['value'][:30]}...")
        
    except Exception as e:
        print(f"Error fetching cookies: {e}")
    finally:
        driver.quit()
    return cookies

def fetch_channels():
    # Source URL from Gtajisan/Toffee-channel-bypass
    # We use this primarily for the static channel info (Logo, Name, M3U8 slug)
    json_url = "https://raw.githubusercontent.com/Gtajisan/Toffee-channel-bypass/main/toffee_channel_data.json"
    print(f"Fetching channel list template from {json_url}...")
    
    try:
        response = requests.get(json_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("channels", [])
    except Exception as e:
        print(f"Error fetching channel list: {e}")
        return []

def generate_m3u(channels, cookies):
    if not channels:
        print("No channels to write.")
        return

    # Construct the Cookie header string
    # Format: CookieName=CookieValue; NextCookie=Value
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    
    # We specifically need the Edge-Cache-Cookie for the headers usually.
    # If the JSON headers had it, we will OVERRIDE it.
    
    print(f"Generating playlist with {len(channels)} channels...")

    # Determine paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming standard structure: scripts/.. -> root -> playlist/
    project_root = os.path.dirname(script_dir) 
    # If script_dir is root/scripts, dirname is root.
    # Check if we are aiming for 'playlist' folder in project root
    playlist_dir = os.path.join(project_root, "playlist")
    
    os.makedirs(playlist_dir, exist_ok=True)
    output_path = os.path.join(playlist_dir, "toffee.m3u")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        for channel in channels:
            name = channel.get("name", "Unknown")
            link = channel.get("link", "")
            logo = channel.get("logo", "")
            category = channel.get("category_name", "Popular TV Channels")
            
            if not link:
                continue

            # Original headers from JSON (might contain static User-Agent we want to keep)
            headers = channel.get("headers", {})
            user_agent = headers.get("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Write EXTINF
            f.write(f'#EXTINF:-1 group-title="{category}" tvg-logo="{logo}",{name}\n')
            
            # Write Headers
            f.write(f'#EXTVLCOPT:http-user-agent={user_agent}\n')
            
            # Inject FRESH cookie
            if cookie_str:
                f.write(f'#EXTVLCOPT:http-cookie={cookie_str}\n')
            
            # Keep other critical headers if they exist and are static
            # client-api-header seems static or long-lived in the JSON, but it might also be rotated.
            # For now, we trust the JSON's client-api-header or ignore if missing. 
            # The Edge-Cache-Cookie is the usual timestamped one.
            for key, value in headers.items():
                k_lower = key.lower()
                if k_lower not in ["user-agent", "cookie", "host"]:
                     f.write(f'#EXTVLCOPT:http-header-{key}={value}\n')

            f.write(f'{link}\n')

    print(f"Playlist saved to {output_path}")

def main():
    # 1. Get Fresh Channels Template
    channels = fetch_channels()
    
    # 2. Get Fresh Cookies via Selenium
    cookies = get_fresh_cookies()
    
    # 3. Generate M3U
    if channels and cookies:
        generate_m3u(channels, cookies)
    else:
        print("Failed to get channels or cookies. Check errors above.")

if __name__ == "__main__":
    main()
