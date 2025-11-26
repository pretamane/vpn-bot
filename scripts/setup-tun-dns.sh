#!/bin/bash
# Wait for TUN interface to be up
for i in {1..10}; do
    if ip link show tun0 >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Configure DNS for TUN interface
if ip link show tun0 >/dev/null 2>&1; then
    # Set DNS servers
    resolvectl dns tun0 1.1.1.1 8.8.8.8
    
    # Enable DNS-over-TLS (opportunistic mode for reliability)
    resolvectl dnsovertls tun0 opportunistic
    
    # Set as default route
    resolvectl default-route tun0 true
    
    # Route all domains through this interface
    resolvectl domain tun0 '~.'
    
    # Flush DNS caches to avoid stale entries
    resolvectl flush-caches
    
    echo "TUN DNS configured: 1.1.1.1, 8.8.8.8 (DoT: opportunistic)"
else
    echo "TUN interface not found"
    exit 1
fi
