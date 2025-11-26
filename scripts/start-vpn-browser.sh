#!/bin/bash
# Myanmar VPN - Browser Launcher
# Automatically starts VPN and launches browser with proxy

set -e

echo "======================================"
echo "Myanmar VPN - Browser Launcher"
echo "======================================"

# Check if SingBox client is already running
if pgrep -f "sing-box.*client-test" > /dev/null; then
    echo "✅ VPN client already running"
else
    echo "🚀 Starting VPN client..."
    /usr/local/bin/sing-box run -c /home/guest/.gemini/antigravity/scratch/client-test.json > /tmp/vpn-client.log 2>&1 &
    sleep 3
    
    if pgrep -f "sing-box.*client-test" > /dev/null; then
        echo "✅ VPN client started"
    else
        echo "❌ Failed to start VPN client"
        echo "Check logs: /tmp/vpn-client.log"
        exit 1
    fi
fi

# Test connection
echo "🔍 Testing VPN connection..."
if timeout 5 curl -x socks5h://127.0.0.1:10808 -s https://api.ipify.org | grep -q "43.205.90.213"; then
    echo "✅ VPN connection working - IP: 43.205.90.213 (AWS India)"
else
    echo "⚠️  VPN may not be working correctly"
fi

echo ""
echo "======================================"
echo "Launching Browser..."
echo "======================================"

# Detect and launch browser
if command -v firefox &> /dev/null; then
    echo "🌐 Opening Firefox with VPN proxy..."
    firefox &
    echo ""
    echo "📋 Configure Firefox manually:"
    echo "   Settings → Network Settings → Manual proxy"
    echo "   SOCKS Host: 127.0.0.1, Port: 10808"
    echo "   ✅ Enable 'Proxy DNS when using SOCKS v5'"
elif command -v google-chrome &> /dev/null; then
    echo "🌐 Opening Chrome with VPN proxy..."
    google-chrome --proxy-server="socks5://127.0.0.1:10808" &
elif command -v chromium-browser &> /dev/null; then
    echo "🌐 Opening Chromium with VPN proxy..."
    chromium-browser --proxy-server="socks5://127.0.0.1:10808" &
else
    echo "❌ No browser found (firefox/chrome/chromium)"
    echo "   Please install a browser and configure manually"
    exit 1
fi

echo ""
echo "======================================"
echo "VPN Active - Test it:"
echo "======================================"
echo "1. Visit: https://api.ipify.org"
echo "   Should show: 43.205.90.213"
echo ""
echo "2. Visit: https://www.facebook.com"
echo "   Should load (censorship bypassed!)"
echo ""
echo "To stop VPN: pkill -f 'sing-box.*client-test'"
echo "======================================"
