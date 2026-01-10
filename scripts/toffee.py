import json
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import urllib.parse
import requests
import datetime

def get_channels_and_cookies():
    options = Options()
    # options.add_argument("--headless=new") # headless for background
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    print("Launching Selenium to scrape mxonlive...")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    
    base_url = "https://mxonlive.wuaze.com/toffee"
    channels_data = []
    
    try:
        print(f"Visiting {base_url}...")
        driver.get(base_url)
        time.sleep(10) # Wait for cloudflare/loading
        
        # Get Cookies/UA for M3U
        cookies = driver.get_cookies()
        if not cookies:
             print("No cookies captured!")
             cookie_str = ""
        else:
             cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        
        user_agent = driver.execute_script("return navigator.userAgent;")
        
        print(f"Captured Cookies: {cookie_str[:50]}...")
        
        # Get Channel List
        # Elements are <a class="card channel-item" href="play.php?id=...">
        elems = driver.find_elements(By.CSS_SELECTOR, "a.channel-item")
        print(f"Found {len(elems)} channels in list.")
        
        pending_channels = []
        for el in elems:
            try:
                name = el.find_element(By.CLASS_NAME, "card-title").text.strip()
                link = el.get_attribute("href") # Absolute URL
                try:
                    logo_el = el.find_element(By.TAG_NAME, "img")
                    logo = logo_el.get_attribute("src")
                except:
                    logo = ""
                
                pending_channels.append({
                    "name": name,
                    "play_url": link,
                    "logo": logo
                })
            except Exception as e:
                print(f"Error parsing listing item: {e}")

        print(f"Scraping stream URLs for {len(pending_channels)} channels...")
        
        # Limit to 5 for testing if needed, but user wants all. 
        # But for correctness, let's do all.
        for i, ch in enumerate(pending_channels):
            try:
                print(f"[{i+1}/{len(pending_channels)}] Processing {ch['name']}...")
                driver.get(ch['play_url'])
                time.sleep(6) # Wait for stream load
                
                logs = driver.get_log('performance')
                stream_url = None
                
                # Check logs for M3U8 or stream.php
                for entry in logs:
                    message = json.loads(entry['message'])['message']
                    if message['method'] == 'Network.requestWillBeSent':
                        req = message['params']['request']
                        url = req['url']
                        if ('stream.php' in url and 'play=true' in url) or '.m3u8' in url:
                             if 'mxonlive' in url:
                                 stream_url = url
                                 break
                
                if stream_url:
                    print(f"  -> Found Master URL: {stream_url}")
                    
                    # Extract Secondary/Variant URL
                    try:
                        session = requests.Session()
                        for cookie in driver.get_cookies():
                            session.cookies.set(cookie['name'], cookie['value'])
                        
                        ua = driver.execute_script("return navigator.userAgent;")
                        session.headers.update({'User-Agent': ua})
                        
                        response = session.get(stream_url)
                        if response.status_code == 200:
                            lines = response.text.splitlines()
                            for line in lines:
                                if line.strip().startswith("http") or (line.strip().endswith(".m3u8") and not line.strip().startswith("#")):
                                    # It's a variant stream
                                    stream_url = line.strip()
                                    print(f"  -> Resolved Secondary URL: {stream_url}")
                                    break
                    except Exception as parse_err:
                        print(f"  -> formatting error: {parse_err}")

                    ch['stream_url'] = stream_url
                else:
                    print(f"  -> No stream found.")
                    
            except Exception as e:
                print(f"Error scraping channel {ch['name']}: {e}")
                
        # Filter valid
        channels_data = [c for c in pending_channels if 'stream_url' in c]
        
    except Exception as e:
        print(f"Global Error: {e}")
    finally:
        driver.quit()
        
    return channels_data, cookie_str, user_agent

def generate_m3u(channels, cookie_str, user_agent):
    print(f"Generating info for {len(channels)} channels...")
    
    playlist_path = os.path.join(os.getcwd(), "playlist", "toffee.m3u")
    os.makedirs(os.path.dirname(playlist_path), exist_ok=True)
    
    with open(playlist_path, "w", encoding="utf-8") as f:
        # Calculate BD Time (UTC + 6)
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
#==================================  
"""
        f.write(m3u_header)
        
        for ch in channels:
            url = ch['stream_url']
            name = ch['name']
            logo = ch['logo']
            
            f.write(f'#EXTINF:-1 group-title="Toffee" tvg-logo="{logo}",{name}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={user_agent}\n')
            f.write(f'#EXTVLCOPT:http-cookie={cookie_str}\n')
            f.write(f'#EXTVLCOPT:http-referrer=https://mxonlive.wuaze.com/\n')
            f.write(f'{url}\n')
            
    print(f"Playlist saved to {playlist_path}")

if __name__ == "__main__":
    channels, cookie, ua = get_channels_and_cookies()
    if channels:
        generate_m3u(channels, cookie, ua)
    else:
        print("No channels extracted.")
