import os
import datetime
import requests

def filter_bein_channels():
    m3u_url = "https://raw.githubusercontent.com/omnixmain/OMNIX-PLAYLIST-ZONE/refs/heads/main/playlist/omni_v5on.m3u"
    output_file = os.path.join("playlist", "BEIN.m3u")
    
    try:
        response = requests.get(m3u_url)
        response.raise_for_status() # Check for HTTP errors
        lines = response.text.splitlines()
            
        filtered_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                extinf_line = lines[i] # Keep original with newline
                # Check for "BEIN" in the EXTINF line (case-insensitive)
                if "BEIN" in line.upper():
                    # Look for the URL
                    j = i + 1
                    url_line = None
                    while j < len(lines):
                        temp_line = lines[j].strip()
                        if temp_line and not temp_line.startswith("#"):
                            url_line = lines[j] # Keep original with newline
                            break
                        if temp_line.startswith("#EXTINF"):
                            break
                        j += 1
                    
                    if url_line:
                        filtered_lines.append(extinf_line + "\n") # Ensure newline
                        filtered_lines.append(url_line + "\n") # Ensure newline
                        i = j # Advance
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        
        # Calculate BD Time (UTC + 6)
        utc_now = datetime.datetime.utcnow()
        bd_time = utc_now + datetime.timedelta(hours=6)
        formatted_time = bd_time.strftime("%Y-%m-%d %I:%M %p")
        
        count = len(filtered_lines) // 2

        m3u_header = f"""#EXTM3U
#=================================
# Developed By: OMNIX EMPIER
# IPTV Telegram Channels: https://t.me/omnix_Empire
# Last Updated: {formatted_time} (BD Time)
# TV channel counts :- {count}
# Disclaimer:
# This tool does NOT host any content.
# It aggregates publicly available data for informational purposes only.
# For any issues or concerns, please contact the developer.
#==================================  
"""
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u_header)
            f.writelines(filtered_lines)
            
        print(f"Successfully created {output_file} with {len(filtered_lines)//2} channels.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    filter_bein_channels()
