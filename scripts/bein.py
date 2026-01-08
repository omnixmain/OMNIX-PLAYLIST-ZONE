import os

def filter_bein_channels():
    input_file = os.path.join("playlist", "dreamtv.m3u")
    output_file = os.path.join("playlist", "BEIN.m3u")
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        filtered_lines = ["#EXTM3U\n"]
        
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
                        filtered_lines.append(extinf_line)
                        filtered_lines.append(url_line)
                        i = j # Advance
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
                
        with open(output_file, "w", encoding="utf-8") as f:
            f.writelines(filtered_lines)
            
        print(f"Successfully created {output_file} with {len(filtered_lines)//2} channels.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    filter_bein_channels()
