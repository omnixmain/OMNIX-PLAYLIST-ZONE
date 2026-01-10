import requests
import os
import datetime
import re

def fetch_and_filter_adult_m3u():
    # URL to fetch the M3U data
    url = "http://esproookttm.top:8080/get.php?username=es6561755618020302&password=d83304ab7c56&type=m3u_plus&output=ts"
    
    # Setup directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    playlist_dir = os.path.join(project_root, "playlist")
    os.makedirs(playlist_dir, exist_ok=True)
    
    output_file = os.path.join(playlist_dir, "adultporn.m3u")
    
    print(f"Fetching data from: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        print(f"Downloaded {len(lines)} lines. Parsing and filtering for ADULT content...")
        
        # Keywords to identify adult channels
        xxx_keywords = ["XXX", "ADULT", "PORN", "18+"]
        
        channels = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                extinf_line = line
                # Look for URL
                j = i + 1
                url_line = None
                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith("#"):
                        url_line = next_line
                        break
                    elif next_line.startswith("#EXTINF"):
                        break
                    j += 1
                
                if url_line:
                    # Check matching keywords in the EXTINF line
                    # Usually "group-title="XXX 18+"" or name "XXX: ..."
                    is_adult = False
                    upper_line = extinf_line.upper()
                    
                    if any(k in upper_line for k in xxx_keywords):
                        is_adult = True
                    
                    # Also check specific group-title extraction if regex needed, but simple string search usually works
                    # Let's extract group-title to be sure
                    # ...
                    
                    if is_adult:
                        channels.append((extinf_line, url_line))
                    
                    i = j
                else:
                    i += 1
            else:
                i += 1
        
        # Calculate time
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        bd_time = utc_now + datetime.timedelta(hours=6)
        current_time = bd_time.strftime("%Y-%m-%d %I:%M %p")
        
        # Write Output
        with open(output_file, "w", encoding="utf-8") as f:
            f.write('#EXTM3U\n')
            f.write('#=================================\n')
            f.write('# Developed By: OMNIX EMPIER\n')
            f.write('# IPTV Telegram Channels: https://t.me/omnix_Empire\n')
            f.write(f'# Last Updated: {current_time} (BD Time)\n')
            f.write(f'# TV channel counts :- {len(channels)}\n')
            f.write('# Disclaimer:\n')
            f.write('# This tool does NOT host any content.\n')
            f.write('# It aggregates publicly available data for informational purposes only.\n')
            f.write('# For any issues or concerns, please contact the developer.\n')
            f.write('#==================================  \n')
            
            for extinf, stream_url in channels:
                f.write(f"{extinf}\n")
                f.write(f"{stream_url}\n")
                
        print(f"Successfully created: {output_file}")
        print(f"Total Adult channels extracted: {len(channels)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_filter_adult_m3u()
