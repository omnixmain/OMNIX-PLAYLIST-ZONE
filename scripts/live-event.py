import requests
import json
import datetime
import os

# Source URLs
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/refs/heads/main/data/fancode.json"
JIOHOTSTAR_URL = ""
SONYLIV_URL = "https://raw.githubusercontent.com/drmlive/sliv-live-events/main/sonyliv.json"

# Output Files
JSON_OUTPUT = "playlist/live-event.json"
M3U_OUTPUT = "playlist/live-event.m3u"

def fetch_data(url, label):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {label}: {e}")
        return None

def normalize_sonyliv(item):
    """Maps SonyLIV item to Fancode schema"""
    try:
        match_id = item.get("contentId", "")
        title = item.get("match_name") or item.get("event_name", "Unknown Event")
        is_live = item.get("isLive", False)
        status = "LIVE" if is_live else "COMPLETED"
        image = item.get("src", "")
        video_url = item.get("video_url", "")
        
        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "image": image,
            "STREAMING_CDN": {
                "Primary_Playback_URL": video_url
            },
            "source": "SonyLIV"
        }
    except Exception as e:
        print(f"Error normalizing SonyLIV item: {e}")
        return None

def normalize_jiohotstar(item):
    """Maps JioHotstar item to Fancode schema"""
    try:
        match_id = item.get("contentId", "")
        title = item.get("title", "Unknown Event")
        status = item.get("status", "LIVE")
        image = item.get("image", "")
        watch_url = item.get("watch_url", "")
        
        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "image": image,
            "STREAMING_CDN": {
                "Primary_Playback_URL": watch_url
            },
            "source": "JioHotstar"
        }
    except Exception as e:
        print(f"Error normalizing JioHotstar item: {e}")
        return None

def generate_m3u(matches):
    content = "#EXTM3U\n"
    for match in matches:
        title = match.get("title", "No Title")
        image = match.get("image", "")
        stream_url = match.get("STREAMING_CDN", {}).get("Primary_Playback_URL", "")
        source = match.get("source", "Fancode")
        
        if stream_url:
            content += f'#EXTINF:-1 tvg-logo="{image}" group-title="{source}",{title}\n'
            content += f'{stream_url}\n'
    return content

def main():
    all_matches = []

    # 1. Fetch Fancode data (Master format)
    fc_data = fetch_data(FANCODE_URL, "Fancode")
    if fc_data:
        # Fancode data might be in "matches" key or root array depending on transient variations, but usually root object has "matches"
        if isinstance(fc_data, dict) and "matches" in fc_data:
            matches = fc_data["matches"]
        elif isinstance(fc_data, list):
            matches = fc_data
        else:
            matches = []
        
        for m in matches:
            m["source"] = "Fancode" # Label source
            all_matches.append(m)

    # 2. Fetch SonyLIV data
    sl_data = fetch_data(SONYLIV_URL, "SonyLIV")
    if sl_data:
        # SonyLIV wrapper check
        sl_matches = []
        if isinstance(sl_data, dict):
             # Check for common wrappers like "matches" key inside
             if "matches" in sl_data:
                 sl_matches = sl_data["matches"]
             else:
                 # It might be in data? Or just the dict itself? 
                 # Based on sample: { ... "matches": [...] }
                 pass
        elif isinstance(sl_data, list):
            sl_matches = sl_data
            
        for item in sl_matches:
            norm = normalize_sonyliv(item)
            if norm:
                all_matches.append(norm)

    # 3. Fetch JioHotstar data
    jh_data = fetch_data(JIOHOTSTAR_URL, "JioHotstar")
    if jh_data:
        # JioHotstar wrapper: { "data": [...] }
        jh_matches = []
        if isinstance(jh_data, dict) and "data" in jh_data:
            jh_matches = jh_data["data"]
        elif isinstance(jh_data, list):
            jh_matches = jh_data
            
        for item in jh_matches:
            norm = normalize_jiohotstar(item)
            if norm:
                all_matches.append(norm)

    # Final Output Structure
    final_json = {
        "name": "live-event",
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_matches": len(all_matches),
        "matches": all_matches
    }

    # Write JSON
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2)
    print(f"Generated {JSON_OUTPUT}")

    # Write M3U
    m3u_content = generate_m3u(all_matches)
    with open(M3U_OUTPUT, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"Generated {M3U_OUTPUT}")

if __name__ == "__main__":
    main()
