import json
import os
import subprocess
import time
import sys

# Configuration
SERVER_IP = "43.205.90.213"
TEST_UUID = "11111111-1111-1111-1111-111111111111"
TEST_PASSWORD = "test-password-123"
PUBLIC_KEY = "x7KInraJeCbtrbMRfE-sbGyCQpQhnRHv6rDVca8RqF0"
SHORT_ID = "55abbd7a"
SERVER_NAME = "www.microsoft.com"

# Actual keys from config.py (I should read them or hardcode them if I know them)
# Let's try to read from config.py or use the ones I saw earlier.
# PUBLIC_KEY = os.getenv("PUBLIC_KEY") ... wait, I am local.
# I saw config.py content earlier.
# PUBLIC_KEY = "7i07..." wait, I need to check config.py again to be sure.

# Let's use a placeholder and I will fill it in after checking config.py
# Or I can just read config.py in this script if I set PYTHONPATH correctly.

sys.path.append(os.path.join(os.getcwd(), 'src'))
try:
    from bot.config import PUBLIC_KEY, SHORT_ID, SERVER_NAME
except ImportError:
    print("Could not import config. Using hardcoded values.")

# Protocols to test
PROTOCOLS = [
    {
        "name": "VLESS Reality",
        "type": "vless",
        "server_port": 443,
        "uuid": TEST_UUID,
        "flow": "xtls-rprx-vision",
        "tls": {
            "enabled": True,
            "server_name": SERVER_NAME,
            "utls": {"enabled": True, "fingerprint": "chrome"},
            "reality": {"enabled": True, "public_key": PUBLIC_KEY, "short_id": SHORT_ID}
        }
    },
    {
        "name": "Shadowsocks",
        "type": "shadowsocks",
        "server_port": 9388,
        "password": TEST_PASSWORD,
        "method": "chacha20-ietf-poly1305"
    },
    {
        "name": "TUIC v5",
        "type": "tuic",
        "server_port": 2083,
        "uuid": TEST_UUID,
        "password": TEST_PASSWORD,
        "mtu": 1200,
        "tls": {
            "enabled": True,
            "server_name": SERVER_NAME,
            "alpn": ["h3"],
            "insecure": True
        }
    },
    {
        "name": "VLESS Plain (Actually TLS)",
        "type": "vless",
        "server_port": 8444,
        "uuid": TEST_UUID,
        "tls": {
            "enabled": True,
            "server_name": SERVER_NAME,
            "insecure": True
        }
    },
    {
        "name": "Shadowsocks Legacy",
        "type": "shadowsocks",
        "server_port": 8388,
        "password": "W+UUieKAlVMtz0JS4RA1u7o2b75dVjBF", # Hardcoded legacy password
        "method": "chacha20-ietf-poly1305"
    }
]

CLIENT_CONFIG_TEMPLATE = {
    "log": {"level": "debug"},
    "inbounds": [
        {
            "type": "mixed",
            "tag": "mixed-in",
            "listen": "127.0.0.1",
            "listen_port": 10800
        }
    ],
    "outbounds": []
}

def run_test():
    print(f"Server IP: {SERVER_IP}")
    print(f"Public Key: {PUBLIC_KEY}")
    
    for proto in PROTOCOLS:
        print(f"\nTesting {proto['name']}...")
        
        # Build outbound
        outbound = {
            "type": proto['type'],
            "tag": "proxy",
            "server": SERVER_IP,
            "server_port": proto['server_port']
        }
        
        if proto['type'] == 'vless':
            outbound['uuid'] = proto['uuid']
            if 'flow' in proto: outbound['flow'] = proto['flow']
            if 'tls' in proto: outbound['tls'] = proto['tls']
            
        elif proto['type'] == 'shadowsocks':
            outbound['password'] = proto['password']
            outbound['method'] = proto['method']
            
        elif proto['type'] == 'tuic':
            outbound['uuid'] = proto['uuid']
            # outbound['password'] = proto['password'] # Check if needed
            if 'congestion_control' in proto: outbound['congestion_control'] = proto['congestion_control']
            if 'tls' in proto: outbound['tls'] = proto['tls']

        config = CLIENT_CONFIG_TEMPLATE.copy()
        config['outbounds'] = [outbound]
        
        # Save config
        config_path = "test_client_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        # Start sing-box
        log_file = open(f"singbox_{proto['type']}.log", "w")
        process = subprocess.Popen(["sing-box", "run", "-c", config_path], stdout=log_file, stderr=log_file)
        time.sleep(2) # Wait for startup
        
        try:
            # Test connectivity
            result = subprocess.run(
                ["curl", "-x", "socks5://127.0.0.1:10800", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://www.google.com"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip() == "200":
                print(f"✅ {proto['name']}: SUCCESS (HTTP 200)")
            else:
                print(f"❌ {proto['name']}: FAILED (Code: {result.stdout.strip()})")
                print("--- Sing-Box Log ---")
                with open(f"singbox_{proto['type']}.log", "r") as f:
                    print(f.read())
                print("--------------------")
        except subprocess.TimeoutExpired:
             print(f"❌ {proto['name']}: FAILED (Timeout)")
             print("--- Sing-Box Log ---")
             with open(f"singbox_{proto['type']}.log", "r") as f:
                 print(f.read())
             print("--------------------")
        except Exception as e:
            print(f"❌ {proto['name']}: FAILED ({e})")
        finally:
            process.terminate()
            process.wait()
            if os.path.exists(config_path):
                os.remove(config_path)

if __name__ == "__main__":
    run_test()
