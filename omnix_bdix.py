import requests
import os

def fetch_and_clean_playlist():
    url = "https://sportsbd.top/playlist/playlist.m3u?id=25feb0d3bbaa"
    output_dir = "playlist"
    output_file = os.path.join(output_dir, "omnix_bdix.m3u")
    
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Fetching playlist from {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        print(f"Error fetching playlist: {e}")
        return

    lines = content.splitlines()
    m3u_lines = []
    
    # Find start of M3U content (handling potential HTML prefix)
    start_index = 0
    found_start = False
    for i, line in enumerate(lines):
        if '#EXTM3U' in line:
            parts = line.split('#EXTM3U')
            if len(parts) > 1:
                # If #EXTM3U is in the middle of a line, use the part from #EXTM3U onwards
                # But actually, we usually want the header on its own line for the new file.
                # So we just start processing from here.
                # We will manually add #EXTM3U as the first line of our output.
                pass 
            start_index = i
            found_start = True
            break
            
    if not found_start:
        print("Warning: #EXTM3U tag not found. Processing entire file usually.")
        start_index = 0

    # Start constructing cleaned playlist
    cleaned_lines = ["#EXTM3U"]
    
    # Process lines from the detected start
    # If we found split content on the start line, we might need to handle it, 
    # but usually the M3U content follows directives.
    # Let's re-read lines starting from start_index, but ignore the actual line content of start_index if it was mixed with HTML
    # unless it contained valid M3U directives after the tag.
    # Simpler approach: Iterate from start_index, filtering strict logic.

    raw_lines = lines[start_index:]
    
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check for Telegram/HTML junk
        if "t.me/" in line or "group-title=\"JOIN TELEGRAM\"" in line or "<!DOCTYPE" in line or "<html" in line:
            i += 1
            continue

        if line.startswith("#EXTINF"):
            # Check if this EXTINF line has bad keywords
            if "JOIN TELEGRAM" in line or "t.me" in line:
                # Skip this line and likely the next URL line
                i += 2 
                continue
            
            # Look ahead for the URL
            if i + 1 < len(raw_lines):
                next_line = raw_lines[i+1].strip()
                if "t.me" in next_line or "telegram.me" in next_line:
                    # Skip both
                    i += 2
                    continue
                else:
                    # Valid channel
                    cleaned_lines.append(line)
                    cleaned_lines.append(next_line)
                    i += 2
            else:
                # End of file after EXTINF?
                i += 1
        elif line.startswith("#"):
            # Other directives
            if "#EXTM3U" not in line: # Already added header
                cleaned_lines.append(line)
            i += 1
        else:
            # Standalone URL or other text? 
            # If we are strictly processing EXTINF pairs, this might be orphaned URL
            # But let's keep it if it looks like a URL and wasn't skipped above
            if line.startswith("http") and "t.me" not in line:
                 cleaned_lines.append(line)
            i += 1

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_lines))
    
    print(f"Cleaned playlist saved to {output_file}")

if __name__ == "__main__":
    fetch_and_clean_playlist()
