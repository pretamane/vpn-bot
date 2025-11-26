#!/bin/bash
# Clean up policy routing rules (SingBox auto_route leftovers)
for p in 9010 9003 9002 9001 9000; do
    while ip rule show | awk '{print $1}' | sed 's/://' | grep -qx $p; do
        ip rule del pref $p || true
    done
done

# Attempt to revert DNS settings for tun0
if ip link show tun0 >/dev/null 2>&1; then
    resolvectl revert tun0
fi

# Flush DNS caches to ensure we don't hold onto stale records
resolvectl flush-caches
