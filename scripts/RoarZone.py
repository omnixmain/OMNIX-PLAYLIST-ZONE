import requests
import json
import os

SERVER_URL = "http://160.187.56.254:8096"
CLIENT = "Emby Data Extractor"
DEVICE = "Python Script"
DEVICE_ID = "python_script_001"
VERSION = "1.0.0"

USERNAME = "RoarZone_Guest"
PASSWORD = ""

def authenticate():
    url = f"{SERVER_URL}/Users/AuthenticateByName"
    headers = {
        "Content-Type": "application/json",
        "X-Emby-Authorization": f'MediaBrowser Client="{CLIENT}", Device="{DEVICE}", DeviceId="{DEVICE_ID}", Version="{VERSION}"'
    }
    data = {"Username": USERNAME, "Pw": PASSWORD}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    return result["AccessToken"], result["User"]["Id"]

def format_duration(ticks):
    if not ticks:
        return ""
    seconds = ticks / 10000000
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def get_items(api_key, user_id):
    url = f"{SERVER_URL}/Users/{user_id}/Items"
    headers = {"X-Emby-Token": api_key}
    # Requesting more fields
    params = {
        "IncludeItemTypes": "Movie,Series", 
        "Recursive": "true", 
        "Fields": "Overview,Path,MediaSources,ImageTags,Genres,ProductionYear,CommunityRating,OfficialRating,RunTimeTicks,MediaStreams,OriginalTitle,OriginalLanguage,ProductionLocations"
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json().get("Items", [])

def determine_category(language_code, original_language, production_locations):
    # Normalize inputs
    lang_audio = language_code.lower() if language_code else ""
    lang_orig = original_language.lower() if original_language else ""
    locations = [loc.lower() for loc in production_locations] if production_locations else []
    
    # helper for south indian
    south_langs = ['tam', 'tamil', 'tel', 'telugu', 'mal', 'malayalam', 'kan', 'kannada']
    
    # 1. Check Original Language (Most reliable for origin)
    if any(x in lang_orig for x in ['hin', 'hindi']):
        return "Bollywood"
    if any(x in lang_orig for x in ['ben', 'bengali']):
        return "Bengali"
    if any(x in lang_orig for x in south_langs):
        return "South Indian"
    if any(x in lang_orig for x in ['eng', 'english']):
        return "Hollywood"

    # 2. Check Locations (If India, try to guess specific industry from audio)
    if any("india" in loc for loc in locations):
        if any(x in lang_audio for x in south_langs):
            return "South Indian"
        if any(x in lang_audio for x in ['ben', 'bengali']):
            return "Bengali"
        # Default for India is Bollywood if no specific regional audio found
        return "Bollywood"
        
    # 3. Fallback to Audio Language
    if any(x in lang_audio for x in ['hin', 'hindi']):
        return "Bollywood"
    if any(x in lang_audio for x in ['ben', 'bengali']):
        return "Bengali"
    if any(x in lang_audio for x in south_langs):
        return "South Indian"
    if any(x in lang_audio for x in ['eng', 'english']):
        return "Hollywood"
    
    return "Other"

def determine_type(item_type):
    if item_type == "Series":
        return "Web Series"
    return "Movie"

def main():
    print(f"Logging in as {USERNAME}...")
    try:
        api_key, user_id = authenticate()
        print("Login success!")
        
        items = get_items(api_key, user_id)
        print(f"Found {len(items)} items.")
        
        json_data = []
        m3u_lines = ["#EXTM3U"]
        
        for item in items:
            item_id = item.get("Id")
            name = item.get("Name")
            overview = item.get("Overview", "")
            item_type = item.get("Type", "Movie")
            
            # Metadata for categorization
            original_language = item.get("OriginalLanguage", "")
            production_locations = item.get("ProductionLocations", [])
            
            # 1. Genres
            genres = item.get("Genres", [])
            genre_str = ", ".join(genres) if genres else ""
            
            # 2. Year & Rating
            year = item.get("ProductionYear", "")
            rating_score = item.get("CommunityRating", "") # e.g. 7.1
            official_rating = item.get("OfficialRating", "") # e.g. PG-13
            
            # 3. Duration
            duration = format_duration(item.get("RunTimeTicks"))
            
            # 4. Media Info (Video/Audio)
            video_quality = ""
            audio_info = ""
            language_code = "und" # Default undefined
            container = "mp4" # default
            
            if item.get("MediaSources"):
                source = item["MediaSources"][0]
                container = source.get("Container", "mp4")
                
                # Video Details
                streams = source.get("MediaStreams", [])
                video_stream = next((s for s in streams if s.get("Type") == "Video"), None)
                if video_stream:
                    width = video_stream.get("Width")
                    height = video_stream.get("Height")
                    codec = video_stream.get("Codec", "").upper()
                    
                    if width and height:
                        if width >= 3800: res = "4K"
                        elif width >= 1900: res = "1080p"
                        elif width >= 1200: res = "720p"
                        else: res = "SD"
                        video_quality = f"{res} {codec}"
                    else:
                        video_quality = codec

                # Audio Details
                audio_stream = next((s for s in streams if s.get("Type") == "Audio" and s.get("IsDefault")), None)
                if not audio_stream and streams:
                     # Fallback to first audio stream
                     audio_stream = next((s for s in streams if s.get("Type") == "Audio"), None)
                
                if audio_stream:
                    lang = audio_stream.get("Language", "Unknown")
                    language_code = lang # Keep raw code for logic
                    lang_display = lang.title()
                    codec = audio_stream.get("Codec", "").upper()
                    channels = audio_stream.get("Channels", "")
                    channel_layout = "5.1" if channels == 6 else "2.0" # Simplification
                    audio_info = f"{lang_display} {codec} {channel_layout}"

            # Construct Image URL
            image_url = ""
            if item.get("ImageTags", {}).get("Primary"):
                image_tag = item["ImageTags"]["Primary"]
                image_url = f"{SERVER_URL}/Items/{item_id}/Images/Primary?maxHeight=400&maxWidth=267&quality=90"

            # Construct Video Stream URL
            stream_url = f"{SERVER_URL}/Videos/{item_id}/stream.{container}?static=true&api_key={api_key}"
            
            # Category & Type Logic
            category = determine_category(language_code, original_language, production_locations) 
            content_type = determine_type(item_type)

            movie_obj = {
                "id": item_id,
                "title": name,
                "overview": overview,
                "genres": genre_str,
                "year": year,
                "rating": rating_score,
                "content_rating": official_rating,
                "duration": duration,
                "video_quality": video_quality,
                "audio_info": audio_info,
                "image": image_url,
                "stream_url": stream_url,
                "category": category,      # New Field
                "type": content_type       # New Field
            }
            json_data.append(movie_obj)
            
            # M3U Entry
            title_ext = f"{name} ({year})"
            if video_quality: title_ext += f" - [{video_quality}]"
            
            # Add category to group-title in M3U for better organization in players
            group_title = f"{category};{genre_str}" if genre_str else category
            
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{item_id}" tvg-logo="{image_url}" group-title="{group_title}",{title_ext}')
            m3u_lines.append(stream_url)
            
        # Ensure output directory exists
        output_dir = "playlist"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(os.path.join(output_dir, "RoarZone.json"), "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        
        with open(os.path.join(output_dir, "RoarZone.m3u"), "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
            
        print(f"Data saved to {output_dir}/RoarZone.json and {output_dir}/RoarZone.m3u. Extracted {len(json_data)} items.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
