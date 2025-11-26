# Monitoring Guide - Users, Keys, and Connections

## Database: All Generated Keys

**View all users and their UUIDs**:
```bash
ssh ubuntu@server
sqlite3 /home/ubuntu/vpn-bot/db/vpn_bot.db "
SELECT 
    uuid,
    telegram_id,
    username,
    data_limit_gb,
    is_active,
    created_at,
    expiry_date
FROM users
ORDER BY created_at DESC;
"
```

**See today's bandwidth usage**:
```bash
sqlite3 /home/ubuntu/vpn-bot/db/vpn_bot.db "
SELECT 
    u.username,
    u.uuid,
    ROUND(l.bytes_used / (1024.0*1024*1024), 2) as gb_used_today,
    u.data_limit_gb,
    CASE WHEN u.is_active THEN 'Active' ELSE 'Blocked' END as status
FROM users u
LEFT JOIN usage_logs l ON u.uuid = l.uuid AND l.date = DATE('now')
ORDER BY gb_used_today DESC;
"
```

## Sing-Box: Connection Logs

**Live connection monitoring**:
```bash
# Watch connections in real-time
sudo journalctl -u sing-box -f

# See recent connections
sudo journalctl -u sing-box -n 100 --no-pager

# Search for specific UUID
sudo journalctl -u sing-box | grep "8b783a86-4926"
```

**Access log file** (if enabled):
```bash
sudo tail -f /var/log/singbox/access.log
```

## Watchdog: Bandwidth Tracking

**See what watchdog is doing**:
```bash
# Live monitoring
sudo journalctl -u watchdog -f

# Recent activity
sudo journalctl -u watchdog -n 50 --no-pager

# Users who hit limits
sudo journalctl -u watchdog | grep "exceeded limit"
```

## Currently Connected Users

**Method 1: Check active connections via netstat**:
```bash
# Shadowsocks connections (port 9388)
sudo netstat -tnp | grep :9388

# VLESS connections (port 8443)
sudo netstat -tnp | grep :8443

# Example output:
# tcp  0  0  43.205.90.213:9388  124.58.12.34:51234  ESTABLISHED  161555/sing-box
#                                  ^client IP
```

**Method 2: Sing-Box API Stats** (query via watchdog):
```bash
# Get stats for specific user
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/ubuntu/vpn-bot/v2ray-proto')
import grpc
import command_pb2
import command_pb2_grpc

channel = grpc.insecure_channel('127.0.0.1:10085')
stub = command_pb2_grpc.StatsServiceStub(channel)

# Query all stats
request = command_pb2.QueryStatsRequest(pattern="", reset=False)
response = stub.QueryStats(request, timeout=5)
for stat in response.stat:
    print(f"{stat.name}: {stat.value} bytes")
EOF
```

## Quick Monitoring Commands

**One-liner: See all active users with usage**:
```bash
ssh ubuntu@server "sqlite3 /home/ubuntu/vpn-bot/db/vpn_bot.db \"SELECT username, ROUND(bytes_used/(1024.0*1024*1024),2) as GB FROM usage_logs JOIN users ON usage_logs.uuid=users.uuid WHERE date=DATE('now') AND bytes_used > 0;\""
```

**One-liner: Count active connections**:
```bash
ssh ubuntu@server "sudo netstat -tn | grep -E ':(9388|8443)' | grep ESTABLISHED | wc -l"
```

**One-liner: List all generated UUIDs**:
```bash
ssh ubuntu@server "sqlite3 /home/ubuntu/vpn-bot/db/vpn_bot.db 'SELECT uuid FROM users;'"
```

## Web Dashboard (Future Enhancement)

For easier monitoring, you could build a simple web dashboard:
- Flask/FastAPI app reading from SQLite
- Shows: Active users, bandwidth graphs, connection history
- Admin panel to block/unblock users

Would you like me to create this?
