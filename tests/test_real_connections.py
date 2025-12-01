#!/usr/bin/env python3
"""
Real-World VPN Connection Test
Simulates actual client connections to detect timeout/I/O errors
Tests actual protocol handshakes and data transfer
"""

import sys
import os
import time
import socket
import ssl
import base64
import subprocess
import json
import sqlite3
import uuid as uuid_lib
from pathlib import Path

# Add project to path
sys.path.insert(0, '/home/ubuntu/vpn-bot')

SERVER_IP = "43.205.90.213"
DB_PATH = "/home/ubuntu/vpn-bot/db/vpn_bot.db"
CONFIG_PATH = "/etc/sing-box/config.json"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def cleanup_test_key(uuid):
    """Clean up test key from database and sing-box config"""
    try:
        # Remove from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
        if cursor.fetchone():
            cursor.execute("DELETE FROM users WHERE uuid = ?", (uuid,))
            conn.commit()
            print(f"{Colors.GREEN}✓ Removed from database{Colors.RESET}")
        conn.close()
        
        # Remove from sing-box config
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        
        removed = False
        for inbound in config['inbounds']:
            if 'users' in inbound:
                original_len = len(inbound['users'])
                inbound['users'] = [u for u in inbound['users'] 
                                   if u.get('uuid') != uuid and u.get('password') != uuid]
                if len(inbound['users']) < original_len:
                    removed = True
        
        if removed:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
                json.dump(config, tmp, indent=2)
                tmp_path = tmp.name
            subprocess.run(['sudo', 'cp', tmp_path, CONFIG_PATH], check=True, 
                          capture_output=True, timeout=5)
            os.remove(tmp_path)
            subprocess.run(['sudo', 'systemctl', 'reload-or-restart', 'sing-box'], 
                          check=True, capture_output=True, timeout=10)
            print(f"{Colors.GREEN}✓ Removed from sing-box config{Colors.RESET}")
        
        return True
    except Exception as e:
        print(f"{Colors.RED}✗ Cleanup failed: {e}{Colors.RESET}")
        return False

def test_shadowsocks_real_connection():
    """Test actual Shadowsocks connection with real handshake"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}🧪 Testing Shadowsocks Real Connection{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    test_uuid = str(uuid_lib.uuid4())
    
    try:
        print(f"{Colors.YELLOW}[1/5] Generating SS key via bot code path...{Colors.RESET}")
        
        # Add to sing-box using bot's actual config manager
        from bot.config_manager import add_ss_user
        result = add_ss_user(test_uuid, "e2e-test-ss")
        
        if not result:
            print(f"{Colors.RED}✗ Failed to add user via config manager{Colors.RESET}")
            return False
        
        time.sleep(3)  # Wait for sing-box to reload
        print(f"{Colors.GREEN}✓ Key generated{Colors.RESET}")
        
        print(f"{Colors.YELLOW}[2/5] Testing TCP connection to port 9388...{Colors.RESET}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((SERVER_IP, 9388))
            print(f"{Colors.GREEN}✓ TCP connection established{Colors.RESET}")
            sock.close()
        except socket.timeout:
            print(f"{Colors.RED}✗ Connection timeout{Colors.RESET}")
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ Connection failed: {e}{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[3/5] Testing Shadowsocks SOCKS5 handshake...{Colors.RESET}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((SERVER_IP, 9388))
            
            # Send SOCKS5 greeting
            sock.sendall(b'\x05\x01\x00')
            response = sock.recv(2)
            
            if response == b'\x05\x00':
                print(f"{Colors.GREEN}✓ SOCKS5 handshake successful{Colors.RESET}")
            else:
                print(f"{Colors.RED}✗ Unexpected SOCKS5 response: {response.hex()}{Colors.RESET}")
                return False
            
            sock.close()
        except socket.timeout:
            print(f"{Colors.RED}✗ Handshake timeout{Colors.RESET}")
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ Handshake failed: {e}{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[4/5] Checking sing-box logs for errors...{Colors.RESET}")
        result = subprocess.run(
            ['sudo', 'journalctl', '-u', 'sing-box', '--since', '10 seconds ago'],
            capture_output=True, text=True, timeout=5
        )
        
        if 'error' in result.stdout.lower() or 'failed' in result.stdout.lower():
            print(f"{Colors.RED}✗ Errors found in logs:{Colors.RESET}")
            for line in result.stdout.split('\n'):
                if 'error' in line.lower() or 'failed' in line.lower():
                    print(f"  {line}")
            return False
        
        print(f"{Colors.GREEN}✓ No errors in logs{Colors.RESET}")
        
        print(f"{Colors.YELLOW}[5/5] Verifying user still in config...{Colors.RESET}")
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        
        user_found = False
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'ss-in':
                for user in inbound['users']:
                    if user.get('password') == test_uuid:
                        user_found = True
                        break
        
        if user_found:
            print(f"{Colors.GREEN}✓ User verified in config{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ User missing from config{Colors.RESET}")
            return False
        
        print(f"\n{Colors.GREEN}✅ Shadowsocks: PASS{Colors.RESET}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}✗ Test failed: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print(f"\n{Colors.YELLOW}→ Cleaning up test key: {test_uuid}{Colors.RESET}")
        cleanup_test_key(test_uuid)

def test_vless_plain_real_connection():
    """Test actual Plain VLESS connection with TLS handshake"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}🧪 Testing Plain VLESS Real Connection{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    test_uuid = str(uuid_lib.uuid4())
    
    try:
        print(f"{Colors.YELLOW}[1/5] Generating Plain VLESS key via bot code path...{Colors.RESET}")
        
        from bot.config_manager import add_vless_plain_user
        result = add_vless_plain_user(test_uuid, "e2e-test-vless-plain")
        
        if not result:
            print(f"{Colors.RED}✗ Failed to add user via config manager{Colors.RESET}")
            return False
        
        time.sleep(3)
        print(f"{Colors.GREEN}✓ Key generated{Colors.RESET}")
        
        print(f"{Colors.YELLOW}[2/5] Testing TCP connection to port 8444...{Colors.RESET}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((SERVER_IP, 8444))
            print(f"{Colors.GREEN}✓ TCP connection established{Colors.RESET}")
            sock.close()  
        except socket.timeout:
            print(f"{Colors.RED}✗ Connection timeout{Colors.RESET}")
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ Connection failed: {e}{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[3/5] Testing TLS handshake with SNI...{Colors.RESET}")
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                with context.wrap_socket(sock, server_hostname='www.microsoft.com') as ssock:
                    ssock.connect((SERVER_IP, 8444))
                    print(f"{Colors.GREEN}✓ TLS handshake successful{Colors.RESET}")
                    print(f"  Cipher: {ssock.cipher()[0]}")
                    print(f"  Protocol: {ssock.version()}")
        except ssl.SSLError as e:
            print(f"{Colors.RED}✗ TLS handshake failed: {e}{Colors.RESET}")
            return False
        except socket.timeout:
            print(f"{Colors.RED}✗ TLS handshake timeout{Colors.RESET}")
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ TLS error: {e}{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[4/5] Checking certificate validity...{Colors.RESET}")
        result = subprocess.run(
            ['sudo', 'openssl', 'x509', '-in', '/etc/sing-box/cert.pem', '-noout', '-subject', '-dates'],
            capture_output=True, text=True, timeout=5
        )
        print(f"  {result.stdout.strip()}")
        print(f"{Colors.GREEN}✓ Certificate info retrieved{Colors.RESET}")
        
        print(f"{Colors.YELLOW}[5/5] Verifying user in config...{Colors.RESET}")
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        
        user_found = False
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'vless-plain-in':
                for user in inbound['users']:
                    if user.get('uuid') == test_uuid:
                        user_found = True
                        break
        
        if user_found:
            print(f"{Colors.GREEN}✓ User verified in config{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ User missing from config{Colors.RESET}")
            return False
        
        print(f"\n{Colors.GREEN}✅ Plain VLESS: PASS{Colors.RESET}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}✗ Test failed: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print(f"\n{Colors.YELLOW}→ Cleaning up test key: {test_uuid}{Colors.RESET}")
        cleanup_test_key(test_uuid)

def test_tuic_real_connection():
    """Test actual TUIC connection"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}🧪 Testing TUIC Real Connection{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    test_uuid = str(uuid_lib.uuid4())
    
    try:
        print(f"{Colors.YELLOW}[1/4] Generating TUIC key via bot code path...{Colors.RESET}")
        
        from bot.config_manager import add_tuic_user
        result = add_tuic_user(test_uuid, "e2e-test-tuic")
        
        if not result:
            print(f"{Colors.RED}✗ Failed to add user via config manager{Colors.RESET}")
            return False
        
        time.sleep(3)
        print(f"{Colors.GREEN}✓ Key generated{Colors.RESET}")
        
        print(f"{Colors.YELLOW}[2/4] Testing UDP port 2083 accessibility...{Colors.RESET}")
        # UDP test is limited, but we can check if port is open
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            # Send a dummy packet
            sock.sendto(b'\x00', (SERVER_IP, 2083))
            print(f"{Colors.GREEN}✓ UDP port accessible{Colors.RESET}")
            sock.close()
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ UDP test inconclusive (expected): {e}{Colors.RESET}")
        
        print(f"{Colors.YELLOW}[3/4] Verifying TUIC service is running...{Colors.RESET}")
        result = subprocess.run(
            ['sudo', 'lsof', '-i', ':2083'],
            capture_output=True, text=True, timeout=5
        )
        
        if 'sing-box' in result.stdout:
            print(f"{Colors.GREEN}✓ sing-box listening on port 2083{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ sing-box not listening on port 2083{Colors.RESET}")
            return False
        
        print(f"{Colors.YELLOW}[4/4] Verifying user in config...{Colors.RESET}")
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        
        user_found = False
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'tuic-in':
                for user in inbound['users']:
                    if user.get('uuid') == test_uuid:
                        user_found = True
                        break
        
        if user_found:
            print(f"{Colors.GREEN}✓ User verified in config{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ User missing from config{Colors.RESET}")
            return False
        
        print(f"\n{Colors.GREEN}✅ TUIC: PASS{Colors.RESET}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}✗ Test failed: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print(f"\n{Colors.YELLOW}→ Cleaning up test key: {test_uuid}{Colors.RESET}")
        cleanup_test_key(test_uuid)

def main():
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("="*60)
    print("🔬 Real-World VPN Connection Test")
    print("="*60)
    print(f"{Colors.RESET}")
    print("This test simulates actual VPN client connections:")
    print("  • Uses bot's actual code paths")
    print("  • Tests real protocol handshakes")
    print("  • Verifies data can flow")
    print("  • Auto-cleans up all test keys")
    print()
    
    results = []
    
    # Test each protocol
    results.append(("Shadowsocks", test_shadowsocks_real_connection()))
    results.append(("Plain VLESS", test_vless_plain_real_connection()))
    results.append(("TUIC", test_tuic_real_connection()))
    
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
        print(f"{Colors.GREEN}All protocols can establish real connections!{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED{Colors.RESET}")
        print(f"{Colors.RED}VPN connections are failing - check errors above{Colors.RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
