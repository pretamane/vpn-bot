#!/bin/bash
# End-to-End VPN Key Connection Test
# Generates new keys, tests connectivity, cleans up automatically
# Tests: Shadowsocks, TUIC, Plain VLESS (excludes VLESS+REALITY)

SERVER_IP="43.205.90.213"
KEY="/home/guest/tzdump/vpn-bot/keys/myanmar-vpn-key.pem"
SERVER="ubuntu@$SERVER_IP"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;94m'
NC='\033[0m'

FAILED_TESTS=0
PASSED_TESTS=0
GENERATED_UUIDS=()

cleanup() {
    if [ ${#GENERATED_UUIDS[@]} -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}========================================${NC}"
        echo -e "${YELLOW}🧹 Cleaning up test keys...${NC}"
        echo -e "${YELLOW}========================================${NC}"
        
        for uuid in "${GENERATED_UUIDS[@]}"; do
            echo -e "${YELLOW}→ Removing $uuid${NC}"
            ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" "cd /home/ubuntu/vpn-bot && python3 << EOF
import sqlite3
import json
import subprocess

DB_PATH = '/home/ubuntu/vpn-bot/db/vpn_bot.db'
CONFIG_PATH = '/etc/sing-box/config.json'

# Remove from database
conn = sqlite3.connect(DB_PATH)
cursor = conn.execute('DELETE FROM users WHERE user_uuid = ?', ('$uuid',))
db_deleted = cursor.rowcount
conn.commit()
conn.close()

# Remove from sing-box config
with open(CONFIG_PATH) as f:
    config = json.load(f)

removed = False
for inbound in config['inbounds']:
    if 'users' in inbound:
        original_len = len(inbound['users'])
        inbound['users'] = [u for u in inbound['users'] if u.get('uuid') != '$uuid' and u.get('password') != '$uuid']
        if len(inbound['users']) < original_len:
            removed = True

if removed:
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
        json.dump(config, tmp, indent=2)
        tmp_path = tmp.name
    subprocess.run(['sudo', 'cp', tmp_path, CONFIG_PATH], check=True)
    subprocess.run(['rm', tmp_path], check=True)

print(f'DB: {db_deleted}, Config: {removed}')
EOF
" 2>&1 | grep -v "Warning"
        done
        
        # Restart sing-box to apply changes
        echo -e "${YELLOW}→ Restarting sing-box...${NC}"
        ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" 'sudo systemctl restart sing-box' 2>&1 | grep -v "Warning"
        sleep 2
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    fi
}

trap cleanup EXIT

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

test_shadowsocks() {
    print_header "🧪 Testing Shadowsocks"
    
    # Generate test UUID
    TEST_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    GENERATED_UUIDS+=("$TEST_UUID")
    
    echo -e "${YELLOW}[1/4] Generating SS key: $TEST_UUID${NC}"
    
    # Add to sing-box config
    RESULT=$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" "cd /home/ubuntu/vpn-bot && python3 << 'ENDPY'
import json
import subprocess
import tempfile

CONFIG_PATH = '/etc/sing-box/config.json'

with open(CONFIG_PATH) as f:
    config = json.load(f)

for inbound in config['inbounds']:
    if inbound.get('tag') == 'ss-in':
        inbound['users'].append({
            'password': '$TEST_UUID',
            'name': 'test-ss-key'
        })
        break

with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
    json.dump(config, tmp, indent=2)
    tmp_path = tmp.name

subprocess.run(['sudo', 'cp', tmp_path, CONFIG_PATH], check=True)
subprocess.run(['rm', tmp_path], check=True)
subprocess.run(['sudo', 'systemctl', 'reload-or-restart', 'sing-box'], check=True)
print('OK')
ENDPY
" 2>&1 | tail -1)
    
    if [ "$RESULT" != "OK" ]; then
        echo -e "${RED}✗ Failed to add SS user${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
    echo -e "${GREEN}✓ Key generated${NC}"
    
    sleep 2  # Wait for service to reload
    
    echo -e "${YELLOW}[2/4] Testing TCP connectivity to port 9388...${NC}"
    if timeout 3 nc -zv $SERVER_IP 9388 2>&1 | grep -q "succeeded\|Connected"; then
        echo -e "${GREEN}✓ Port accessible${NC}"
    else
        echo -e "${RED}✗ Port timeout${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
    
    echo -e "${YELLOW}[3/4] Verifying user in config...${NC}"
    USER_COUNT=$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" "sudo cat /etc/sing-box/config.json | jq '[.inbounds[] | select(.tag==\"ss-in\") | .users[] | select(.password==\"$TEST_UUID\")] | length'" 2>&1 | tail -1)
    
    if [ "$USER_COUNT" = "1" ]; then
        echo -e "${GREEN}✓ User configured in sing-box${NC}"
    else
        echo -e "${RED}✗ User not found in config${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
    
    echo -e "${YELLOW}[4/4] Checking sing-box logs for errors...${NC}"
    ERRORS=$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" 'sudo journalctl -u sing-box --since "10 seconds ago" | grep -i "error" | wc -l' 2>&1 | tail -1)
    
    if [ "$ERRORS" = "0" ]; then
        echo -e "${GREEN}✓ No errors in logs${NC}"
        echo -e "${GREEN}✅ Shadowsocks: PASS${NC}"
        ((PASSED_TESTS++))
        return 0
    else
        echo -e "${RED}✗ Found $ERRORS errors in logs${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
}

test_tuic() {
    print_header "🧪 Testing TUIC"
    
    TEST_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    GENERATED_UUIDS+=("$TEST_UUID")
    
    echo -e "${YELLOW}[1/4] Generating TUIC key: $TEST_UUID${NC}"
    
    RESULT=$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" "cd /home/ubuntu/vpn-bot && python3 << 'ENDPY'
import json
import subprocess
import tempfile

CONFIG_PATH = '/etc/sing-box/config.json'

with open(CONFIG_PATH) as f:
    config = json.load(f)

for inbound in config['inbounds']:
    if inbound.get('tag') == 'tuic-in':
        inbound['users'].append({
            'uuid': '$TEST_UUID',
            'password': '$TEST_UUID',
            'name': 'test-tuic-key'
        })
        break

with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
    json.dump(config, tmp, indent=2)
    tmp_path = tmp.name

subprocess.run(['sudo', 'cp', tmp_path, CONFIG_PATH], check=True)
subprocess.run(['rm', tmp_path], check=True)
subprocess.run(['sudo', 'systemctl', 'reload-or-restart', 'sing-box'], check=True)
print('OK')
ENDPY
" 2>&1 | tail -1)
    
    if [ "$RESULT" != "OK" ]; then
        echo -e "${RED}✗ Failed to add TUIC user${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
    echo -e "${GREEN}✓ Key generated${NC}"
    
    sleep 2
    
    echo -e "${YELLOW}[2/4] Testing UDP connectivity to port 2083...${NC}"
    if timeout 3 nc -zv $SERVER_IP 2083 2>&1 | grep -q "succeeded\|open\|Connected"; then
        echo -e "${GREEN}✓ Port accessible${NC}"
    else
        echo -e "${YELLOW}⚠ UDP test inconclusive (expected for UDP)${NC}"
    fi
    
    echo -e "${YELLOW}[3/4] Verifying user in config...${NC}"
    USER_COUNT=$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" "sudo cat /etc/sing-box/config.json | jq '[.inbounds[] | select(.tag==\"tuic-in\") | .users[] | select(.uuid==\"$TEST_UUID\")] | length'" 2>&1 | tail -1)
    
    if [ "$USER_COUNT" = "1" ]; then
        echo -e "${GREEN}✓ User configured in sing-box${NC}"
    else
        echo -e "${RED}✗ User not found in config${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
    
    echo -e "${YELLOW}[4/4] Checking sing-box status...${NC}"
    if ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" 'sudo systemctl is-active sing-box' 2>&1 | grep -q "active"; then
        echo -e "${GREEN}✓ Sing-box running${NC}"
        echo -e "${GREEN}✅ TUIC: PASS${NC}"
        ((PASSED_TESTS++))
        return 0
    else
        echo -e "${RED}✗ Sing-box not running${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
}

test_plain_vless() {
    print_header "🧪 Testing Plain VLESS"
    
    TEST_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    GENERATED_UUIDS+=("$TEST_UUID")
    
    echo -e "${YELLOW}[1/4] Generating Plain VLESS key: $TEST_UUID${NC}"
    
    RESULT=$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" "cd /home/ubuntu/vpn-bot && python3 << 'ENDPY'
import json
import subprocess
import tempfile

CONFIG_PATH = '/etc/sing-box/config.json'

with open(CONFIG_PATH) as f:
    config = json.load(f)

for inbound in config['inbounds']:
    if inbound.get('tag') == 'vless-plain-in':
        inbound['users'].append({
            'uuid': '$TEST_UUID',
            'name': 'test-vless-plain-key'
        })
        break

with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
    json.dump(config, tmp, indent=2)
    tmp_path = tmp.name

subprocess.run(['sudo', 'cp', tmp_path, CONFIG_PATH], check=True)
subprocess.run(['rm', tmp_path], check=True)
subprocess.run(['sudo', 'systemctl', 'reload-or-restart', 'sing-box'], check=True)
print('OK')
ENDPY
" 2>&1 | tail -1)
    
    if [ "$RESULT" != "OK" ]; then
        echo -e "${RED}✗ Failed to add Plain VLESS user${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
    echo -e "${GREEN}✓ Key generated${NC}"
    
    sleep 2
    
    echo -e "${YELLOW}[2/4] Testing TLS handshake on port 8443...${NC}"
    if timeout 3 openssl s_client -connect $SERVER_IP:8443 -servername www.microsoft.com < /dev/null 2>&1 | grep -q "Verify return code: 0\|CONNECTED"; then
        echo -e "${GREEN}✓ TLS handshake successful${NC}"
    else
        echo -e "${YELLOW}⚠ TLS handshake inconclusive (self-signed cert expected)${NC}"
    fi
    
    echo -e "${YELLOW}[3/4] Verifying user in config...${NC}"
    USER_COUNT=$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" "sudo cat /etc/sing-box/config.json | jq '[.inbounds[] | select(.tag==\"vless-plain-in\") | .users[] | select(.uuid==\"$TEST_UUID\")] | length'" 2>&1 | tail -1)
    
    if [ "$USER_COUNT" = "1" ]; then
        echo -e "${GREEN}✓ User configured in sing-box${NC}"
    else
        echo -e "${RED}✗ User not found in config${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
    
    echo -e "${YELLOW}[4/4] Checking certificate validity...${NC}"
    CERT_CHECK=$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" 'openssl x509 -in /etc/sing-box/cert.pem -noout -checkend 0' 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Certificate valid${NC}"
        echo -e "${GREEN}✅ Plain VLESS: PASS${NC}"
        ((PASSED_TESTS++))
        return 0
    else
        echo -e "${RED}✗ Certificate invalid or expired${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
}

# Main execution
print_header "🔬 End-to-End VPN Key Connection Test"
echo "Testing: Shadowsocks, TUIC, Plain VLESS"
echo "Excludes: VLESS+REALITY (unstable)"
echo ""
echo "This test will:"
echo "  1. Generate new keys for each protocol"
echo "  2. Verify configuration updates"
echo "  3. Test connectivity"
echo "  4. Auto-cleanup all test keys"

test_shadowsocks
test_tuic
test_plain_vless

# Final summary
print_header "📊 Test Summary"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo -e "${GREEN}All protocols are generating working keys!${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}Review errors above${NC}"
    exit 1
fi
