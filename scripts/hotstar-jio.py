import requests
import os
import sys

url = "https://hotstarlive.delta-cloud.workers.dev/?token=a13d9c-4b782a-6c90fd-9a1b84"
output_file = "playlist/hotstar-jio.m3u"
# Switching to Android-like User-Agent as Browser UA triggers YouTube redirect
user_agent = "okhttp/3.12.1" 

def fetch_playlist():
    print(f"Fetching URL: {url}")
    print(f"User-Agent: {user_agent}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': user_agent,
        'X-Requested-With': 'com.live.sktechtv', # Often required for these workers
        'cache-control': 'no-cache, no-store',
    })
    
    # Retry strategy
    retries = 3
    for i in range(retries):
        try:
            print(f"Attempt {i+1} of {retries}...")
            response = session.get(url, timeout=20)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                if "#EXTM3U" in content:
                    print("Success! valid M3U data found.")
                    return content
                else:
                    print("Response received properly but does not seem to be M3U content.")
                    print(f"Content preview: {content[:200]}")
            else:
                 print(f"Failed with status code: {response.status_code}")
                 print(f"Response: {response.text[:200]}")

        except requests.RequestException as e:
            print(f"Network error on attempt {i+1}: {e}")
        
    print("All retry attempts failed.")
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
        # Fail hard so the workflow shows red
        print("Could not fetch playlist. Exiting with error.")
        sys.exit(1)
            
if __name__ == "__main__":
    main()
