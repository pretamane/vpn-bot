import time
import subprocess
import re
import json
import os
from collections import defaultdict, deque

# Configuration
LOG_FILE = "/var/log/singbox/access.log"
MAX_CONCURRENT_IPS = 5
MAX_SPEED_MBPS = 8.0
CHECK_INTERVAL = 5  # Seconds
WINDOW_SIZE = 60 # Seconds to look back for concurrency

# State
user_ips = defaultdict(lambda: deque()) # UUID -> deque of (timestamp, ip)
user_bytes = defaultdict(int) # UUID -> total bytes
last_check_time = time.time()

def follow(file):
    file.seek(0, os.SEEK_END)
    while True:
        line = file.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def parse_line(line):
    # Log format examples:
    # +0630 2025-11-22 02:31:29 INFO [751975074 0ms] inbound/vless[vless-in]: inbound connection from 127.0.0.1:38372
    # +0630 2025-11-22 02:31:29 INFO [751975074 100ms] inbound/vless[vless-in]: outbound connection to example.com:80 user: uuid ...
    
    try:
        # Extract Request ID
        id_match = re.search(r'\[(?P<id>\d+)\s', line)
        if not id_match:
            return None
        req_id = id_match.group('id')

        # Extract IP
        ip_match = re.search(r'inbound connection from (?P<ip>[^:]+):', line)
        if ip_match:
            return {'type': 'connect', 'id': req_id, 'ip': ip_match.group('ip')}

        # Extract User
        user_match = re.search(r'user: (?P<user>[^ ]+)', line)
        if user_match:
            return {'type': 'auth', 'id': req_id, 'user': user_match.group('user')}
            
        return None
    except Exception as e:
        print(f"Error parsing line: {e}")
        return None

# State for correlation
request_ips = {} # req_id -> ip

def enforce_limits():
    global last_check_time, request_ips
    current_time = time.time()
    time_diff = current_time - last_check_time
    
    # Cleanup old request_ips (optional, to prevent memory leak)
    if len(request_ips) > 10000:
        request_ips.clear() # Simple flush

    if time_diff < CHECK_INTERVAL:
        return

    # Check Concurrency
    for uuid, history in user_ips.items():
        # Clean old entries
        while history and history[0][0] < current_time - WINDOW_SIZE:
            history.popleft()
        
        unique_ips = set(ip for ts, ip in history)
        if len(unique_ips) > MAX_CONCURRENT_IPS:
            print(f"[VIOLATION] User {uuid} has {len(unique_ips)} IPs: {unique_ips}")
            # TODO: Trigger block action
            # For now, we just log. To block, we would need to restart service or use API.

    last_check_time = current_time

def main():
    print("Starting Watchdog...")
    if not os.path.exists(LOG_FILE):
        print(f"Log file {LOG_FILE} not found. Waiting...")
        while not os.path.exists(LOG_FILE):
            time.sleep(1)

    with open(LOG_FILE, 'r') as f:
        # Seek to end to avoid parsing old logs
        f.seek(0, os.SEEK_END)
        
        for line in follow(f):
            data = parse_line(line)
            if data:
                if data['type'] == 'connect':
                    request_ips[data['id']] = data['ip']
                elif data['type'] == 'auth':
                    req_id = data['id']
                    if req_id in request_ips:
                        ip = request_ips[req_id]
                        user = data['user']
                        user_ips[user].append((time.time(), ip))
                        # print(f"User {user} connected from {ip}")
            
            enforce_limits()

if __name__ == "__main__":
    main()
