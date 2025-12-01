import json
import subprocess
import os
from bot.config import SINGBOX_CONFIG_PATH

def load_config():
    try:
        with open(SINGBOX_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Config file not found at {SINGBOX_CONFIG_PATH}. Using mock config.")
        return {"inbounds": [{"users": []}]}

def save_config(config):
    # Write to a temporary file first
    temp_path = "/tmp/singbox_config.json"
    try:
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Move to actual location with sudo (bot runs as ubuntu user, not root)
        subprocess.run(["sudo", "cp", temp_path, SINGBOX_CONFIG_PATH], check=True, timeout=5)
        subprocess.run(["rm", temp_path], check=True, timeout=5)
    except (subprocess.CalledProcessError, PermissionError) as e:
        print(f"Warning: Failed to save config to {SINGBOX_CONFIG_PATH}: {e}")
        raise  # Re-raise to make errors visible
    finally:
        # Clean up temp file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

def add_user_to_config(uuid, email):
    config = load_config()
    
    # Add to inbound users
    try:
        inbound = config['inbounds'][0] # Assuming first inbound is VLESS
        users = inbound.get('users', [])
        
        # Check if user already exists
        for user in users:
            if user['uuid'] == uuid:
                return False
                
        users.append({
            "uuid": uuid,
            "flow": "xtls-rprx-vision",
            "name": email # Optional, for identification
        })
        inbound['users'] = users
        
        # Add to API stats users if enabled
        if 'experimental' in config and 'v2ray_api' in config['experimental']:
            stats_users = config['experimental']['v2ray_api']['stats'].get('users', [])
            if uuid not in stats_users:
                stats_users.append(uuid)
                config['experimental']['v2ray_api']['stats']['users'] = stats_users
                
        save_config(config)
        reload_service()
        return True
    except (KeyError, IndexError) as e:
        print(f"Error updating config structure: {e}")
        return False

def add_ss_user(password, name):
    """Add a Shadowsocks user with unique password for tracking."""
    config = load_config()
    
    try:
        # Find Shadowsocks inbound (type: shadowsocks)
        ss_inbound = None
        for inbound in config.get('inbounds', []):
            if inbound.get('type') == 'shadowsocks':
                ss_inbound = inbound
                break
        
        if not ss_inbound:
            print("Warning: No Shadowsocks inbound found in config")
            return False
        
        # Initialize users array if it doesn't exist
        if 'users' not in ss_inbound:
            ss_inbound['users'] = []
        
        users = ss_inbound['users']
        
        # Check if user already exists
        for user in users:
            if user.get('password') == password:
                return False
        
        # Add new user
        users.append({
            "password": password,
            "name": name
        })
        
        save_config(config)
        reload_service()
        return True
    except Exception as e:
        print(f"Error adding SS user: {e}")
        return False

def add_tuic_user(uuid, name):
    """Add a user to the TUIC inbound."""
    config = load_config()
    
    try:
        # Find TUIC inbound
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'tuic-in': # Use .get() for safety
                # Initialize users array if it doesn't exist
                if 'users' not in inbound:
                    inbound['users'] = []

                # Check if user exists
                for user in inbound['users']:
                    if user['uuid'] == uuid:
                        return False # User already exists
                
                # Add user
                inbound['users'].append({
                    "uuid": uuid,
                    "password": uuid, # TUIC uses password field often same as UUID
                    "name": name
                })
                save_config(config)
                reload_service()
                return True
        print("Warning: No TUIC inbound with tag 'tuic-in' found in config")
        return False
    except Exception as e:
        print(f"Error adding TUIC user: {e}")
        return False

def add_vless_plain_user(uuid, name):
    """Add a user to the Plain VLESS inbound."""
    config = load_config()
    
    try:
        # Find Plain VLESS inbound
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'vless-plain-in': # Use .get() for safety
                # Initialize users array if it doesn't exist
                if 'users' not in inbound:
                    inbound['users'] = []

                # Check if user exists
                for user in inbound['users']:
                    if user['uuid'] == uuid:
                        return False # User already exists
                
                # Add user
                inbound['users'].append({
                    "uuid": uuid,
                    "name": name
                })
                save_config(config)
                reload_service()
                return True
        print("Warning: No Plain VLESS inbound with tag 'vless-plain-in' found in config")
        return False
    except Exception as e:
        print(f"Error adding Plain VLESS user: {e}")
        return False

def remove_ss_user(password):
    """Remove a Shadowsocks user by password (UUID)."""
    config = load_config()
    
    try:
        # Find Shadowsocks inbound
        ss_inbound = None
        for inbound in config.get('inbounds', []):
            if inbound.get('type') == 'shadowsocks':
                ss_inbound = inbound
                break
        
        if not ss_inbound or 'users' not in ss_inbound:
            return False
        
        users = ss_inbound['users']
        initial_count = len(users)
        
        # Filter out the user with matching password
        ss_inbound['users'] = [u for u in users if u.get('password') != password]
        
        if len(ss_inbound['users']) < initial_count:
            save_config(config)
            reload_service()
            return True
            
        return False
    except Exception as e:
        print(f"Error removing SS user: {e}")
        return False

def reload_service():
    """Gracefully reload sing-box without dropping connections."""
    print("Reloading Sing-Box configuration...")
    try:
        # Use 'reload' instead of 'restart' to avoid breaking existing connections
        subprocess.run(["sudo", "systemctl", "reload", "sing-box"], check=True, timeout=10)
        print("Sing-Box configuration reloaded successfully.")
    except subprocess.CalledProcessError:
        # If reload fails, fall back to restart (some services don't support reload)
        print("Reload failed, attempting restart...")
        try:
            subprocess.run(["sudo", "systemctl", "restart", "sing-box"], check=True, timeout=10)
            print("Sing-Box service restarted.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Warning: Failed to reload/restart sing-box service: {e}")
            raise  # Re-raise to make errors visible

def remove_vless_user(uuid):
    """Remove a VLESS user by UUID."""
    config = load_config()
    
    try:
        inbound = config['inbounds'][0] # Assuming first inbound is VLESS
        users = inbound.get('users', [])
        initial_count = len(users)
        
        # Filter out user
        inbound['users'] = [u for u in users if u.get('uuid') != uuid]
        
        if len(inbound['users']) < initial_count:
            save_config(config)
            reload_service()
            return True
            
        return False
    except Exception as e:
        print(f"Error removing VLESS user: {e}")
        return False
