import requests
import json
import os

def fetch_jio_tv_data():
    url = "https://jtv.pfy.workers.dev/"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"JSON saved to {filepath}")

def generate_m3u(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        
        for channel in data:
            name = channel.get('name', 'Unknown Channel')
            logo = channel.get('logo', '')
            link = channel.get('link', '')
            drm_scheme = channel.get('drmScheme', '')
            drm_license = channel.get('drmLicense', '')
            cookie = channel.get('cookie', '')
            
            # Skip invalid entries
            if not link:
                continue

            # Write EXTINF info
            f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="JioTV", {name}\n')
            
            # Write DRM info if available
            if drm_scheme:
                f.write(f'#KODIPROP:inputstream.adaptive.license_type={drm_scheme}\n')
            if drm_license:
                f.write(f'#KODIPROP:inputstream.adaptive.license_key={drm_license}\n')
            
            # Construct final URL with headers if needed
            final_url = link
            if cookie:
                final_url += f"|Cookie={cookie}"
            
            f.write(f'{final_url}\n')
    
    print(f"M3U saved to {filepath}")

def main():
    print("Starting JioTV processing...")
    data = fetch_jio_tv_data()
    
    if data:
        playlist_dir = os.path.join(os.getcwd(), "playlist")
        json_path = os.path.join(playlist_dir, "jio-tv(omnix).json")
        m3u_path = os.path.join(playlist_dir, "jio-tv(omnix).m3u")
        
        save_json(data, json_path)
        generate_m3u(data, m3u_path)
        print("Processing complete.")
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    main()
