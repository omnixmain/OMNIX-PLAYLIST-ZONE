import requests
import os
import sys
import datetime

url = "https://hotstarlive.delta-cloud.workers.dev/?token=240bb9-374e2e-3c13f0-4a7xz5"
output_file = "playlist/JIOSTAR.m3u"

# List of agents to try
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0", # Working UA
    "okhttp/3.12.1", 
    "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
]

def fetch_playlist():
    print(f"Fetching URL: {url}")
    
    session = requests.Session()
    
    for attempt, agent in enumerate(user_agents):
        print(f"\n--- Attempt {attempt+1} with User-Agent: {agent} ---")
        
        try:
            headers = {
                'User-Agent': agent,
                'Accept': '*/*',
                'cache-control': 'no-cache, no-store',
            }
            
            response = session.get(url, headers=headers, timeout=20)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                if "#EXTM3U" in content:
                    print("Success! valid M3U data found.")
                    return content
                else:
                    print("Response received properly but does not seem to be M3U content.")
                    print(f"Preview: {content[:100]}...")
            else:
                 print(f"Failed with status code: {response.status_code}")

        except requests.RequestException as e:
            print(f"Network error: {e}")
            
    print("\nAll User-Agents failed.")
    return None

def main():
    content = fetch_playlist()
    
    # Ensure directory exists regardless of success, to avoid path errors
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    if content:
        with open(output_file, "w", encoding="utf-8") as f:
            # Calculate BD Time (UTC + 6)
            utc_now = datetime.datetime.utcnow()
            bd_time = utc_now + datetime.timedelta(hours=6)
            formatted_time = bd_time.strftime("%Y-%m-%d %I:%M %p")
            
            lines = content.splitlines()
            channel_count = sum(1 for line in lines if line.strip().startswith("#EXTINF"))
            
            # Remove existing #EXTM3U or header lines if simple
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
        print(f"Saved playlist to {output_file}")
    else:
        # Check if file exists to determine if we should fail hard or just warn
        if os.path.exists(output_file):
            print("Could not update playlist. Keeping existing file.")
        
        # Fail hard so the workflow shows red
        print("Required playlist could not be fetched. Exiting with error.")
        sys.exit(1)
            
if __name__ == "__main__":
    main()
