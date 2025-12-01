#!/usr/bin/env python3
import json
import subprocess
import tempfile

CONFIG_PATH = "/etc/sing-box/config.json"

print("Loading config...")
with open(CONFIG_PATH) as f:
    config = json.load(f)

# Fix Shadowsocks - add network field
for inbound in config["inbounds"]:
    if inbound.get("tag") == "ss-in":
        if "network" not in inbound:
            inbound["network"] = "tcp"
        print(f"Fixed SS: network={inbound['network']}")
        
    elif inbound.get("tag") == "vless-plain-in":
        if "tls" in inbound:
            if "server_name" not in inbound["tls"]:
                inbound["tls"]["server_name"] = "www.microsoft.com"
            print(f"Fixed Plain VLESS: SNI={inbound['tls']['server_name']}")

with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp:
    json.dump(config, tmp, indent=2)
    tmp_path = tmp.name
    
subprocess.run(["sudo", "cp", tmp_path, CONFIG_PATH], check=True)
subprocess.run(["rm", tmp_path], check=True)
subprocess.run(["sudo", "systemctl", "restart", "sing-box"], check=True)

print("Config updated and sing-box restarted")
