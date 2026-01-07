import os
import re
import datetime
import urllib.parse
import json

PLAYLIST_DIR = "playlist"

def get_expiry_from_url(url):
    # Regex to find expiry timestamps (keys like e, exp, expires, etc.)
    # Looks for key=timestamp where timestamp is 10+ digits
    # Matches: e=123.., exp=123.., expires=123..
    # Relaxed to find it anywhere in the string
    
    match = re.search(r'\b(e|exp|expires|expiry|vk_expire)=(\d{10,})', url, re.IGNORECASE)
    
    if match:
        key = match.group(1)
        expiry_ts = int(match.group(2))
        
        # Milliseconds check
        if expiry_ts > 9999999999: 
             expiry_ts = expiry_ts / 1000
             
        dt = datetime.datetime.fromtimestamp(expiry_ts)
        now = datetime.datetime.now()
        diff = dt - now
        
        minutes_left = diff.total_seconds() / 60
        return {
            "type": "timestamp_param",
            "key": key,
            "expiry_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "minutes_left": f"{minutes_left:.2f}"
        }
    
    # Check for token without explicit expiry key (heuristic)
    if "token=" in url or "u=" in url or "hdnea=" in url:
         return {
            "type": "token_present",
            "key": "token",
            "expiry_time": "Unknown (Encoded)",
            "minutes_left": "Unknown"
         }

    return None

def analyze_file(filename):
    path = os.path.join(PLAYLIST_DIR, filename)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    urls = [line.strip() for line in lines if line.strip().startswith('http')]
    
    if not urls:
        print(f"[{filename}] No URLs found.")
        return

    # Check first 5 URLs to see if they share a pattern
    print(f"--- Analyzing {filename} ({len(urls)} channels) ---")
    
    # We only analyze a sample to avoid spam, but we want to see if they are consistent.
    sample_urls = urls[:3] 
    
    found_any = False
    for i, url in enumerate(sample_urls):
        res = get_expiry_from_url(url)
        if res:
            found_any = True
            print(f"  URL {i+1}: Found expiry param '{res['key']}'")
            print(f"    Expires: {res['expiry_time']}")
            print(f"    Time remaining: {res['minutes_left']} minutes")
        else:
            # Check for JWT-like tokens
            if "token=" in url or "u=" in url:
                 print(f"  URL {i+1}: Contains token/auth params but explicit expiry timestamp not identified in standard keys.")
            else:
                 print(f"  URL {i+1}: No obvious expiry parameters found.")
    
    if not found_any:
        print(f"  => Could not determine explicit expiration for {filename} from URL parameters.")
    print("")

def main():
    if not os.path.exists(PLAYLIST_DIR):
        print("Playlist directory not found.")
        return
        
    for filename in os.listdir(PLAYLIST_DIR):
        if filename.endswith(".m3u") or filename.endswith(".m3u8"):
            analyze_file(filename)

if __name__ == "__main__":
    main()
