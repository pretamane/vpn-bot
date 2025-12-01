#!/bin/bash
# VPN Troubleshooting Suite - Run diagnostics on VLESS issues

echo "=========================================="
echo "VPN TROUBLESHOOTING DIAGNOSTICS"
echo "=========================================="
echo ""

# 1. Check sing-box status
echo "[1] Sing-box Service Status"
echo "----------------------------------------"
sudo systemctl status sing-box --no-pager | head -15
echo ""

# 2. Check recent VLESS errors
echo "[2] Recent VLESS Errors (last 50 lines)"
echo "----------------------------------------"
sudo tail -50 /var/log/singbox/access.log | grep -i "error\|vless" | tail -20
echo ""

# 3. Count active connections
echo "[3] Active Connections on Port 443"
echo "----------------------------------------"
CONN_COUNT=$(ss -tn | grep ":443 " | wc -l)
echo "Total connections: $CONN_COUNT"
if [ $CONN_COUNT -gt 100 ]; then
    echo "⚠️  WARNING: High connection count (>100)"
fi
echo ""

# 4. Check config vs database sync
echo "[4] Config vs Database Sync"
echo "----------------------------------------"
CONFIG_VLESS=$(sudo cat /etc/sing-box/config.json | jq -r '.inbounds[0].users | length')
DB_VLESS=$(sqlite3 /home/ubuntu/vpn-bot/db/vpn_bot.db "SELECT COUNT(*) FROM users WHERE protocol='vless' AND is_active=1")
echo "VLESS users in config: $CONFIG_VLESS"
echo "VLESS users in database: $DB_VLESS"
if [ "$CONFIG_VLESS" != "$DB_VLESS" ]; then
    echo "⚠️  MISMATCH DETECTED!"
    echo "Missing UUIDs:"
    sqlite3 /home/ubuntu/vpn-bot/db/vpn_bot.db "SELECT uuid FROM users WHERE protocol='vless' AND is_active=1" > /tmp/db_uuids.txt
    sudo cat /etc/sing-box/config.json | jq -r '.inbounds[0].users[].uuid' > /tmp/config_uuids.txt
    comm -23 <(sort /tmp/db_uuids.txt) <(sort /tmp/config_uuids.txt) | head -5
fi
echo ""

# 5. Server resources
echo "[5] Server Resources"
echo "----------------------------------------"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "Memory: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"
echo "Disk: $(df -h / | awk 'NR==2{print $5}')"
echo ""

# 6. Network test
echo "[6] Network Latency"
echo "----------------------------------------"
ping -c 3 1.1.1.1 | tail -2
echo ""

# 7. Recent key generation
echo "[7] Recently Generated Keys"
echo "----------------------------------------"
sqlite3 /home/ubuntu/vpn-bot/db/vpn_bot.db "SELECT uuid, username, protocol, datetime(created_at) FROM users WHERE created_at > datetime('now', '-1 hour') ORDER BY created_at DESC LIMIT 5"
echo ""

# 8. Bot service status
echo "[8] VPN Bot Status"
echo "----------------------------------------"
sudo systemctl status vpn-bot --no-pager | head -10
echo ""

echo "=========================================="
echo "DIAGNOSTICS COMPLETE"
echo "=========================================="
