import requests
import os

def fetch_and_filter_m3u():
    url = "http://dreamtv22.info:25461/get.php?username=319006301129&password=417198287244&type=m3u_plus"
    output_file = os.path.join("playlist", "dreamtv.m3u")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        filtered_lines = ["#EXTM3U"]
        
        # Simple parser: check pairs of lines (or chunks)
        # Usually #EXTINF is followed by URL
        
        # We process line by line. If we find #EXTINF, we hold it. 
        # If the next non-empty/non-comment line is a URL ending in .ts, we keep both.
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                extinf_line = line
                # Look ahead for URL
                j = i + 1
                url_line = None
                while j < len(lines):
                    temp_line = lines[j].strip()
                    if temp_line and not temp_line.startswith("#"):
                        url_line = temp_line
                        break
                    if temp_line.startswith("#EXTINF"): # Found another EXTINF before URL, abort previous
                        break
                    j += 1
                
                if url_line and url_line.endswith(".ts"):
                    filtered_lines.append(extinf_line)
                    filtered_lines.append(url_line)
                    i = j # Advance to the line after URL
                else:
                    i += 1
            else:
                i += 1
                
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(filtered_lines))
            
        print(f"Successfully created {output_file} with {len(filtered_lines)//2} channels.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_filter_m3u()
