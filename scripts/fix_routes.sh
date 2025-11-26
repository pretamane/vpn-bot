#!/bin/bash
# fix_routes.sh - Manual Policy Routing for SingBox

# 1. Flush old rules to be clean
sudo ip rule del fwmark 5555 2>/dev/null
sudo ip rule del from all lookup 100 2>/dev/null
sudo ip route flush table 100 2>/dev/null

# 2. Add default route to table 100 via TUN
# Wait for tun0 to be up
echo "Waiting for tun0..."
while ! ip link show tun0 >/dev/null 2>&1; do
  sleep 1
done
echo "tun0 is up."

sudo ip route add default dev tun0 table 100

# 3. Add Exception: Marked packets (SingBox VPN traffic) go to MAIN table
sudo ip rule add fwmark 5555 lookup main priority 500

# 4. Add Catch-All: Everything else goes to TABLE 100 (TUN)
sudo ip rule add from all lookup 100 priority 1000

# 5. Verify
ip rule show
ip route show table 100
echo "Manual routing applied."
