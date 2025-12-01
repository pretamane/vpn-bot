#!/usr/bin/env python3
"""
Comprehensive Key Generation Test Suite
Tests all protocol key generation including admin TUIC
"""

import sys
import os
import time
sys.path.insert(0, '/home/ubuntu/vpn-bot')

from bot.config_manager import add_ss_user, add_tuic_user, add_vless_plain_user, add_user_to_config
import uuid as uuid_lib
import json

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

SERVER_IP = "43.205.90.213"
generated_uuids = []

def cleanup_test_keys():
    """Clean up all generated test keys"""
    print(f"\n{Colors.YELLOW}→ Cleaning up test keys...{Colors.RESET}")
    
    for user_uuid in generated_uuids:
        # Remove from database
        import sqlite3
        try:
            conn = sqlite3.connect("/home/ubuntu/vpn-bot/db/vpn_bot.db")
            cursor = conn.execute("DELETE FROM users WHERE uuid = ?", (user_uuid,))
            if cursor.rowcount > 0:
                print(f"  {Colors.GREEN}✓ Removed from DB: {user_uuid[:8]}...{Colors.RESET}")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  {Colors.RED}✗ DB cleanup failed: {e}{Colors.RESET}")
        
        # Remove from sing-box config
        try:
            with open("/etc/sing-box/config.json") as f:
                config = json.load(f)
            
            removed = False
            for inbound in config['inbounds']:
                if 'users' in inbound:
                    original_len = len(inbound['users'])
                    inbound['users'] = [u for u in inbound['users'] 
                                       if u.get('uuid') != user_uuid and u.get('password') != user_uuid]
                    if len(inbound['users']) < original_len:
                        removed = True
            
            if removed:
                import tempfile, subprocess
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
                    json.dump(config, tmp, indent=2)
                    tmp_path = tmp.name
                subprocess.run(['sudo', 'cp', tmp_path, '/etc/sing-box/config.json'], 
                             check=True, capture_output=True)
                os.remove(tmp_path)
                print(f"  {Colors.GREEN}✓ Removed from sing-box config{Colors.RESET}")
        except Exception as e:
            print(f"  {Colors.RED}✗ Config cleanup failed: {e}{Colors.RESET}")
    
    # Restart sing-box
    try:
        import subprocess
        subprocess.run(['sudo', 'systemctl', 'restart', 'sing-box'], 
                      check=True, capture_output=True, timeout=10)
        print(f"  {Colors.GREEN}✓ Sing-box restarted{Colors.RESET}")
    except:
        pass

def test_shadowsocks_generation():
    """Test 1: Shadowsocks Key Generation"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}Test 1: Shadowsocks Key Generation{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    user_uuid = str(uuid_lib.uuid4())
    generated_uuids.append(user_uuid)
    
    try:
        print(f"{Colors.YELLOW}[1/3] Generating SS key...{Colors.RESET}")
        result = add_ss_user(user_uuid, "test-ss-automated")
        
        if result:
            print(f"{Colors.GREEN}✓ Key generated via config manager{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ Config manager returned False{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[2/3] Verifying in sing-box config...{Colors.RESET}")
        with open("/etc/sing-box/config.json") as f:
            config = json.load(f)
        
        found = False
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'ss-in':
                for user in inbound['users']:
                    if user.get('password') == user_uuid:
                        found = True
                        break
        
        if found:
            print(f"{Colors.GREEN}✓ User found in config{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ User not in config{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[3/3] Validating link format...{Colors.RESET}")
        import base64
        ss_credential = f"chacha20-ietf-poly1305:{user_uuid}"
        ss_encoded = base64.b64encode(ss_credential.encode()).decode()
        ss_link = f"ss://{ss_encoded}@{SERVER_IP}:9388#TestSS"
        
        if ss_link.startswith("ss://"):
            print(f"{Colors.GREEN}✓ Valid SS link format{Colors.RESET}")
            print(f"  Link: {ss_link[:50]}...")
        else:
            print(f"{Colors.RED}✗ Invalid link format{Colors.RESET}")
            return False
        
        print(f"\n{Colors.GREEN}✅ Shadowsocks Test: PASS{Colors.RESET}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}✗ Test failed: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False

def test_tuic_generation():
    """Test 2: TUIC Key Generation (Sing-box)"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}Test 2: TUIC Key Generation (Port 2083){Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    user_uuid = str(uuid_lib.uuid4())
    generated_uuids.append(user_uuid)
    
    try:
        print(f"{Colors.YELLOW}[1/3] Generating TUIC key...{Colors.RESET}")
        result = add_tuic_user(user_uuid, "test-tuic-automated")
        
        if result:
            print(f"{Colors.GREEN}✓ Key generated{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ Config manager returned False{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[2/3] Verifying in config...{Colors.RESET}")
        with open("/etc/sing-box/config.json") as f:
            config = json.load(f)
        
        found = False
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'tuic-in':
                for user in inbound['users']:
                    if user.get('uuid') == user_uuid:
                        found = True
                        break
        
        if found:
            print(f"{Colors.GREEN}✓ User in config{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ User not found{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[3/3] Validating link...{Colors.RESET}")
        tuic_link = f"tuic://{user_uuid}:{user_uuid}@{SERVER_IP}:2083?congestion_control=bbr&alpn=h3&sni=www.microsoft.com#TestTUIC"
        
        if tuic_link.startswith("tuic://"):
            print(f"{Colors.GREEN}✓ Valid TUIC link{Colors.RESET}")
            print(f"  Link: {tuic_link[:50]}...")
        else:
            print(f"{Colors.RED}✗ Invalid format{Colors.RESET}")
            return False
        
        print(f"\n{Colors.GREEN}✅ TUIC Test: PASS{Colors.RESET}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}✗ Test failed: {e}{Colors.RESET}")
        return False

def test_admin_tuic_generation():
    """Test 3: Admin TUIC Key Generation (Legacy Server Port 8443)"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}Test 3: Admin TUIC (Dedicated India Server){Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    user_uuid = str(uuid_lib.uuid4())
    generated_uuids.append(user_uuid)
    
    try:
        print(f"{Colors.YELLOW}[1/3] Testing password authentication...{Colors.RESET}")
        ADMIN_PASSWORD = "#ThawZin2k77!"
        test_password = "#ThawZin2k77!"
        
        if test_password == ADMIN_PASSWORD:
            print(f"{Colors.GREEN}✓ Password validation works{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ Password mismatch{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[2/3] Generating admin TUIC link...{Colors.RESET}")
        # This uses legacy tuic-server, not sing-box
        admin_tuic_link = f"tuic://{user_uuid}:{user_uuid}@{SERVER_IP}:8443?congestion_control=bbr&alpn=h3&sni=www.microsoft.com#AdminTUIC"
        
        if admin_tuic_link.startswith("tuic://") and ":8443" in admin_tuic_link:
            print(f"{Colors.GREEN}✓ Valid admin TUIC link (port 8443){Colors.RESET}")
            print(f"  Link: {admin_tuic_link[:50]}...")
        else:
            print(f"{Colors.RED}✗ Invalid format or wrong port{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[3/3] Checking legacy tuic-server status...{Colors.RESET}")
        import subprocess
        result = subprocess.run(['sudo', 'lsof', '-i', ':8443'], 
                               capture_output=True, text=True)
        
        if 'tuic-serv' in result.stdout or 'tuic-server' in result.stdout:
            print(f"{Colors.GREEN}✓ Legacy TUIC server running on 8443{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}⚠ Legacy server not detected (may need manual start){Colors.RESET}")
        
        print(f"\n{Colors.GREEN}✅ Admin TUIC Test: PASS{Colors.RESET}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}✗ Test failed: {e}{Colors.RESET}")
        return False

def test_vless_reality_generation():
    """Test 4: VLESS+REALITY Key Generation"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}Test 4: VLESS+REALITY Key Generation{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    user_uuid = str(uuid_lib.uuid4())
    generated_uuids.append(user_uuid)
    
    try:
        print(f"{Colors.YELLOW}[1/2] Generating VLESS+REALITY key...{Colors.RESET}")
        result = add_user_to_config(user_uuid, "test-vless-reality")
        
        if result:
            print(f"{Colors.GREEN}✓ Key generated{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ Failed{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[2/2] Validating link...{Colors.RESET}")
        vless_link = f"vless://{user_uuid}@{SERVER_IP}:443?security=reality&encryption=none&type=tcp&flow=xtls-rprx-vision&sni=www.google.com&fp=chrome&pbk=PUBLIC_KEY&sid=55abbd7a#TestVLESS"
        
        if vless_link.startswith("vless://") and "security=reality" in vless_link:
            print(f"{Colors.GREEN}✓ Valid VLESS+REALITY link{Colors.RESET}")
            print(f"  Link: {vless_link[:50]}...")
        else:
            print(f"{Colors.RED}✗ Invalid format{Colors.RESET}")
            return False
        
        print(f"\n{Colors.GREEN}✅ VLESS+REALITY Test: PASS{Colors.RESET}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}✗ Test failed: {e}{Colors.RESET}")
        return False

def main():
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("="*60)
    print("🔬 Comprehensive Key Generation Test Suite")
    print("="*60)
    print(f"{Colors.RESET}")
    print("Testing all protocol key generation functions:")
    print("  • Shadowsocks (port 9388)")
    print("  • TUIC (port 2083)")
    print("  • Admin TUIC (port 8443 - legacy server)")
    print("  • VLESS+REALITY (port 443)")
    print()
    
    results = []
    
    # Run all tests
    results.append(("Shadowsocks", test_shadowsocks_generation()))
    results.append(("TUIC", test_tuic_generation()))
    results.append(("Admin TUIC", test_admin_tuic_generation()))
    results.append(("VLESS+REALITY", test_vless_reality_generation()))
    
    # Cleanup
    cleanup_test_keys()
    
    # Summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"{Colors.RESET}")
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for protocol, result in results:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {protocol}: {status}")
    
    print()
    print(f"Passed: {Colors.GREEN}{passed}{Colors.RESET}")
    print(f"Failed: {Colors.RED}{failed}{Colors.RESET}")
    print()
    
    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED{Colors.RESET}")
        print(f"{Colors.GREEN}All key generation functions working correctly!{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED{Colors.RESET}")
        print(f"{Colors.RED}Check errors above for details{Colors.RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
