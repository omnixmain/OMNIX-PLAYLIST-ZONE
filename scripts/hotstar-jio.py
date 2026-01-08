import requests
import os

url = "https://hotstarlive.delta-cloud.workers.dev/?token=a13d9c-4b782a-6c90fd-9a1b84"
output_file = "playlist/hotstar-jio.m3u"

# Working User-Agent
user_agent = "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0"

print(f"Fetching URL: {url}")
print(f"User-Agent: {user_agent}")

try:
    headers = {
        'User-Agent': user_agent,
        'cache-control': 'no-cache, no-store',
    }
    
    response = requests.get(url, headers=headers, timeout=15)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.text
        if "#EXTM3U" in content:
            print("Success! valid M3U data found.")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Saved playlist to {output_file}")
        else:
            print("Response is not a valid M3U playlist.")
            print(content[:200]) # Print start of content for debugging
    else:
        print(f"Failed with status code: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Error: {e}")
