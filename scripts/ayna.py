import requests
try:
    from curl_cffi import requests as crequests
except ImportError:
    print("curl_cffi not found, falling back to requests (may fail)")
    crequests = requests

import re
import time
import sys
import base64
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket



BASE_URL = "https://n.shopnojaal.top/ayna/"
# Match href that contains play.php
LINK_PATTERN = r'<a[^>]+href=["\']([^"\']*play\.php\?id=[^"\']+)["\'][^>]*>(.*?)</a>'
VIDEO_SRC_PATTERN = r'var\s+streamUrl\s*=\s*atob\("([^"]+)"\)'
# Non-greedy match for src to avoid skipping to onerror
LOGO_PATTERN = r'<img[^>]*?\bsrc=["\']([^"\']+)["\']'
CATEGORY_PATTERN = r'<span[^>]*class=["\']channel-category["\'][^>]*>(.*?)</span>'

def log(msg):
    print(msg)
    sys.stdout.flush()

def process_channel(args):
    """
    Worker function to process a single channel using curl_cffi.
    args is a tuple: (base_url, url, name, logo_url, category)
    """
    base_url, url, name, logo_url, category = args
    full_url = urljoin(base_url, url)
    
    try:
        # Use simple get with retry logic if possible or just timeout
        # impersonate="chrome" handles the TLS fingerprint
        play_resp = crequests.get(full_url, impersonate="chrome", timeout=15)
        
        if play_resp.status_code != 200:
            # log(f"[{name}] Failed: Status {play_resp.status_code}")
            return None
        
        play_resp_text = play_resp.text
        
        # Extract video source
        match = re.search(VIDEO_SRC_PATTERN, play_resp_text)
        if match:
            b64_src = match.group(1)
            try:
                # Decode Base64
                video_src = base64.b64decode(b64_src).decode('utf-8')
                return {
                    "name": name,
                    "logo": logo_url,
                    "group": category,
                    "url": video_src
                }
            except Exception as e:
                log(f"[{name}] Failed to decode base64: {e}") 
    except Exception as e:
        log(f"Error processing {name}: {e}")
        pass
    
    return None

def main():
    log(f"Fetching channel list from {BASE_URL}...")
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': '*/*',
        'Connection': 'keep-alive',
    }
    
    # Use curl_cffi for main page too
    try:
        response = crequests.get(BASE_URL, impersonate="chrome", timeout=30)
        if response.status_code != 200:
            log(f"Failed to fetch main page: Status {response.status_code}")
            return
        response_text = response.text
    except Exception as e:
        log(f"Failed to fetch main page: {e}")
        return

    # Find all channel links and names
    raw_matches = re.findall(LINK_PATTERN, response_text, re.IGNORECASE | re.DOTALL)
    
    channels_to_process = []
    seen_urls = set()
    
    log(f"Found {len(raw_matches)} raw matches. Parsing...")

    for url, name_html in raw_matches:
        # Extract Logo
        logo_url = ""
        logo_match = re.search(LOGO_PATTERN, name_html, re.IGNORECASE)
        if logo_match:
            raw_logo = logo_match.group(1)
            logo_url = urljoin(BASE_URL, raw_logo)

        # Extract Category
        category = "Ayna TV" # Default
        cat_match = re.search(CATEGORY_PATTERN, name_html, re.IGNORECASE)
        if cat_match:
            category = cat_match.group(1).strip()

        # Clean Name
        name_match = re.search(r'<h6[^>]*class=["\']channel-name["\'][^>]*>(.*?)</h6>', name_html, re.IGNORECASE)
        if name_match:
            clean_name = name_match.group(1).strip()
        else:
            clean_name = re.sub(r'<[^>]+>', '', name_html).strip() # Fallback
        
        clean_name = re.sub(r'\s+', ' ', clean_name)
        full_url = urljoin(BASE_URL, url)
        
        if full_url not in seen_urls:
            channels_to_process.append((full_url, clean_name, logo_url, category))
            seen_urls.add(full_url)
    
    log(f"Processing {len(channels_to_process)} unique channels with threading...")

    if not channels_to_process:
        log("DEBUG: No channels found. Response content start:")
        log(response.text[:500])
        return
    
    m3u_content = ["#EXTM3U"]
    
    
    work_items = []
    for url, name, logo, category in channels_to_process:
        work_items.append((BASE_URL, url, name, logo, category))
        
    results = []
    completed_count = 0
    total = len(work_items)

    # Using 5 threads as per plan to avoid blocking/captcha
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_channel = {executor.submit(process_channel, item): item for item in work_items}
        
        for future in as_completed(future_to_channel):
            completed_count += 1
            res = future.result()
            if res:
                log(f"[{completed_count}/{total}] Found: {res['name']}")
                # Append immediately or collect? Collecting is safer for ordering if needed, but M3U order doesn't matter much.
                # Let's collect.
                results.append(res)
            else:
                log(f"[{completed_count}/{total}] Failed/No Stream")

    # Generate M3U
    for item in results:
        logo_attr = f' tvg-logo="{item["logo"]}"' if item["logo"] else ""
        group = item.get("group", "Ayna TV")
        m3u_content.append(f'#EXTINF:-1 group-title="{group}"{logo_attr},{item["name"]}')
        m3u_content.append(item["url"])

    import os
    output_dir = "playlist"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(output_dir, "ayna.m3u")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content))
    
    log(f"Saved playlist to {output_file} with {len(results)} channels.")

if __name__ == "__main__":
    main()

