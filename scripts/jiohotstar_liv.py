import requests
import os
import datetime
import sys

# Configuration
URL = "https://hotstar-live-event.alpha-circuit.workers.dev/?token=a13d9c-4b782a-6c90fd-9a1b84"
OUTPUT_FILE = "playlist/jiohotstar_liv.m3u"

# List of agents to try
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0", # Working UA
    "okhttp/3.12.1", 
    "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
]

def fetch_playlist():
    print(f"Fetching URL: {URL}")
    
    session = requests.Session()
    
    for attempt, agent in enumerate(user_agents):
        print(f"\n--- Attempt {attempt+1} with User-Agent: {agent} ---")
        
        try:
            headers = {
                'User-Agent': agent,
                'Accept': '*/*',
                'cache-control': 'no-cache, no-store',
            }
            
            response = session.get(URL, headers=headers, timeout=20)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                if "#EXTM3U" in content:
                    print("Success! valid M3U data found.")
                    return content
                else:
                    print("Response received properly but does not seem to be M3U content.")
                    # print(f"Preview: {content[:100]}...") # Debug preview
            else:
                 print(f"Failed with status code: {response.status_code}")

        except requests.RequestException as e:
            print(f"Network error: {e}")
            
    print("\nAll User-Agents failed.")
    return None

def main():
    content = fetch_playlist()
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    if content:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            # Calculate BD Time (UTC + 6)
            utc_now = datetime.datetime.utcnow()
            bd_time = utc_now + datetime.timedelta(hours=6)
            formatted_time = bd_time.strftime("%Y-%m-%d %I:%M %p")
            
            lines = content.splitlines()
            channel_count = sum(1 for line in lines if line.strip().startswith("#EXTINF"))
            
            # Remove existing #EXTM3U if present
            if lines and lines[0].startswith("#EXTM3U"):
                lines.pop(0)

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
            f.write(m3u_header)
            f.write("\n".join(lines))
        print(f"Saved playlist to {OUTPUT_FILE}")
    else:
        print("Failed to fetch content.")
        if not os.path.exists(OUTPUT_FILE):
             sys.exit(1)

if __name__ == "__main__":
    main()
