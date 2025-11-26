#!/bin/bash
# RESTORED: Last working configuration
# This setup WORKS but will block the agent's responses while active

echo "🚀 Starting Mumbai VPN..."

# Start SingBox
systemctl --user start sing-box

# Wait for tun0
echo "⏳ Waiting for tun0..."
while ! ip link show tun0 >/dev/null 2>&1; do
  sleep 1
done
echo "✅ tun0 is up"

# Apply manual routing
sudo ip rule del fwmark 5555 2>/dev/null
sudo ip rule del from all lookup 100 2>/dev/null
sudo ip route flush table 100 2>/dev/null

sudo ip route add default dev tun0 table 100
sudo ip rule add fwmark 5555 lookup main priority 500
sudo ip rule add from all lookup 100 priority 1000

echo "✅ Manual routing applied"
echo ""
echo "═══════════════════════════════════"
echo "VPN IS NOW ACTIVE (System-Wide)"
echo "═══════════════════════════════════"
echo ""
echo "⚠️  WARNING: Agent will stop responding while VPN is on"
echo ""
echo "To verify VPN is working:"
echo "  curl -s https://ipapi.is/json | jq .ip"
echo "  # Should show: 43.205.90.213 (Mumbai)"
echo ""
echo "To test browsing:"
echo "  Open Chrome/Firefox and visit facebook.com"
echo ""
echo "To stop VPN:"
echo "  sbox down"
echo ""
