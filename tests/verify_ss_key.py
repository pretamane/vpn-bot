import json
import os
import subprocess
import time
import sys
import base64

# Key Details from User
# ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTowMjY0YmQxOC0yZGNhLTRkMDItOWRiNy02ZWY4MWQyZDMzZTQ=@43.205.90.213:9388#pretamane-Key16
# Decoded: chacha20-ietf-poly1305:0264bd18-2dca-4d02-9db7-6ef81d2d33e4

SERVER_IP = "43.205.90.213"
SERVER_PORT = 9388
METHOD = "chacha20-ietf-poly1305"
PASSWORD = "0264bd18-2dca-4d02-9db7-6ef81d2d33e4"
TAG = "pretamane-Key16"

CLIENT_CONFIG = {
    "log": {"level": "debug"},
    "inbounds": [
        {
            "type": "mixed",
            "tag": "mixed-in",
            "listen": "127.0.0.1",
            "listen_port": 10800
        }
    ],
    "outbounds": [
        {
            "type": "shadowsocks",
            "tag": "proxy",
            "server": SERVER_IP,
            "server_port": SERVER_PORT,
            "method": METHOD,
            "password": PASSWORD
        }
    ]
}

def run_test():
    print(f"Testing Shadowsocks Key: {TAG}")
    print(f"Server: {SERVER_IP}:{SERVER_PORT}")
    
    config_path = "test_ss_key.json"
    log_path = "singbox_ss_key.log"
    
    with open(config_path, 'w') as f:
        json.dump(CLIENT_CONFIG, f, indent=2)
        
    log_file = open(log_path, "w")
    process = subprocess.Popen(["sing-box", "run", "-c", config_path], stdout=log_file, stderr=log_file)
    time.sleep(2) # Wait for startup
    
    try:
        # Test connectivity
        print("Attempting connection to http://www.google.com...")
        result = subprocess.run(
            ["curl", "-x", "socks5://127.0.0.1:10800", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://www.google.com"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip() == "200":
            print(f"✅ Connection SUCCESS (HTTP 200)")
        else:
            print(f"❌ Connection FAILED (Code: {result.stdout.strip()})")
            print("--- Sing-Box Log ---")
            with open(log_path, "r") as f:
                print(f.read())
            print("--------------------")
            
    except subprocess.TimeoutExpired:
         print(f"❌ Connection FAILED (Timeout)")
         print("--- Sing-Box Log ---")
         with open(log_path, "r") as f:
             print(f.read())
         print("--------------------")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        process.terminate()
        process.wait()
        log_file.close()
        if os.path.exists(config_path):
            os.remove(config_path)
        # Keep log file for review if needed, or print it above

if __name__ == "__main__":
    run_test()
