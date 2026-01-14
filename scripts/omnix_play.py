import json
import os
import urllib.request
import urllib.error
import datetime

def fetch_token():
    token_url = "https://cookies.yecic62314.workers.dev/"
    print(f"Fetching token from {token_url}...")
    try:
        req = urllib.request.Request(token_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        req.add_header('Referer', 'https://mixweb.yecic62314.workers.dev/')
        req.add_header('Origin', 'https://mixweb.yecic62314.workers.dev')
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                token = response.read().decode('utf-8').strip()
                # The token might be a pure string or key=value. 
                # Browser finding said format is __hdnea__=... 
                # If the worker returns just the value, we might need to prepend key.
                # But usually these workers return the full query string or token value.
                # Let's assume it returns the value or full string and handle cleaner.
                # Finding said: "The token format is __hdnea__=st=..."
                # So the worker likely returns "st=..." or "__hdnea__=st=..."
                # Let's inspect the token when we run it. For now, trust the code to append.
                # Parse and print expiry time for user awareness
                try:
                    import datetime
                    # expect token to be key=value or just value. 
                    # __hdnea__=st=...~exp=1767230025~...
                    if "exp=" in token:
                        exp_ts = int(token.split("exp=")[1].split("~")[0])
                        exp_date = datetime.datetime.fromtimestamp(exp_ts)
                        print(f"Token received. Valid until: {exp_date} (Timestamp: {exp_ts})")
                    else:
                        print(f"Token received: {token[:30]}...")
                except Exception as e:
                    print(f"Token received (expiry parse fail): {token[:30]}...")

                return token
    except Exception as e:
        print(f"Error fetching token: {e}")
    return None

def generate_m3u(json_path, output_path):
    # JSON URL derived from site deobfuscation
    json_url = "https://roarzones.yecic62314.workers.dev/"
    
    print(f"Fetching channels from {json_url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://mixweb.yecic62314.workers.dev/",
        "Origin": "https://mixweb.yecic62314.workers.dev"
    }

    try:
        req = urllib.request.Request(json_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            channels = json.load(response)
    except Exception as e:
        print(f"Error fetching channels: {e}")
        # Fallback to local if web fails
        try:
             with open(json_path, 'r', encoding='utf-8') as f:
                channels = json.load(f)
             print("Loaded from local backup.")
        except:
             print("Could not load from web or local.")
             return

    # Fetch Token
    token_param_name = "__hdnea__"
    token_value = fetch_token()
    
    if token_value:
        if not token_value.startswith("__hdnea__="):
           token_value = f"{token_param_name}={token_value}"
    else:
        print("Warning: Generating playlist without signed tokens!")

    print(f"Found {len(channels)} channels.")

    # Calculate BD Time (UTC + 6)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    bd_time = utc_now + datetime.timedelta(hours=6)
    formatted_time = bd_time.strftime("%Y-%m-%d %I:%M %p")

    m3u_header = f"""#EXTM3U
#=================================
# Developed By: OMNIX EMPIER
# IPTV Telegram Channels: https://t.me/omnix_Empire
# Last Updated: {formatted_time} (BD Time)
# TV channel counts :- {len(channels)}
# Disclaimer:
# This tool does NOT host any content.
# It aggregates publicly available data for informational purposes only.
# For any issues or concerns, please contact the developer.
#==================================  """

    m3u_content = [m3u_header]

    # Official Headers identified
    user_agent = "plaYtv/7.1.5 (Linux;Android 13) ExoPlayerLib/2.11.6"
    referer = "https://www.jiotv.com/"

    for channel in channels:
        name = channel.get("channel-name", "Unknown Channel")
        group = channel.get("group-title", "Uncategorized")
        logo = channel.get("tvg-logo", "")
        tvg_id = channel.get("tvg-id", "")
        url = channel.get("mpd_url", "")
        license_type = channel.get("license_type", "")
        license_key = channel.get("license_key", "")
        
        if not url:
            continue

        # Append Token to URL
        final_url = url
        if token_value:
            separator = "&" if "?" in final_url else "?"
            final_url = f"{final_url}{separator}{token_value}"

        # Start entry
        m3u_content.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{group}",{name}')
        
        # Add DRM props if present
        if license_type == "clearkey" and license_key:
            m3u_content.append('#KODIPROP:inputstream.adaptive.license_type=clearkey')
            m3u_content.append(f'#KODIPROP:inputstream.adaptive.license_key={license_key}')
        
        # Add Network Headers via tags (VLC/Kodi)
        m3u_content.append(f'#EXTVLCOPT:http-user-agent={user_agent}')
        
        # Add Cookie tag
        if token_value:
             m3u_content.append(f'#EXTVLCOPT:http-cookie={token_value}')

        m3u_content.append(f'#EXTVLCOPT:http-referrer={referer}')
        
        # Append the URL
        m3u_content.append(final_url)

    print(f"Writing M3U to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"Done! Playlist saved to {output_path}")
    print("To extend expiry in the future, simply run this script again.")

if __name__ == "__main__":
    json_file = "all_channels.json"
    m3u_file = "omnix_play.m3u"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    playlist_dir = os.path.join(os.path.dirname(script_dir), 'playlist')
    os.makedirs(playlist_dir, exist_ok=True)

    json_full_path = os.path.join(playlist_dir, json_file)
    m3u_full_path = os.path.join(playlist_dir, m3u_file)
    
    generate_m3u(json_full_path, m3u_full_path)
