import subprocess
import json
import os
import sys
import time
import base64

# Configuration
SERVER_HOST = "ubuntu@43.205.90.213"
SSH_KEY = "keys/myanmar-vpn-key.pem"
REMOTE_SCRIPT_PATH = "/home/ubuntu/vpn-bot/scripts/remote_user_manager.py"
LOCAL_SCRIPT_PATH = "scripts/remote_user_manager.py"
NS_NAME = "vpn_test_ns"

PROTOCOLS = [
    {"name": "VLESS Reality", "type": "vless", "protocol_arg": "vless"},
    {"name": "Shadowsocks", "type": "ss", "protocol_arg": "ss"},
    {"name": "TUIC v5", "type": "tuic", "protocol_arg": "tuic"},
    {"name": "VLESS Plain", "type": "vless-plain", "protocol_arg": "vless-plain"}
]

def run_ssh_command(command):
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
        SERVER_HOST, command
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def deploy_script():
    print("Deploying remote user manager script...")
    cmd = [
        "scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
        LOCAL_SCRIPT_PATH, f"{SERVER_HOST}:{REMOTE_SCRIPT_PATH}"
    ]
    subprocess.run(cmd, check=True)

def generate_client_config(protocol_info, credentials):
    # Template based on verify_protocols.py
    config = {
        "log": {"level": "debug"},
        "inbounds": [{"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 10800}],
        "outbounds": []
    }
    
    outbound = {
        "tag": "proxy",
        "server": "43.205.90.213"
    }
    
    if protocol_info['type'] == 'vless':
        outbound.update({
            "type": "vless",
            "server_port": 443,
            "uuid": credentials['uuid'],
            "flow": "xtls-rprx-vision",
            "tls": {
                "enabled": True,
                "server_name": "www.google.com",
                "utls": {"enabled": True, "fingerprint": "chrome"},
                "reality": {"enabled": True, "public_key": "x7KInraJeCbtrbMRfE-sbGyCQpQhnRHv6rDVca8RqF0", "short_id": "55abbd7a"}
            }
        })
    elif protocol_info['type'] == 'ss':
        outbound.update({
            "type": "shadowsocks",
            "server_port": 9388,
            "method": "chacha20-ietf-poly1305",
            "password": credentials['password']
        })
    elif protocol_info['type'] == 'tuic':
        outbound.update({
            "type": "tuic",
            "server_port": 2083,
            "uuid": credentials['uuid'],
            "password": credentials['uuid'],
            "tls": {
                "enabled": True,
                "server_name": "www.google.com",
                "alpn": ["h3"],
                "insecure": True
            }
        })
    elif protocol_info['type'] == 'vless-plain':
        outbound.update({
            "type": "vless",
            "server_port": 8444,
            "uuid": credentials['uuid'],
            "tls": {
                "enabled": True,
                "server_name": "www.microsoft.com",
                "insecure": True
            }
        })
        
    config['outbounds'].append(outbound)
    return config

def run_isolated_test(config_path):
    # Use existing run_isolated_test.sh logic but adapted for single run
    # Actually, we can just run sing-box inside the existing NS if it's up, or create it.
    # For simplicity, let's use a modified version of run_isolated_test.sh that takes a config file
    
    # We will write a temp script to run inside NS
    test_script = f"""
import subprocess
import time
import os

print("Starting sing-box...")
log_file = open("e2e_singbox.log", "w")
proc = subprocess.Popen(["sing-box", "run", "-c", "{config_path}"], stdout=log_file, stderr=log_file)
time.sleep(2)

print("Testing connectivity...")
try:
    result = subprocess.run(
        ["curl", "-x", "socks5://127.0.0.1:10800", "-s", "-o", "/dev/null", "-w", "%{{http_code}}", "http://www.google.com"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0 and result.stdout.strip() == "200":
        print("SUCCESS")
    else:
        print(f"FAILED: {{result.stdout.strip()}}")
except Exception as e:
    print(f"ERROR: {{e}}")
finally:
    proc.terminate()
    proc.wait()
    log_file.close()
"""
    with open("temp_test_runner.py", "w") as f:
        f.write(test_script)
        
    # Run inside NS (assuming NS exists or we create it)
    # We'll rely on run_isolated_test.sh to set up NS, but we need to inject our logic.
    # Let's just use 'ip netns exec' assuming the NS is set up. 
    # Wait, run_isolated_test.sh creates and destroys NS.
    # We should probably modify run_isolated_test.sh to accept a command/script to run.
    
    # Alternative: We create a wrapper shell script
    cmd = f"sudo ip netns exec {NS_NAME} python3 temp_test_runner.py"
    
    # We need to ensure NS exists. Let's assume we run this whole script inside the NS? 
    # No, we need internet access to SSH to server.
    
    # Let's use a helper shell script to setup NS, run our python test, then teardown
    # But we need to do this for EACH protocol.
    # Better: Setup NS once, run all tests, teardown.
    pass

def setup_ns():
    subprocess.run(["sudo", "ip", "netns", "add", NS_NAME], check=False)
    subprocess.run(["sudo", "ip", "link", "add", "veth_ns", "type", "veth", "peer", "name", "veth_host"], check=False)
    subprocess.run(["sudo", "ip", "link", "set", "veth_ns", "netns", NS_NAME], check=False)
    subprocess.run(["sudo", "ip", "addr", "add", "10.200.1.1/24", "dev", "veth_host"], check=False)
    subprocess.run(["sudo", "ip", "link", "set", "veth_host", "up"], check=False)
    subprocess.run(["sudo", "ip", "netns", "exec", NS_NAME, "ip", "link", "set", "lo", "up"], check=False)
    subprocess.run(["sudo", "ip", "netns", "exec", NS_NAME, "ip", "addr", "add", "10.200.1.2/24", "dev", "veth_ns"], check=False)
    subprocess.run(["sudo", "ip", "netns", "exec", NS_NAME, "ip", "link", "set", "veth_ns", "up"], check=False)
    subprocess.run(["sudo", "ip", "netns", "exec", NS_NAME, "ip", "route", "add", "default", "via", "10.200.1.1"], check=False)
    subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], stdout=subprocess.DEVNULL)
    # Get main interface
    main_int = subprocess.check_output("ip route | grep default | awk '{print $5}'", shell=True).decode().strip()
    subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "POSTROUTING", "-s", "10.200.1.0/24", "-o", main_int, "-j", "MASQUERADE"], check=False)
    subprocess.run(["sudo", "iptables", "-A", "FORWARD", "-i", main_int, "-o", "veth_host", "-j", "ACCEPT"], check=False)
    subprocess.run(["sudo", "iptables", "-A", "FORWARD", "-o", main_int, "-i", "veth_host", "-j", "ACCEPT"], check=False)

def teardown_ns():
    subprocess.run(["sudo", "ip", "netns", "delete", NS_NAME], check=False)
    # Cleanup iptables (simplified, might leave rules if failed before)
    # Ideally we should be more careful, but for dev env it's okay-ish.

def main():
    deploy_script()
    setup_ns()
    
    results = {}
    
    try:
        for proto in PROTOCOLS:
            print(f"\nTesting {proto['name']}...")
            
            # 1. Add User
            cmd = f"python3 {REMOTE_SCRIPT_PATH} add --protocol {proto['protocol_arg']} --name e2e_test_user"
            res = run_ssh_command(cmd)
            if res.returncode != 0:
                print(f"Failed to add user: {res.stderr}")
                results[proto['name']] = "Setup Failed"
                continue
                
            try:
                data = json.loads(res.stdout)
                
                if data['status'] != 'success':
                    print(f"Error from remote: {data.get('message')}")
                    results[proto['name']] = "Setup Failed"
                    continue
                    
                # 2. Generate Config
                config = generate_client_config(proto, data)
                config_path = f"e2e_{proto['type']}.json"
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                    
                # 3. Run Test
                # Create runner script
                runner_code = f"""
import subprocess, time, sys
log_file = open("e2e_singbox.log", "w")
proc = subprocess.Popen(["sing-box", "run", "-c", "{config_path}"], stdout=log_file, stderr=log_file)
time.sleep(2)
try:
    res = subprocess.run(["curl", "-x", "socks5h://127.0.0.1:10800", "-s", "-o", "/dev/null", "-w", "%{{http_code}}", "http://www.google.com"], capture_output=True, text=True, timeout=10)
    if res.returncode == 0 and res.stdout.strip() == "200": print("SUCCESS")
    else:
        print(f"FAILED: {{res.stdout.strip()}}")
        print(f"Curl Stderr: {{res.stderr}}")
        print("--- Sing-Box Log ---")
        try:
            with open("e2e_singbox.log", "r") as f: print(f.read())
        except: print("Log file not found")
        print("--------------------")
except Exception as e:
    print(f"ERROR: {{e}}")
    print("--- Sing-Box Log ---")
    try:
        subprocess.run(["sudo", "cat", "e2e_singbox.log"], check=False)
    except: print("Failed to read log file")
    print("--------------------")
finally: proc.terminate()
"""
                with open("temp_runner.py", "w") as f:
                    f.write(runner_code)
                    
                res = subprocess.run(["sudo", "ip", "netns", "exec", NS_NAME, "python3", "temp_runner.py"], capture_output=True, text=True)
                status = res.stdout.strip()
                print(f"Result: {status}")
                results[proto['name']] = status

            except json.JSONDecodeError:
                print(f"Failed to parse JSON from remote: {res.stdout}")
                print(f"Remote stderr: {res.stderr}")
                results[proto['name']] = "Setup Failed"
                continue
                
            finally:
                # 4. Remove User
                if 'data' in locals() and data:
                    identifier = data.get('uuid') or data.get('password')
                    if identifier:
                        cmd = f"python3 {REMOTE_SCRIPT_PATH} remove --protocol {proto['protocol_arg']} --id {identifier}"
                        run_ssh_command(cmd)
                    
    finally:
        teardown_ns()
        if os.path.exists("temp_runner.py"): os.remove("temp_runner.py")
        
    print("\n=== E2E Test Results ===")
    for name, status in results.items():
        icon = "✅" if status == "SUCCESS" else "❌"
        print(f"{icon} {name}: {status}")

if __name__ == "__main__":
    main()
