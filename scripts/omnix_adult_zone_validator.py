import requests
import concurrent.futures
import os
import time

def check_stream(line):
    url = line.strip()
    if not url.startswith('http'):
        return None
        
    try:
        # Stream check with headers to mimic a browser/player
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Use HEAD request for speed, but some servers reject HEAD, so fallback to GET with stream=True
        try:
            response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                return url
        except:
            # Fallback to a very short GET
            response = requests.get(url, headers=headers, stream=True, timeout=5)
            if response.status_code == 200:
                response.close()
                return url
    except:
        pass
    return None

def validate_m3u():
    # Setup paths relative to script location
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    playlist_dir = os.path.join(base_dir, 'playlist')
    os.makedirs(playlist_dir, exist_ok=True)

    input_file = os.path.join(playlist_dir, "omnix_adult_zone.m3u")
    output_file = os.path.join(playlist_dir, "omnix_adult_zone_active.m3u")
    
    if not os.path.exists(input_file):
        print(f"{input_file} not found!")
        return

    print("Reading M3U file...")
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    current_entry = []
    
    for line in lines:
        if line.startswith('#EXTINF'):
            if current_entry:
                entries.append(current_entry)
            current_entry = [line]
        elif line.strip() and not line.startswith('#'):
            if current_entry:
                current_entry.append(line)
                entries.append(current_entry)
                current_entry = []
        elif current_entry:
            current_entry.append(line)
            
    # Add the last entry
    if current_entry:
        entries.append(current_entry)

    print(f"Found {len(entries)} entries. Checking validity...")

    active_entries = []
    
    # Process in chunks to avoid overwhelming local network or CPU if list is huge
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_entry = {executor.submit(check_stream, entry[-1].strip()): entry for entry in entries}
        
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            try:
                result = future.result()
                if result:
                    active_entries.append(entry)
                    # Optional: Print progress
            except Exception:
                pass

    print(f"Found {len(active_entries)} active streams out of {len(entries)}.")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for entry in active_entries:
            for line in entry:
                f.write(line)

    print(f"Saved active playlist to {output_file}")

if __name__ == "__main__":
    validate_m3u()
