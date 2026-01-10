import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import os
import concurrent.futures

# Configuration
BASE_URL = "https://v5on.site"
PLAYLIST_FILE = "playlist/omni_v5on.m3u"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://v5on.site/",
}

# Use a session for connection pooling
session = requests.Session()
session.headers.update(HEADERS)

def get_bd_time():
    """Returns the current time in Bangladesh timezone."""
    bd_tz = pytz.timezone('Asia/Dhaka')
    now = datetime.datetime.now(bd_tz)
    return now.strftime("%Y-%m-%d %I:%M %p (BD Time)")

def fetch_soup(url):
    """Fetches a URL and returns a BeautifulSoup object."""
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_categories():
    """Scrapes categories from the homepage."""
    soup = fetch_soup(BASE_URL)
    categories = []
    if soup:
        # Prioritize 'All' or main listing if evident, but let's just grab all links with ?cat=
        # The user observation implies 'All' might have everything.
        
        # Look for the 'All' category specifically to put it first if possible
        # But generic scraping is safer.
        buttons = soup.find_all(['button', 'a'], href=True)
        for btn in buttons:
            href = btn['href']
            if '?cat=' in href:
                # Convert relative to absolute
                full_url = BASE_URL + "/" + href if not href.startswith('http') else href
                name = btn.get_text(strip=True)
                
                # Check duplicates
                if not any(c['url'] == full_url for c in categories):
                    categories.append({'name': name, 'url': full_url})

    if not categories:
        print("No specific categories found, checking homepage...")
        categories.append({'name': 'All', 'url': BASE_URL})
        
    return categories

def process_category(category):
    """Worker function to process a single category."""
    url = category['url']
    cat_name = category['name']
    
    # Simple logging (since threads can interleave output, keep it minimal)
    # print(f"Scanning: {cat_name}") 
    
    soup = fetch_soup(url)
    found_channels = []
    
    if not soup:
        return found_channels
        
    cards = soup.select('.channel-card, .card, .channel')
    if not cards:
        cards = soup.select('a[href*="play.php?id="]')

    for card in cards:
        try:
            link_tag = card if card.name == 'a' else card.find('a')
            if not link_tag: continue
                
            href = link_tag.get('href')
            if 'play.php?id=' not in href: continue
            
            id_str = href.split('id=')[1].split('&')[0]
            
            name_tag = card.find(['h5', 'h6', 'div', 'span'], class_=['card-title', 'channel-name', 'title'])
            name = name_tag.get_text(strip=True) if name_tag else link_tag.get_text(strip=True)
            
            img_tag = card.find('img')
            logo = img_tag['src'] if img_tag else ""
            if logo and not logo.startswith('http'):
                logo = BASE_URL + "/" + logo.lstrip('/')
                
            found_channels.append({
                'id': id_str,
                'name': name,
                'logo': logo,
                'category': cat_name,
                'stream_url': f"{BASE_URL}/api/playlist.php?id={id_str}"
            })
        except:
            continue
            
    return found_channels

def generate_m3u(channels):
    """Generates the M3U content."""
    bd_time = get_bd_time()
    count = len(channels)
    
    header = f"""#EXTM3U
#=================================
# Developed By: OMNIX EMPIER
# IPTV Telegram Channels: https://t.me/omnix_Empire
# Last Updated: {bd_time}
# TV channel counts :- {count}
# Disclaimer:
# This tool does NOT host any content.
# It aggregates publicly available data for informational purposes only.
# For any issues or concerns, please contact the developer.
#==================================

"""
    entries = []
    for ch in channels:
        name = ch['name'].replace(',', ' ')
        cat = ch['category'].replace(',', ' ')
        
        # Construct URL with Pipe syntax for headers (Kodi/IPTV Standard)
        # This often works where EXTVLCOPT fails
        stream_url_with_headers = f'{ch["stream_url"]}|Referer={HEADERS["Referer"]}&User-Agent={HEADERS["User-Agent"]}'
        
        entries.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{name}" tvg-logo="{ch["logo"]}" group-title="{cat}",{name}')
        entries.append(f'#EXTVLCOPT:http-referrer={HEADERS["Referer"]}')
        entries.append(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}')
        entries.append(stream_url_with_headers)
        
    return header + '\n'.join(entries)

def main():
    print("Starting v5on.site scraper with multi-threading...")
    categories = get_categories()
    print(f"Found {len(categories)} categories to scan.")
    
    all_channels = []
    seen_ids = set()
    total_entries_found = 0
    total_duplicates = 0
    
    # Use ThreadPoolExecutor to fetch categories in parallel
    # 20 workers should be fast enough without killing the server
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_cat = {executor.submit(process_category, cat): cat for cat in categories}
        
        for future in concurrent.futures.as_completed(future_to_cat):
            cat = future_to_cat[future]
            try:
                channels = future.result()
                total_entries_found += len(channels)
                
                new_count = 0
                for ch in channels:
                    if ch['id'] not in seen_ids:
                        all_channels.append(ch)
                        seen_ids.add(ch['id'])
                        new_count += 1
                    else:
                        total_duplicates += 1
                
                if new_count > 0:
                    print(f"[{cat['name']}] Found {new_count} new unique channels.")
                # else:
                #     print(f"[{cat['name']}] No new channels (all duplicates).")
            except Exception as e:
                print(f"Error processing {cat['name']}: {e}")

    print(f"Total entries found across categories: {total_entries_found}")
    print(f"Total unique channels (by ID): {len(all_channels)}")
    print(f"Duplicates removed: {total_duplicates}")
    
    # Sort channels to ensure consistent order
    all_channels.sort(key=lambda x: x['name'])
    
    os.makedirs(os.path.dirname(PLAYLIST_FILE), exist_ok=True)
    m3u_content = generate_m3u(all_channels)
    with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
        
    print(f"Playlist saved to {PLAYLIST_FILE}")

if __name__ == "__main__":
    main()
