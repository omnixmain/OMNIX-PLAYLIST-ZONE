import requests
import re
import os
import datetime
import urllib.parse

def fetch_and_generate_m3u():
    url = "https://crichd2h.xfireflixbd.workers.dev/"
    
    # Determine the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    playlist_dir = os.path.join(project_root, "playlist")
    
    # Ensure playlist directory exists
    os.makedirs(playlist_dir, exist_ok=True)
    output_file = os.path.join(playlist_dir, "crichd2h.m3u")
    
    print(f"Fetching data from: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        print(f"Downloaded content. Parsing...")
        
        # robust parsing by splitting the content by class="card"
        # each chunk (except the first) will verify the beginning of a card
        chunks = html_content.split('class="card"')
        
        channels = []
        
        # skip the first chunk as it is before the first card
        for chunk in chunks[1:]:
            # structure check - ensure it has data-name in the first few characters
            # usually: data-id=".." data-name=".." data-cat=".."
            
            # Extract Name
            name_match = re.search(r'data-name="([^"]+)"', chunk)
            
            # Extract Category
            cat_match = re.search(r'data-cat="([^"]+)"', chunk)
            
            # Extract Logo
            # Look for img src within this chunk
            logo_match = re.search(r'<img src="([^"]+)"', chunk)
            
            # Extract Stream URL
            # Look for <a class="btn" href="...">
            link_match = re.search(r'href="([^"]+)"', chunk)
            
            if name_match and link_match:
                name = name_match.group(1)
                group = cat_match.group(1) if cat_match else "Uncategorized"
                stream_url = link_match.group(1)
                
                logo = ""
                if logo_match:
                    raw_src = logo_match.group(1)
                    if "u=" in raw_src:
                        try:
                            encoded_part = raw_src.split("u=", 1)[1]
                            # Sometimes it might be double encoded or just need unquote
                            logo = urllib.parse.unquote(encoded_part)
                        except:
                            logo = raw_src
                    else:
                        logo = raw_src

                # validation: ensure stream_url is actually a url
                if "http" in stream_url:
                    channels.append({
                        "name": name,
                        "group": group,
                        "logo": logo,
                        "url": stream_url
                    })
        
        channel_count = len(channels)
        
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
            for channel in channels:
                # Sanitize name for tvg-id if needed or just use name
                line1 = f'#EXTINF:-1 tvg-id="{channel["name"]}" tvg-name="{channel["name"]}" tvg-logo="{channel["logo"]}" group-title="{channel["group"]}",{channel["name"]}'
                line2 = channel["url"]
                f.write(line1 + "\n")
                f.write(line2 + "\n")
            
        print(f"Successfully created: {output_file}")
        print(f"Total Live TV channels extracted: {channel_count}")
        
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching content: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_and_generate_m3u()
