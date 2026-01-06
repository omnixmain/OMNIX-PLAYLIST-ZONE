import requests
import os

def download_m3u():
    url = "https://raw.githubusercontent.com/bugsfreeweb/LiveTVCollector/refs/heads/main/Movies/Private/Movies.m3u"
    
    # Ensure playlist directory exists
    playlist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'playlist')
    os.makedirs(playlist_dir, exist_ok=True)
    
    output_file = os.path.join(playlist_dir, "omnix_adult_zone.m3u")
    
    try:
        print(f"Downloading M3U from {url}...")
        response = requests.get(url)
        response.raise_for_status()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
            
        print(f"Successfully downloaded and saved to {output_file}")
        
    except Exception as e:
        print(f"Error downloading M3U: {str(e)}")
        # Don't exit with error to avoid failing the workflow completely if just source is down, 
        # but for now let's exit to notify failure
        exit(1)

if __name__ == "__main__":
    download_m3u()
