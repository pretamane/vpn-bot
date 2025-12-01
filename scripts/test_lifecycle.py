import sys
import os
import uuid
import json
import subprocess
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from bot.config_manager import add_ss_user, remove_ss_user

# Mock config
SERVER_IP = "43.205.90.213"
SERVER_PORT = 9388 # SS Port
METHOD = "chacha20-ietf-poly1305"

def test_full_lifecycle():
    user_uuid = str(uuid.uuid4())
    name = "Lifecycle-Test-User"
    
    print(f"1. Adding user {name} ({user_uuid})...")
    if not add_ss_user(user_uuid, name):
        print("❌ Failed to add user!")
        return

    print("2. User added and service reloaded. Waiting 5 seconds...")
    time.sleep(5)
    
    print(f"3. Testing connectivity for {user_uuid}...")
    
    # Generate client config
    client_config = {
        "log": {"level": "info"},
        "inbounds": [{"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 10808}],
        "outbounds": [{
            "type": "shadowsocks",
            "tag": "ss-out",
            "server": SERVER_IP,
            "server_port": SERVER_PORT,
            "method": METHOD,
            "password": user_uuid
        }]
    }
    
    config_path = f"test_lifecycle_{user_uuid}.json"
    with open(config_path, "w") as f:
        json.dump(client_config, f, indent=2)
        
    # Test connectivity
    proc = subprocess.Popen(["sing-box", "run", "-c", config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    
    try:
        result = subprocess.run(
            ["curl", "-v", "--proxy", "socks5://127.0.0.1:10808", "https://www.google.com", "--connect-timeout", "10"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ SUCCESS: Connection established!")
        else:
            print(f"❌ FAILURE: Curl failed with code {result.returncode}")
            print(result.stderr)
    finally:
        proc.terminate()
        proc.wait()
        if os.path.exists(config_path):
            os.remove(config_path)
            
    print("4. Cleaning up...")
    remove_ss_user(user_uuid)

if __name__ == "__main__":
    test_full_lifecycle()
