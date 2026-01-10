import requests
import os
import datetime

def fetch_and_filter_m3u():
    # URL to fetch the M3U data
    url = "http://esproookttm.top:8080/get.php?username=es6561755618020302&password=d83304ab7c56&type=m3u_plus&output=ts"
    
    # Determine the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go one level up to find the playlist directory (assuming scripts/ is a sibling of playlist/)
    project_root = os.path.dirname(script_dir)
    playlist_dir = os.path.join(project_root, "playlist")
    
    # Ensure playlist directory exists
    os.makedirs(playlist_dir, exist_ok=True)
    
    output_file = os.path.join(playlist_dir, "dreamtv.m3u")
    
    print(f"Fetching data from: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        filtered_lines = []
        
        print(f"Downloaded {len(lines)} lines. Parsing...")
        
        i = 0
        channel_count = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("#EXTINF"):
                extinf_line = line
                # Look for the URL in following lines
                j = i + 1
                url_line = None
                
                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith("#"):
                        url_line = next_line
                        break
                    elif next_line.startswith("#EXTINF"):
                        # Found another channel marker before a URL, abort previous
                        break
                    j += 1
                
                # If we found a URL, add both lines
                if url_line:
                    filtered_lines.append(extinf_line)
                    filtered_lines.append(url_line)
                    channel_count += 1
                    i = j # Move index to the URL line, loop will increment to next
                else:
                    i += 1
            else:
                i += 1
                
                i += 1
        
        # Calculate BD Time (UTC + 6)
        utc_now = datetime.datetime.utcnow()
        bd_time = utc_now + datetime.timedelta(hours=6)
        formatted_time = bd_time.strftime("%Y-%m-%d %I:%M %p")

        m3u_header = f"""#EXTM3U
#=================================
# Developed By: OMNIX EMPIER
# IPTV Telegram Channels: https://t.me/omnix_Empire
# Last Updated: {formatted_time} (BD Time)
# TV channel counts :- {channel_count}
# Disclaimer:
# This tool does NOT host any content.
# It aggregates publicly available data for informational purposes only.
# For any issues or concerns, please contact the developer.
#==================================  
"""
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u_header)
            f.write("\n".join(filtered_lines))
            
        print(f"Successfully created: {output_file}")
        print(f"Total Live TV channels extracted: {channel_count}")
        
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching M3U: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_and_filter_m3u()
