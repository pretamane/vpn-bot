#!/bin/bash
# NetworkManager dispatcher script to reapply TUN DNS when network changes

# Only run for interface up events
if [[ "$2" != "up" ]]; then
    exit 0
fi

# Only run for the primary network interface (wlp1s0)
if [[ "$1" != "wlp1s0" ]]; then
    exit 0
fi

# Wait a moment for the interface to be fully up
sleep 2

# Check if sing-box is running
if ! systemctl --user is-active sing-box >/dev/null 2>&1; then
    exit 0
fi

# Get the path to sbox
SBOX="$HOME/bin/sbox"

# Reapply DNS settings
"$SBOX" dns apply

exit 0
