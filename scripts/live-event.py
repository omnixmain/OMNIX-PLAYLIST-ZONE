import requests
import json
import datetime
import os

# Source URLs
FANCODE_URL_1 = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/refs/heads/main/data/fancode.json"
FANCODE_URL_2 = "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json"
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

def normalize_fancode_1(item):
    """Maps Fancode Source 1 item to standardized schema favoring passthrough"""
    try:
        # We want to preserve as much as possible from Source 1 as it is the 'template'
        normalized = item.copy()
        
        # Ensure core fields for merging
        match_id_val = item.get("match_id")
        normalized["match_id"] = int(match_id_val) if str(match_id_val).isdigit() else str(match_id_val)
        
        normalized["source"] = "Fancode"
        
        # Ensure STREAMING_CDN exists
        if "STREAMING_CDN" not in normalized or not isinstance(normalized["STREAMING_CDN"], dict):
             normalized["STREAMING_CDN"] = {}

        # Backfill Primary_Playback_URL if missing but video_url exists
        if not normalized["STREAMING_CDN"].get("Primary_Playback_URL") and item.get("video_url"):
             normalized["STREAMING_CDN"]["Primary_Playback_URL"] = item.get("video_url")

        return normalized
    except Exception as e:
        return None

def normalize_fancode_2(item):
    """Maps Fancode Source 2 item to standardized schema"""
    try:
        match_id_val = item.get("match_id")
        match_id = int(match_id_val) if str(match_id_val).isdigit() else str(match_id_val)
        
        title = item.get("title", "Unknown Event")
        status = item.get("status", "LIVE")
        
        # Image
        image = item.get("src") or item.get("image", "")

        # Construct STREAMING_CDN object 
        streaming_cdn = {}
        adfree_url = item.get("adfree_url")
        dai_url = item.get("dai_url")
        
        if adfree_url:
            streaming_cdn["Primary_Playback_URL"] = adfree_url
        if dai_url:
            streaming_cdn["dai_google_cdn"] = dai_url
            
        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "streamingStatus": "STARTED" if status == "LIVE" else "NOT_STARTED",
            "category": item.get("event_category", "Sports"),
            "tournament": item.get("event_name", ""),
            "startTime": item.get("startTime", ""),
            "image": image,
            "src": image,
            "image_cdn": {
                "APP": image,
                "PLAYBACK": image,
                "BG_IMAGE": image
            },
            "teams": [], # Default empty list
            "STREAMING_CDN": streaming_cdn,
            "source": "Fancode"
        }
    except Exception as e:
        return None

def normalize_sonyliv(item):
    try:
        match_id_val = item.get("contentId", "")
        match_id = int(match_id_val) if str(match_id_val).isdigit() else str(match_id_val)
            
        title = item.get("match_name") or item.get("event_name", "Unknown Event")
        is_live = item.get("isLive", False)
        status = "LIVE" if is_live else "COMPLETED"
        image = item.get("src", "")
        video_url = item.get("video_url", "")
        
        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "streamingStatus": "STARTED" if is_live else "COMPLETED",
            "category": "SonyLIV",
            "tournament": "SonyLIV Events",
            "startTime": "",
            "image": image,
            "src": image,
            "image_cdn": {
                "APP": image,
                "PLAYBACK": image,
                "BG_IMAGE": image
            },
            "teams": [],
            "STREAMING_CDN": {
                "Primary_Playback_URL": video_url
            },
            "source": "SonyLIV"
        }
    except Exception as e:
        return None

def normalize_jiohotstar(item):
    try:
        match_id_val = item.get("contentId", "")
        match_id = int(match_id_val) if str(match_id_val).isdigit() else str(match_id_val)
            
        title = item.get("title", "Unknown Event")
        status = item.get("status", "LIVE")
        image = item.get("image", "")
        watch_url = item.get("watch_url", "")
        
        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "streamingStatus": "STARTED" if status == "LIVE" else "COMPLETED",
            "category": "JioHotstar",
            "tournament": "JioHotstar Events",
            "startTime": "",
            "image": image,
            "src": image,
            "image_cdn": {
                "APP": image,
                "PLAYBACK": image,
                "BG_IMAGE": image
            },
            "teams": [],
            "STREAMING_CDN": {
                "Primary_Playback_URL": watch_url
            },
            "source": "JioHotstar"
        }
    except Exception as e:
        return None

def merge_event(fancode_map, new_item):
    match_id = new_item.get("match_id")
    if not match_id:
        return

    # Normalize key to string for lookup map, but keep value's match_id as is (int/str)
    lookup_key = str(match_id)

    if lookup_key in fancode_map:
        existing_item = fancode_map[lookup_key]
        
        # Merge STREAMING_CDN
        existing_cdn = existing_item.get("STREAMING_CDN", {})
        new_cdn = new_item.get("STREAMING_CDN", {})
        
        if new_cdn.get("Primary_Playback_URL") and not existing_cdn.get("Primary_Playback_URL"):
            existing_cdn["Primary_Playback_URL"] = new_cdn["Primary_Playback_URL"]
            
        if new_cdn.get("dai_google_cdn"):
             if not existing_cdn.get("dai_google_cdn"):
                 existing_cdn["dai_google_cdn"] = new_cdn["dai_google_cdn"]
        
        # Merge other rich fields if existing is "poor" (e.g. from Source 2 which is slimmer)
        # If existing missing teams but new has it, take it.
        if "teams" not in existing_item and "teams" in new_item:
            existing_item["teams"] = new_item["teams"]
            
        if "image_cdn" not in existing_item and "image_cdn" in new_item:
             existing_item["image_cdn"] = new_item["image_cdn"]

        existing_item["STREAMING_CDN"] = existing_cdn
        
    else:
        fancode_map[lookup_key] = new_item

def generate_m3u(matches):
    content = "#EXTM3U\n"
    for match in matches:
        title = match.get("title", "No Title")
        image = match.get("image", "")
        source = match.get("source", "Live")
        
        cdn = match.get("STREAMING_CDN", {})
        primary_url = cdn.get("Primary_Playback_URL")
        dai_url = cdn.get("dai_google_cdn")
        
        if primary_url:
            suffix = " [Main]" if dai_url else ""
            display_title = f"{title}{suffix}"
            content += f'#EXTINF:-1 tvg-logo="{image}" group-title="{source}",{display_title}\n'
            content += f'{primary_url}\n'
            
        if dai_url:
            display_title = f"{title} [DAI]"
            content += f'#EXTINF:-1 tvg-logo="{image}" group-title="{source}",{display_title}\n'
            content += f'{dai_url}\n'
            
    return content

def main():
    fancode_map = {} # str(match_id) -> event_dict
    other_matches = []

    # 1. Fetch Fancode Source 1 (The Template)
    fc_data_1 = fetch_data(FANCODE_URL_1, "Fancode 1")
    if fc_data_1:
        matches = []
        if isinstance(fc_data_1, dict) and "matches" in fc_data_1:
            matches = fc_data_1["matches"]
        elif isinstance(fc_data_1, list):
            matches = fc_data_1
        
        for m in matches:
            norm = normalize_fancode_1(m)
            if norm:
                merge_event(fancode_map, norm)

    # 2. Fetch Fancode Source 2
    fc_data_2 = fetch_data(FANCODE_URL_2, "Fancode 2")
    if fc_data_2:
        matches = []
        if isinstance(fc_data_2, dict) and "matches" in fc_data_2:
            matches = fc_data_2["matches"]
        elif isinstance(fc_data_2, list):
            matches = fc_data_2
            
        for m in matches:
            norm = normalize_fancode_2(m)
            if norm:
                merge_event(fancode_map, norm)

    # 3. SonyLIV
    sl_data = fetch_data(SONYLIV_URL, "SonyLIV")
    if sl_data:
        sl_matches = []
        if isinstance(sl_data, dict) and "matches" in sl_data:
             sl_matches = sl_data["matches"]
        elif isinstance(sl_data, list):
            sl_matches = sl_data
        for item in sl_matches:
            norm = normalize_sonyliv(item)
            if norm:
                other_matches.append(norm)

    # 4. JioHotstar
    jh_data = fetch_data(JIOHOTSTAR_URL, "JioHotstar")
    if jh_data:
        jh_matches = []
        if isinstance(jh_data, dict) and "data" in jh_data:
            jh_matches = jh_data["data"]
        elif isinstance(jh_data, list):
            jh_matches = jh_data
        for item in jh_matches:
            norm = normalize_jiohotstar(item)
            if norm:
                other_matches.append(norm)

    final_matches = list(fancode_map.values()) + other_matches
    
    # Calculate counts
    live_count = sum(1 for m in final_matches if m.get("status") == "LIVE")
    upcoming_count = sum(1 for m in final_matches if m.get("status") != "LIVE") # Simplified

    # Final JSON Structure - High Fidelity
    final_json = {
        "Author": "𝕆𝕄ℕ𝕀𝕏 𝔼𝕄ℙ𝕀ℝ𝔼",
        "name": "FanCode Live Matches API",
        "last_updated": datetime.datetime.now().strftime("%I:%M:%S %p %d-%m-%Y"),
        "headers": {
            "User-Agent": "ReactNativeVideo/8.4.0 (Linux;Android 13) AndroidXMedia3/1.1.1",
            "Referer": "https://fancode.com/"
        },
        "total_matches": len(final_matches),
        "live_matches": live_count,
        "upcoming_matches": upcoming_count,
        "matches": final_matches
    }

    # Write JSON
    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2)
    print(f"Generated {JSON_OUTPUT}")

    # Write M3U
    m3u_content = generate_m3u(final_matches)
    with open(M3U_OUTPUT, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"Generated {M3U_OUTPUT}")

if __name__ == "__main__":
    main()
