import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import os

# Configuration
BASE_URL = "https://v5on.site"
PLAYLIST_FILE = "playlist/omni_v5on.m3u"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://v5on.site/",
}

def get_bd_time():
    """Returns the current time in Bangladesh timezone."""
    bd_tz = pytz.timezone('Asia/Dhaka')
    now = datetime.datetime.now(bd_tz)
    return now.strftime("%Y-%m-%d %I:%M %p (BD Time)")

def fetch_soup(url):
    """Fetches a URL and returns a BeautifulSoup object."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
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
        # Adjust selector based on actual site structure
        # Looking for links with ?cat=
        # This is a general approach based on typical structures found in previous step
        nav_buttons = soup.find_all('button', class_='nav-link') # Common BS5 class or based on investigation
        
        # Fallback: look for any link with ?cat=
        if not categories:
             links = soup.find_all('a', href=True)
             for link in links:
                 href = link['href']
                 if '?cat=' in href:
                     name = link.get_text(strip=True)
                     if name and name not in [c['name'] for c in categories]:
                         categories.append({'name': name, 'url': BASE_URL + "/" + href if not href.startswith('http') else href})
    
    # If no categories found, maybe the home page IS the list or has a different structure
    # We will assume at least one default category or the home page itself has channels
    if not categories:
        print("No categories found, checking homepage for channels directly...")
        categories.append({'name': 'Uncategorized', 'url': BASE_URL})
        
    return categories

def get_channels_from_page(url, category_name):
    """Scrapes channels from a specific page."""
    soup = fetch_soup(url)
    channels = []
    if not soup:
        return channels
        
    # Selector for channel cards based on typical bootstrap/grid layouts
    # Previous investigation hinted at .channel-card
    cards = soup.select('.channel-card, .card, .channel')
    
    # If using generic links if cards not found
    if not cards:
        cards = soup.select('a[href*="play.php?id="]')

    for card in cards:
        try:
            # Try to find the link first
            link_tag = card if card.name == 'a' else card.find('a')
            if not link_tag:
                continue
                
            href = link_tag.get('href')
            if 'play.php?id=' not in href:
                continue
            
            # Extract ID
            id_str = href.split('id=')[1].split('&')[0]
            
            # Extract Name
            name_tag = card.find(['h5', 'h6', 'div', 'span'], class_=['card-title', 'channel-name', 'title'])
            name = name_tag.get_text(strip=True) if name_tag else link_tag.get_text(strip=True)
            
            # Extract Logo
            img_tag = card.find('img')
            logo = img_tag['src'] if img_tag else ""
            if logo and not logo.startswith('http'):
                logo = BASE_URL + "/" + logo.lstrip('/')
                
            channels.append({
                'id': id_str,
                'name': name,
                'logo': logo,
                'category': category_name,
                'stream_url': f"{BASE_URL}/api/playlist.php?id={id_str}"
            })
        except Exception as e:
            continue
            
    return channels

def generate_m3u(channels):
    """Generates the M3U content with the custom header."""
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
    
    entries = ""
    for ch in channels:
        # Sanitize data
        name = ch['name'].replace(',', ' ')
        cat = ch['category'].replace(',', ' ')
        
        entries += f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{name}" tvg-logo="{ch["logo"]}" group-title="{cat}",{name}\n'
        entries += f'{ch["stream_url"]}\n'
        
    return header + entries

def main():
    print("Starting v5on.site scraper...")
    categories = get_categories()
    print(f"Found {len(categories)} categories.")
    
    all_channels = []
    seen_ids = set()
    
    for cat in categories:
        print(f"Scraping category: {cat['name']}")
        channels = get_channels_from_page(cat['url'], cat['name'])
        
        new_channels = 0
        for ch in channels:
            if ch['id'] not in seen_ids:
                all_channels.append(ch)
                seen_ids.add(ch['id'])
                new_channels += 1
        print(f"  Found {new_channels} new channels.")
        
    print(f"Total unique channels found: {len(all_channels)}")
    
    # Create output directory
    os.makedirs(os.path.dirname(PLAYLIST_FILE), exist_ok=True)
    
    # Generate and save M3U
    m3u_content = generate_m3u(all_channels)
    with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
        
    print(f"Playlist saved to {PLAYLIST_FILE}")

if __name__ == "__main__":
    main()
