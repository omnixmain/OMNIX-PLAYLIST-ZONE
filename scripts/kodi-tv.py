import os
import requests
import re
import sys

def get_playlist_urls():
    url = "https://raw.githubusercontent.com/omnixmain/OMNIX-PLAYLIST-ZONE/refs/heads/main/playlists_list.md"
    urls = []
    print(f"Fetching playlist list from: {url}", flush=True)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
        for line in lines:
            # Look for lines like | Name | URL |
            match = re.search(r'\|\s*.*?\s*\|\s*(https?://\S+)\s*\|', line)
            if match:
                urls.append(match.group(1))
    except Exception as e:
        print(f"Error fetching playlist list: {e}", flush=True)
    return urls

def fetch_and_parse_m3u(url):
    entries = []
    print(f"Fetching: {url}", flush=True)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
        
        current_extinf = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#EXTINF:'):
                current_extinf = line
            elif not line.startswith('#'):
                # It's a URL
                if current_extinf:
                    entries.append((current_extinf, line))
                    current_extinf = None
                else:
                    entries.append((f'#EXTINF:-1,Channel', line))

    except Exception as e:
        print(f"Error fetching {url}: {e}", flush=True)
    
    return entries

def save_m3u(entries, output_file):
    seen_urls = set()
    unique_entries = []
    
    for extinf, url in entries:
        if url not in seen_urls:
            unique_entries.append((extinf, url))
            seen_urls.add(url)
            
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for extinf, url in unique_entries:
                f.write(f'{extinf}\n{url}\n')
        print(f"Saved {len(unique_entries)} channels to {output_file}", flush=True)
    except Exception as e:
        print(f"Error writing to {output_file}: {e}", flush=True)

def main():
    print("Script started...", flush=True)
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(scripts_dir)
    
    output_file = os.path.join(repo_root, 'playlist', 'kodi-tv.m3u')
    
    urls = get_playlist_urls()
    print(f"Found {len(urls)} playlists.", flush=True)
    
    all_channels = []
    
    # Use ThreadPoolExecutor to fetch playlists concurrently
    # Adjust max_workers as needed, 10 is usually a safe starting point for IO-bound tasks
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_url = {executor.submit(fetch_and_parse_m3u, url): url for url in urls}
        
        # Process results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
            url = future_to_url[future]
            try:
                channels = future.result()
                all_channels.extend(channels)
                print(f"Completed {i+1}/{len(urls)}: {url} ({len(channels)} channels)", flush=True)
            except Exception as e:
                print(f"Excpetion fetching {url}: {e}", flush=True)
        
    print(f"Total channels found (before dedupe): {len(all_channels)}", flush=True)
    save_m3u(all_channels, output_file)
    print("Script finished.", flush=True)

if __name__ == "__main__":
    main()
