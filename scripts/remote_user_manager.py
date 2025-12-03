import sys
import os
import uuid
import json
import argparse
import contextlib

# Add src to path so we can import bot modules
sys.path.append('/home/ubuntu/vpn-bot/src')

try:
    from bot.config_manager import add_user_to_config, add_ss_user, add_tuic_user, add_vless_plain_user, add_admin_tuic_user, remove_ss_user, remove_vless_user
    from bot.config import SERVER_IP, SERVER_PORT, SS_PORT, TUIC_PORT, VLESS_PLAIN_PORT, PUBLIC_KEY, SHORT_ID, SERVER_NAME
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def generate_vless_link(uid, server_ip, server_port, public_key, short_id, server_name, name):
    return f"vless://{uid}@{server_ip}:{server_port}?encryption=none&flow=xtls-rprx-vision&security=reality&sni={server_name}&fp=chrome&pbk={public_key}&sid={short_id}&type=tcp&headerType=none#{name}"

def generate_ss_link(password, server_ip, server_port, method, name):
    import base64
    user_info = f"{method}:{password}"
    user_info_b64 = base64.urlsafe_b64encode(user_info.encode()).decode().strip('=')
    return f"ss://{user_info_b64}@{server_ip}:{server_port}#{name}"

def add_user(protocol, name):
    uid = str(uuid.uuid4())
    
    if protocol == 'vless':
        with contextlib.redirect_stdout(sys.stderr):
            success = add_user_to_config(uid, name)
        if success:
            link = generate_vless_link(uid, SERVER_IP, SERVER_PORT, PUBLIC_KEY, SHORT_ID, SERVER_NAME, name)
            print(json.dumps({"status": "success", "uuid": uid, "link": link, "protocol": "vless"}))
        else:
            print(json.dumps({"status": "error", "message": "Failed to add VLESS user"}))
            
    elif protocol == 'ss':
        # For SS, password is the UUID
        with contextlib.redirect_stdout(sys.stderr):
            success = add_ss_user(uid, name)
        if success:
            link = generate_ss_link(uid, SERVER_IP, SS_PORT, "chacha20-ietf-poly1305", name)
            print(json.dumps({"status": "success", "password": uid, "link": link, "protocol": "ss"}))
        else:
            print(json.dumps({"status": "error", "message": "Failed to add SS user"}))
            
    elif protocol == 'tuic':
        with contextlib.redirect_stdout(sys.stderr):
            success = add_tuic_user(uid, name)
        if success:
            # TUIC link format is complex, just returning credentials for now
            print(json.dumps({"status": "success", "uuid": uid, "password": uid, "protocol": "tuic"}))
        else:
            print(json.dumps({"status": "error", "message": "Failed to add TUIC user"}))
            
    elif protocol == 'admin_tuic':
        if not name:
            print(json.dumps({"status": "error", "message": "Name required for admin_tuic user"}))
            return
        with contextlib.redirect_stdout(sys.stderr):
            success = add_admin_tuic_user(uid, name)
        if success:
            print(json.dumps({"status": "success", "uuid": uid, "name": name, "protocol": "admin_tuic"}))
        else:
            print(json.dumps({"status": "error", "message": "Failed to add Admin TUIC user"}))
            
    elif protocol == 'vless-plain':
        with contextlib.redirect_stdout(sys.stderr):
            success = add_vless_plain_user(uid, name)
        if success:
             print(json.dumps({"status": "success", "uuid": uid, "protocol": "vless-plain"}))
        else:
             print(json.dumps({"status": "error", "message": "Failed to add VLESS Plain user"}))
    else:
        print(json.dumps({"status": "error", "message": f"Unknown protocol: {protocol}"}))

def remove_user(protocol, identifier):
    if protocol == 'vless' or protocol == 'vless-plain' or protocol == 'tuic':
        # TUIC and VLESS Plain removal logic might need to be added to config_manager if missing
        # For now assuming remove_vless_user works for VLESS
        with contextlib.redirect_stdout(sys.stderr):
            success = remove_vless_user(identifier)
        if success:
             print(json.dumps({"status": "success", "message": f"Removed {identifier}"}))
        else:
             print(json.dumps({"status": "error", "message": "Failed to remove user"}))
    elif protocol == 'ss':
        with contextlib.redirect_stdout(sys.stderr):
            success = remove_ss_user(identifier)
        if success:
             print(json.dumps({"status": "success", "message": f"Removed {identifier}"}))
        else:
             print(json.dumps({"status": "error", "message": "Failed to remove user"}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['add', 'remove'])
    parser.add_argument("protocol", choices=['vless', 'ss', 'tuic', 'vlessplain', 'admin_tuic'], help="VPN protocol")
    parser.add_argument('--name', help='User name for add')
    parser.add_argument('--id', help='UUID/Password for remove')
    
    args = parser.parse_args()
    
    if args.action == 'add':
        if not args.name:
            print(json.dumps({"status": "error", "message": "Name required for add"}))
            sys.exit(1)
        add_user(args.protocol, args.name)
    elif args.action == 'remove':
        if not args.id:
            print(json.dumps({"status": "error", "message": "ID required for remove"}))
            sys.exit(1)
        remove_user(args.protocol, args.id)
