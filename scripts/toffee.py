import re
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

BASE_URL = "https://mxonlive.wuaze.com/toffee"

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

def get_stream_url(session, url_suffix, name):
    full_url = f"{BASE_URL}/{url_suffix}"
    try:
        r = session.get(full_url, timeout=15)
        if r.status_code != 200:
            return None
        
        html = r.text
        
        # Regex for stream
        # M3U8
        m3u8_match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html)
        if m3u8_match:
            return m3u8_match.group(1)
        
        # stream.php
        php_match = re.search(r'["\'](stream\.php\?[^"\']+)["\']', html)
        if php_match:
            return f"{BASE_URL}/{php_match.group(1)}"
            
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        
    return None

def main():
    print("Launching Selenium to bypass protection...")
    driver = get_driver()
    
    try:
        driver.get(f"{BASE_URL}/")
        print("Waiting for page load...")
        time.sleep(10) # Wait for challenge
        
        title = driver.title
        print(f"Page Title: {title}")
        
        html = driver.page_source
        
        # Extract Cookies
        selenium_cookies = driver.get_cookies()
        
        # Create requests session
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{BASE_URL}/"
        })
        
        for cookie in selenium_cookies:
            s.cookies.set(cookie['name'], cookie['value'])
            
        driver.quit()
        
        unique_channels = {}

        if BeautifulSoup:
            soup = BeautifulSoup(html, 'html.parser')
            sections = soup.find_all(class_='category-section')
            
            if sections:
                print(f"Found {len(sections)} categories via BeautifulSoup.")
                for section in sections:
                    # Get Category Name
                    cat_title_el = section.find(class_='cat-title')
                    category = cat_title_el.get_text(strip=True) if cat_title_el else "Other"
                    
                    # Find channels
                    channels = section.find_all(class_='channel-item')
                    
                    for ch_el in channels:
                        href = ch_el.get('href')
                        if not href and ch_el.name != 'a':
                            parent = ch_el.find_parent('a')
                            if parent: href = parent.get('href')
                            
                        if not href or 'play.php?id=' not in href:
                            continue
                            
                        id_match = re.search(r'id=([^&]+)', href)
                        url_suffix = f"play.php?id={id_match.group(1)}" if id_match else href

                        if url_suffix in unique_channels:
                            continue

                        # Extract Logo
                        img = ch_el.find('img')
                        logo = img.get('src') if img else ""
                        if logo and not logo.startswith('http'):
                            logo = f"{BASE_URL}/{logo}"
                            
                        # Extract Name
                        title_el = ch_el.find(class_='card-title')
                        raw_name = title_el.get_text(strip=True) if title_el else ch_el.get_text(strip=True)
                        
                        clean_name = raw_name
                        # Remove junk if any
                        clean_name = re.sub(r'group-title="[^"]+",?', '', clean_name)
                        
                        # Remove image path artifacts at the start
                        # Matches anything ending in .png", .webp", .jpg" followed by space or just the quote
                        clean_name = re.sub(r'^.*?\.(png|webp|jpg)["\s]+', '', clean_name, flags=re.IGNORECASE)
                        
                        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                        clean_name = clean_name.lstrip(', ')
                        
                        if not clean_name:
                            clean_name = "Channel " + url_suffix

                        unique_channels[url_suffix] = (url_suffix, clean_name, logo, category)
        
        # Fallback or if empty
        if not unique_channels:
            print("Fallback to Regex parsing...")
            LINK_PATTERN = r'<a[^>]+href=["\'](play\.php\?id=[^"\']+)["\'][^>]*>(.*?)</a>'
            LOGO_PATTERN = r'<img[^>]+src=["\']([^"\']+)["\']'
            
            matches = re.findall(LINK_PATTERN, html, re.DOTALL | re.IGNORECASE)
            for url_suffix, content in matches:
                if url_suffix in unique_channels: continue
                
                logo_match = re.search(LOGO_PATTERN, content)
                logo = logo_match.group(1) if logo_match else ""
                if logo and not logo.startswith("http"):
                    logo = f"{BASE_URL}/{logo}"
                    
                clean_name = re.sub(r'<[^>]+>', '', content).strip()
                clean_name = re.sub(r'w_\d+,[^ ]+', '', clean_name)
                clean_name = re.sub(r'q_\d+,[^ ]+', '', clean_name)
                
                group = "Toffee TV"
                group_match = re.search(r'group-title=["\']([^"\']+)["\']', clean_name)
                if group_match:
                    group = group_match.group(1)
                    clean_name = clean_name.replace(group_match.group(0), '')
                
                clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                clean_name = clean_name.lstrip(', ')
                
                if not clean_name: clean_name = "Channel " + url_suffix
                
                unique_channels[url_suffix] = (url_suffix, clean_name, logo, group)

        work_items = list(unique_channels.values())
        results = []
        
        print(f"Processing {len(work_items)} channels...")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_map = {executor.submit(get_stream_url, s, item[0], item[1]): item for item in work_items}
            
            for future in as_completed(future_map):
                item = future_map[future]
                stream_url = future.result()
                if stream_url:
                    results.append({
                        "name": item[1],
                        "logo": item[2],
                        "url": stream_url,
                        "group": item[3]
                    })
                    print(f"Found: {item[1]} ({item[3]})")

        if results:
            content = "#EXTM3U\n"
            for res in results:
                content += f'#EXTINF:-1 group-title="{res["group"]}" tvg-logo="{res["logo"]}",{res["name"]}\n'
                content += f'{res["url"]}\n'
                
            output_dir = "playlist"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "toffee.m3u")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Playlist saved to {output_path}")
            
    except Exception as e:
        print(f"Error: {e}")
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    main()
