#!/usr/bin/env python3
"""
SingBox Watchdog with V2Ray API Integration
Monitors user traffic and enforces device/speed limits
"""

import time
import subprocess
import json
from collections import defaultdict

# Configuration
API_ENDPOINT = "127.0.0.1:10085"
USER_UUID = "98132a92-dfcc-445f-a73e-aa7dddab3398"
MAX_CONCURRENT_IPS = 5
MAX_SPEED_MBPS = 8.0
CHECK_INTERVAL = 5  # Seconds

# State
last_stats = {"downlink": 0, "uplink": 0}
last_check_time = time.time()

def query_stats_grpcurl(pattern):
    """Query stats using grpcurl command"""
    try:
        cmd = [
            "grpcurl",
            "-plaintext",
            "-d", json.dumps({"pattern": pattern, "reset": False}),
            API_ENDPOINT,
            "v2ray.core.app.stats.command.StatsService/QueryStats"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"[ERROR] grpcurl failed: {result.stderr}")
            return None
    except FileNotFoundError:
        print("[ERROR] grpcurl not found. Install with: sudo apt install grpcurl")
        return None
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        return None

def get_user_traffic():
    """Get traffic stats for the user"""
    stats = {}
    
    # Query downlink
    downlink_pattern = f"user>>>{USER_UUID}>>>traffic>>>downlink"
    result = query_stats_grpcurl(downlink_pattern)
    if result and "stat" in result:
        for stat in result["stat"]:
            if "downlink" in stat.get("name", ""):
                stats["downlink"] = int(stat.get("value", 0))
    
    # Query uplink
    uplink_pattern = f"user>>>{USER_UUID}>>>traffic>>>uplink"
    result = query_stats_grpcurl(uplink_pattern)
    if result and "stat" in result:
        for stat in result["stat"]:
            if "uplink" in stat.get("name", ""):
                stats["uplink"] = int(stat.get("value", 0))
    
    return stats

def get_active_connections():
    """Count active connections to port 443"""
    try:
        result = subprocess.run(
            ["sudo", "ss", "-tn", "state", "established", "sport", "=", ":443"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split("\n")
        # Filter out header and count unique source IPs
        ips = set()
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 5:
                # Extract source IP from "IP:PORT" format
                src = parts[4].rsplit(":", 1)[0]
                ips.add(src)
        return ips
    except Exception as e:
        print(f"[ERROR] Failed to check connections: {e}")
        return set()

def enforce_limits():
    global last_stats, last_check_time
    
    current_time = time.time()
    time_diff = current_time - last_check_time
    
    if time_diff < CHECK_INTERVAL:
        return
    
    # Get current stats
    current_stats = get_user_traffic()
    
    if current_stats:
        # Calculate speed
        downlink_diff = current_stats.get("downlink", 0) - last_stats.get("downlink", 0)
        uplink_diff = current_stats.get("uplink", 0) - last_stats.get("uplink", 0)
        
        # Convert to Mbps
        downlink_speed_mbps = (downlink_diff * 8) / (time_diff * 1_000_000)
        uplink_speed_mbps = (uplink_diff * 8) / (time_diff * 1_000_000)
        
        print(f"[STATS] Down: {downlink_speed_mbps:.2f} Mbps | Up: {uplink_speed_mbps:.2f} Mbps")
        
        # Check speed limits
        if downlink_speed_mbps > MAX_SPEED_MBPS:
            print(f"[VIOLATION] Download speed {downlink_speed_mbps:.2f} Mbps > {MAX_SPEED_MBPS} Mbps")
        
        if uplink_speed_mbps > MAX_SPEED_MBPS:
            print(f"[VIOLATION] Upload speed {uplink_speed_mbps:.2f} Mbps > {MAX_SPEED_MBPS} Mbps")
        
        last_stats = current_stats
    
    # Check connection count
    active_ips = get_active_connections()
    if len(active_ips) > MAX_CONCURRENT_IPS:
        print(f"[VIOLATION] {len(active_ips)} active IPs > {MAX_CONCURRENT_IPS} limit: {active_ips}")
    else:
        print(f"[INFO] Active connections: {len(active_ips)} IPs")
    
    last_check_time = current_time

def main():
    print("=" * 60)
    print("SingBox Watchdog - API Enabled")
    print("=" * 60)
    print(f"User UUID: {USER_UUID}")
    print(f"API Endpoint: {API_ENDPOINT}")
    print(f"Limits: {MAX_CONCURRENT_IPS} devices, {MAX_SPEED_MBPS} Mbps")
    print(f"Check Interval: {CHECK_INTERVAL}s")
    print("=" * 60)
    
    # Test API connectivity
    print("[INFO] Testing API connectivity...")
    test_stats = get_user_traffic()
    if test_stats:
        print(f"[OK] API accessible. Initial stats: {test_stats}")
    else:
        print("[WARNING] Could not query API. Continuing anyway...")
    
    print("[INFO] Starting monitoring loop...")
    
    while True:
        try:
            enforce_limits()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down...")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
