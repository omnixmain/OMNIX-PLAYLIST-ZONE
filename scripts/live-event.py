import requests
import json
import datetime
import os

# Source URLs
FANCODE_URL_1 = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/refs/heads/main/data/fancode.json"
FANCODE_URL_2 = "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json"
JIOHOTSTAR_URL = "https://github.com/drmlive/willow-live-events/raw/refs/heads/main/willow.json"
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
    """Maps Fancode Source 1 item to standardized schema"""
    try:
        match_id = str(item.get("match_id", ""))
        title = item.get("title", "Unknown Event")
        status = item.get("status", "LIVE")
        image = item.get("src", "")
        # Handle variations where src might be different keys
        if not image:
             image = item.get("image", "")

        streams = []
        stream_url = item.get("STREAMING_CDN", {}).get("Primary_Playback_URL") or item.get("video_url")
        if stream_url:
             streams.append({"name": "Main", "url": stream_url})

        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "image": image,
            "streams": streams,
            "source": "Fancode"
        }
    except Exception as e:
        # print(f"Error normalizing Fancode 1 item: {e}")
        return None

def normalize_fancode_2(item):
    """Maps Fancode Source 2 item to standardized schema"""
    try:
        match_id = str(item.get("match_id", ""))
        title = item.get("title", "Unknown Event")
        status = item.get("status", "LIVE")
        image = item.get("src", "")
        
        streams = []
        dai_url = item.get("dai_url")
        adfree_url = item.get("adfree_url")
        
        if adfree_url:
            streams.append({"name": "Ad-Free", "url": adfree_url})
        if dai_url:
            streams.append({"name": "DAI", "url": dai_url})
            
        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "image": image,
            "streams": streams,
            "source": "Fancode"
        }
    except Exception as e:
        # print(f"Error normalizing Fancode 2 item: {e}")
        return None

def normalize_sonyliv(item):
    """Maps SonyLIV item to standardized schema"""
    try:
        match_id = str(item.get("contentId", ""))
        title = item.get("match_name") or item.get("event_name", "Unknown Event")
        is_live = item.get("isLive", False)
        status = "LIVE" if is_live else "COMPLETED"
        image = item.get("src", "")
        video_url = item.get("video_url", "")
        
        streams = []
        if video_url:
            streams.append({"name": "Main", "url": video_url})

        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "image": image,
            "streams": streams,
            "source": "SonyLIV"
        }
    except Exception as e:
        print(f"Error normalizing SonyLIV item: {e}")
        return None

def normalize_jiohotstar(item):
    """Maps JioHotstar item to standardized schema"""
    try:
        match_id = str(item.get("contentId", ""))
        title = item.get("title", "Unknown Event")
        status = item.get("status", "LIVE")
        image = item.get("image", "")
        watch_url = item.get("watch_url", "")
        
        streams = []
        if watch_url:
            streams.append({"name": "Main", "url": watch_url})
        
        return {
            "match_id": match_id,
            "title": title,
            "status": status,
            "image": image,
            "streams": streams,
            "source": "JioHotstar"
        }
    except Exception as e:
        print(f"Error normalizing JioHotstar item: {e}")
        return None

def merge_fancode_events(fancode_map, new_item):
    match_id = new_item.get("match_id")
    if not match_id:
        return

    if match_id in fancode_map:
        existing_item = fancode_map[match_id]
        # Merge streams
        existing_urls = {s["url"] for s in existing_item["streams"]}
        for new_stream in new_item["streams"]:
            if new_stream["url"] not in existing_urls:
                existing_item["streams"].append(new_stream)
                existing_urls.add(new_stream["url"])
        
        # Update other fields if missing in existing
        if not existing_item.get("image") and new_item.get("image"):
            existing_item["image"] = new_item["image"]
    else:
        fancode_map[match_id] = new_item

def generate_m3u(matches):
    content = "#EXTM3U\n"
    for match in matches:
        base_title = match.get("title", "No Title")
        image = match.get("image", "")
        source = match.get("source", "Live")
        streams = match.get("streams", [])
        
        for i, stream in enumerate(streams):
            stream_name = stream.get("name", "Stream")
            stream_url = stream.get("url")
            
            if not stream_url:
                continue

            # If there's only one stream, use base title. If multiple, append stream name.
            # actually user asked to combine them so they show properly. 
            # In M3U, separate entries are needed for valid playback in most players.
            # We will label them clearly.
            if len(streams) > 1:
                display_title = f"{base_title} [{stream_name}]"
            else:
                display_title = base_title
            
            content += f'#EXTINF:-1 tvg-logo="{image}" group-title="{source}",{display_title}\n'
            content += f'{stream_url}\n'
    return content

def main():
    fancode_map = {} # match_id -> event_dict
    other_matches = []

    # 1. Fetch Fancode Source 1
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
                merge_fancode_events(fancode_map, norm)

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
                merge_fancode_events(fancode_map, norm)

    # 3. Fetch SonyLIV data
    sl_data = fetch_data(SONYLIV_URL, "SonyLIV")
    if sl_data:
        sl_matches = []
        if isinstance(sl_data, dict):
             if "matches" in sl_data:
                 sl_matches = sl_data["matches"]
        elif isinstance(sl_data, list):
            sl_matches = sl_data
            
        for item in sl_matches:
            norm = normalize_sonyliv(item)
            if norm:
                other_matches.append(norm)

    # 4. Fetch JioHotstar data
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

    # Combine all
    all_fancode_matches = list(fancode_map.values())
    final_matches = all_fancode_matches + other_matches

    # Final Output Structure
    final_json = {
        "name": "live-event",
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_matches": len(final_matches),
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
