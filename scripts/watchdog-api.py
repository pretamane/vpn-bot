#!/usr/bin/env python3
"""
SingBox Watchdog with V2Ray API Integration
Uses generated gRPC stubs to query stats and enforce limits
"""

import sys
import time
import subprocess
import grpc
from collections import defaultdict

# Add proto directory to path
sys.path.insert(0, '/home/guest/.gemini/antigravity/scratch/v2ray-proto')

try:
    import command_pb2
    import command_pb2_grpc
except ImportError as e:
    print(f"[FATAL] Failed to import generated proto files: {e}")
    print("Run: cd v2ray-proto && python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. command.proto")
    sys.exit(1)

# Configuration
API_ENDPOINT = "127.0.0.1:10085"
USER_UUID = "98132a92-dfcc-445f-a73e-aa7dddab3398"
MAX_CONCURRENT_IPS = 5
MAX_SPEED_MBPS = 8.0
CHECK_INTERVAL = 5  # Seconds

# State
last_stats = {"downlink": 0, "uplink": 0}
last_check_time = time.time()

def query_user_stats(stub, direction):
    """Query user traffic stats via gRPC"""
    try:
        pattern = f"user>>>{USER_UUID}>>>traffic>>>{direction}"
        request = command_pb2.QueryStatsRequest(
            pattern=pattern,
            reset=False
        )
        response = stub.QueryStats(request, timeout=5)
        
        for stat in response.stat:
            if direction in stat.name:
                return stat.value
        return 0
    except grpc.RpcError as e:
        print(f"[ERROR] gRPC error querying {direction}: {e.code()} - {e.details()}")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to query {direction}: {e}")
        return 0

def get_user_traffic(stub):
    """Get current traffic stats for user"""
    return {
        "downlink": query_user_stats(stub, "downlink"),
        "uplink": query_user_stats(stub, "uplink")
    }

def get_active_connections():
    """Count active connections to port 443"""
    try:
        result = subprocess.run(
            ["sudo", "ss", "-tn", "state", "established", "sport", "=", ":443"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.strip().split("\n")
        ips = set()
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 5:
                src = parts[4].rsplit(":", 1)[0]
                # Filter out IPv6 localhost
                if src not in ["::1", "127.0.0.1"]:
                    ips.add(src)
        return ips
    except Exception as e:
        print(f"[ERROR] Failed to check connections: {e}")
        return set()

def enforce_limits(stub):
    """Main enforcement logic"""
    global last_stats, last_check_time
    
    current_time = time.time()
    time_diff = current_time - last_check_time
    
    if time_diff < CHECK_INTERVAL:
        return
    
    # Get current stats
    current_stats = get_user_traffic(stub)
    
    # Calculate speed
    downlink_diff = current_stats["downlink"] - last_stats["downlink"]
    uplink_diff = current_stats["uplink"] - last_stats["uplink"]
    
    # Convert to Mbps
    downlink_speed_mbps = (downlink_diff * 8) / (time_diff * 1_000_000)
    uplink_speed_mbps = (uplink_diff * 8) / (time_diff * 1_000_000)
    
    print(f"[STATS] Down: {downlink_speed_mbps:.2f} Mbps | Up: {uplink_speed_mbps:.2f} Mbps | Total: {current_stats['downlink']/1_000_000:.1f}MB down, {current_stats['uplink']/1_000_000:.1f}MB up")
    
    # Check speed limits
    violations = []
    if downlink_speed_mbps > MAX_SPEED_MBPS:
        violations.append(f"Download {downlink_speed_mbps:.2f} Mbps > {MAX_SPEED_MBPS} Mbps")
    
    if uplink_speed_mbps > MAX_SPEED_MBPS:
        violations.append(f"Upload {uplink_speed_mbps:.2f} Mbps > {MAX_SPEED_MBPS} Mbps")
    
    # Check connection count
    active_ips = get_active_connections()
    if len(active_ips) > MAX_CONCURRENT_IPS:
        violations.append(f"{len(active_ips)} active IPs > {MAX_CONCURRENT_IPS} limit")
    
    if violations:
        print(f"[VIOLATION] {' | '.join(violations)}")
        print(f"[VIOLATION] Active IPs: {active_ips}")
        # TODO: Implement enforcement action (e.g., restart service, API call to disable user)
    else:
        if active_ips:
            print(f"[OK] {len(active_ips)} active IPs (within limit)")
    
    last_stats = current_stats
    last_check_time = current_time

def main():
    print("=" * 70)
    print("SingBox Watchdog - V2Ray API Integration")
    print("=" * 70)
    print(f"User UUID: {USER_UUID}")
    print(f"API Endpoint: {API_ENDPOINT}")
    print(f"Limits: {MAX_CONCURRENT_IPS} devices, {MAX_SPEED_MBPS} Mbps per device")
    print(f"Check Interval: {CHECK_INTERVAL}s")
    print("=" * 70)
    
    # Connect to gRPC API
    try:
        channel = grpc.insecure_channel(API_ENDPOINT)
        stub = command_pb2_grpc.StatsServiceStub(channel)
        
        # Test connection
        print("[INFO] Testing API connection...")
        test_stats = get_user_traffic(stub)
        print(f"[OK] API connected. Initial stats: {test_stats}")
        
    except Exception as e:
        print(f"[FATAL] Failed to connect to API: {e}")
        return 1
    
    print("[INFO] Starting monitoring loop...")
    print()
    
    try:
        while True:
            enforce_limits(stub)
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
    except Exception as e:
        print(f"[FATAL] Unexpected error: {e}")
        return 1
    finally:
        channel.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
