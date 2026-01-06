import aiohttp
import asyncio
import os
import time
from tqdm.asyncio import tqdm

# Semaphore to control concurrency (adjust as needed based on network/CPU)
CONCURRENCY_LIMIT = 50

async def check_stream(session, line, semaphore):
    url = line.strip()
    if not url.startswith('http'):
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    async with semaphore:
        try:
            # Try HEAD request first for speed
            try:
                async with session.head(url, headers=headers, timeout=5, allow_redirects=True) as response:
                    if response.status == 200:
                        return url
            except (aiohttp.ClientError, asyncio.TimeoutError):
                # Fallback to GET with stream=True equivalent (just reading headers/start)
                # In aiohttp, we just do the request and close it.
                pass

            # Fallback to GET
            async with session.get(url, headers=headers, timeout=5) as response:
                if response.status == 200:
                    return url
        except (aiohttp.ClientError, asyncio.TimeoutError, Exception):
            pass
        return None

async def validate_m3u_async():
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
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    # helper to check entry and return it if valid
    async def check_entry(session, entry, semaphore):
        url = entry[-1].strip()
        res = await check_stream(session, url, semaphore)
        return entry if res else None

    async with aiohttp.ClientSession() as session:
        tasks = [check_entry(session, entry, semaphore) for entry in entries]
        
        valid_entries = []
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Validating Streams", unit="stream"):
            result = await f
            if result:
                valid_entries.append(result)

    print(f"Found {len(valid_entries)} active streams out of {len(entries)}.")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        # To maintain original order, strict concurrency might scramble it.
        # But usually playlist order doesn't matter as much as validity.
        # If order matters, we'd need to await all and index them.
        # For now, we append as they finish (or just collected list). 
        # Actually standard asyncio.gather maintains order if we used that, but as_completed does not.
        # Let's just write what we found.
        for entry in valid_entries:
            for line in entry:
                f.write(line)

    print(f"Saved active playlist to {output_file}")

def main():
    asyncio.run(validate_m3u_async())

if __name__ == "__main__":
    main()
