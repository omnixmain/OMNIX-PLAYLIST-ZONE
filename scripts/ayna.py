import requests
import re
import time
import sys
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
try:
    import urllib3.util.connection as urllib3_cn
except ImportError:
    import requests.packages.urllib3.util.connection as urllib3_cn

def allowed_gai_family():
    return socket.AF_INET

urllib3_cn.allowed_gai_family = allowed_gai_family

BASE_URL = "http://xown.site/web/ayna"
# Match href that contains play.php
LINK_PATTERN = r'<a[^>]+href=["\']([^"\']*play\.php\?id=[^"\']+)["\'][^>]*>(.*?)</a>'
VIDEO_SRC_PATTERN = r'var\s+videoSrc\s*=\s*"([^"]+)"'
LOGO_PATTERN = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'

def log(msg):
    print(msg)
    sys.stdout.flush()

def process_channel(args):
    """
    Worker function to process a single channel.
    args is a tuple: (session, base_url, url, name, logo_url)
    """
    session, base_url, url, name, logo_url = args
    full_url = urljoin(base_url, url)
    
    try:
        # Response time might be slow, giving it 15s
        play_resp = session.get(full_url, timeout=15)
        
        if play_resp.status_code != 200:
            return None
        
        # Extract video source
        match = re.search(VIDEO_SRC_PATTERN, play_resp.text)
        if match:
            video_src = match.group(1)
            return {
                "name": name,
                "logo": logo_url,
                "url": video_src
            }
    except Exception as e:
        log(f"Error processing {name}: {e}")
        pass
    
    return None

def main():
    log(f"Fetching channel list from {BASE_URL}...")
    headers = {
        'User-Agent': 'curl/8.16.0',
        'Accept': '*/*, text/html',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'identity',
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    
    try:
        response = session.get(BASE_URL, timeout=30)
        response.raise_for_status()
    except Exception as e:
        log(f"Failed to fetch main page: {e}")
        return

    # Find all channel links and names
    raw_matches = re.findall(LINK_PATTERN, response.text, re.IGNORECASE | re.DOTALL)
    
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

        # Clean Name
        clean_name = re.sub(r'<[^>]+>', '', name_html).strip()
        full_url = urljoin(BASE_URL, url)
        
        if full_url not in seen_urls:
            channels_to_process.append((full_url, clean_name, logo_url))
            seen_urls.add(full_url)
    
    log(f"Processing {len(channels_to_process)} unique channels with threading...")

    if not channels_to_process:
        log("DEBUG: No channels found. Response content start:")
        log(response.text[:500])
        return
    
    m3u_content = ["#EXTM3U"]
    
    # Use a session for connection pooling
    session = requests.Session()
    session.headers.update(headers)
    
    # Prepare arguments for worker
    # We pass the session (Session is not thread-safe if we were making concurrent requests *with the same session object* potentially,
    # but here we are just reading. Actually requests.Session IS thread-safe.
    # However, creating a new session per thread or one global session is fine.
    # For simplicity and performance, one shared session is usually okay.
    
    work_items = []
    for url, name, logo in channels_to_process:
        # We pass relative url here because process_channel does urljoin, but wait, we already did urljoin above.
        # Let's clean up. The process_channel takes 'url', let's pass the already full url.
        # Actually my process_channel expects (session, base_url, url, ...) and does join.
        # But `channels_to_process` has `full_url`. 
        # I will adjust the args passed.
        work_items.append((session, BASE_URL, url, name, logo))
        
    # We need to change process_channel to accept full_url or handle it. 
    # Since I can't restart the edit without cancelling, I'll rely on my instruction to Rewrite implementation.
    # Wait, the ReplacementContent is what I am searching for. I need to make sure the ReplacementContent is correct.
    # In my ReplacementContent above:
    # process_channel takes args=(session, base_url, url, name, logo_url)
    # and does full_url = urljoin(base_url, url)
    # in the loop: channels_to_process has FULL URLs. 
    # So urljoin(BASE_URL, full_url) will still be full_url. This is fine.
    
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
        m3u_content.append(f'#EXTINF:-1 group-title="Ayna TV"{logo_attr},{item["name"]}')
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

