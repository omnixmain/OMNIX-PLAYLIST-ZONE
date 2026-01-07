import requests
import re
import time
import sys
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket



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
    Worker function to process a single channel using curl.
    args is a tuple: (base_url, url, name, logo_url)
    """
    base_url, url, name, logo_url = args
    full_url = urljoin(base_url, url)
    
    try:
        curl_cmd = 'curl.exe' if sys.platform == 'win32' else 'curl'
        # Reduced timeout for individual channels
        result = subprocess.run(
            [curl_cmd, '-s', '-L', '--retry', '2', '-H', 'User-Agent: Mozilla/5.0', '--max-time', '15', full_url],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode != 0:
            # log(f"[{name}] Failed curl: {result.returncode}") # optional debug
            return None
        
        play_resp_text = result.stdout
        
        # Extract video source
        match = re.search(VIDEO_SRC_PATTERN, play_resp_text)
        if match:
            video_src = match.group(1)
            return {
                "name": name,
                "logo": logo_url,
                "url": video_src
            }
        # else:
            # log(f"[{name}] Failed: No video src.") 
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
    
    session = requests.Session()
    session.headers.update(headers)
    
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    
    import subprocess
    try:
        # Use curl to fetch the main page
        curl_cmd = 'curl.exe' if sys.platform == 'win32' else 'curl'
        result = subprocess.run(
            [curl_cmd, '-s', '-L', '--retry', '3', '-H', 'User-Agent: Mozilla/5.0', BASE_URL],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore' # ignore encoding errors
        )
        if result.returncode != 0:
            log(f"Failed to fetch main page with curl. RC: {result.returncode}, Stderr: {result.stderr}, Stdout: {result.stdout}")
            return
        response_text = result.stdout
    except Exception as e:
        log(f"Failed to run curl: {e}")
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
    
    
    work_items = []
    for url, name, logo in channels_to_process:
        work_items.append((BASE_URL, url, name, logo))
        
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

