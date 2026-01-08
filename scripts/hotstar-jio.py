import requests
import os
import sys

url = "https://hotstarlive.delta-cloud.workers.dev/?token=a13d9c-4b782a-6c90fd-9a1b84"
output_file = "playlist/hotstar-jio.m3u"

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
                'cache-control': 'no-cache, no-store',
                # 'X-Requested-With': 'com.live.sktechtv' if 'okhttp' in agent else 'XMLHttpRequest', 
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
            f.write(content)
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
