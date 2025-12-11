import json
import subprocess
import os
import fcntl
import time
from src.bot.config import SINGBOX_CONFIG_PATH

LOCK_FILE = "/tmp/singbox_config.lock"

class FileLock:
    def __init__(self, lock_file=LOCK_FILE, timeout=30):
        self.lock_file = lock_file
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        start_time = time.time()
        self.fd = open(self.lock_file, 'w')
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError):
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file} within {self.timeout} seconds")
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            self.fd.close()

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
        result = subprocess.run(["sudo", "cp", temp_path, SINGBOX_CONFIG_PATH], 
                                check=True, timeout=5, capture_output=True)
        print(f"Config saved successfully to {SINGBOX_CONFIG_PATH}")
        subprocess.run(["rm", temp_path], check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, PermissionError, subprocess.TimeoutExpired) as e:
        error_msg = f"CRITICAL: Failed to save config to {SINGBOX_CONFIG_PATH}: {e}"
        print(error_msg)
        # Log to a file for debugging
        try:
            with open('/tmp/config_manager_errors.log', 'a') as log:
                import datetime
                log.write(f"{datetime.datetime.now()}: {error_msg}\n")
        except:
            pass
        raise  # Re-raise to make errors visible
    finally:
        # Clean up temp file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass



def add_user_to_config(uuid, email, limit_mbps=0):
    """Wrapper to handle locking and reloading separately."""
    should_reload = False
    with FileLock():
        should_reload = _add_user_to_config_internal(uuid, email, limit_mbps)
    
    if should_reload:
        reload_service()
        return True
    return False

def _add_user_to_config_internal(uuid, email, limit_mbps=0):
    config = load_config()
    
    # Determine target inbound based on limit
    # Default to main inbound (vless-in)
    target_tag = "vless-in"
    
    # If limit is set (e.g. 12 Mbps), use limited inbound
    if limit_mbps > 0 and limit_mbps <= 12.0: 
        target_tag = "vless-limited-in"
        
    print(f"Adding user {email} to inbound: {target_tag} (Limit: {limit_mbps} Mbps)")

    # Find the target inbound
    target_inbound = None
    for inbound in config['inbounds']:
        if inbound.get('tag') == target_tag:
            target_inbound = inbound
            break
            
    # Fallback to first VLESS if tag not found (backward compatibility)
    if not target_inbound:
        print(f"Warning: Inbound with tag '{target_tag}' not found. Falling back to first VLESS inbound.")
        for inbound in config['inbounds']:
             if inbound['type'] == 'vless':
                target_inbound = inbound
                break
    
    if not target_inbound:
        print("Error: No VLESS inbound found in config.")
        return False

    users = target_inbound.get('users', [])
    
    # Remove user from ALL VLESS inbounds to ensure they are only in the target one
    # This handles moving users between limited and unlimited inbounds
    for inbound in config['inbounds']:
        if inbound['type'] == 'vless' and 'users' in inbound:
            original_count = len(inbound['users'])
            inbound['users'] = [u for u in inbound['users'] if u['uuid'] != uuid]
            if len(inbound['users']) < original_count:
                print(f"Removed user {uuid} from inbound {inbound.get('tag')} (Moving to {target_tag})")

    # Check if user already exists in target (should be gone now, but safety check)
    users = target_inbound.get('users', [])
    for user in users:
        if user['uuid'] == uuid:
            # Should not happen due to removal above, but if it does, update name
            user['name'] = email
            save_config(config)
            return True
            
    users.append({
        "uuid": uuid,
        "flow": "xtls-rprx-vision",
        "name": email
    })
    target_inbound['users'] = users
    
    # Add to API stats users if enabled
    if 'experimental' in config and 'v2ray_api' in config['experimental']:
        stats_users = config['experimental']['v2ray_api']['stats'].get('users', [])
        if uuid not in stats_users:
            stats_users.append(uuid)
            config['experimental']['v2ray_api']['stats']['users'] = stats_users
            
    save_config(config)
    
    # VERIFY
    verify_config = load_config()
    found = False
    for inbound in verify_config.get('inbounds', []):
        if inbound.get('tag') == target_tag:
            for user in inbound.get('users', []):
                if user.get('uuid') == uuid:
                    found = True
                    break
    
    if not found:
        error_msg = f"CRITICAL: VLESS user {email} NOT found in {target_tag} after save!"
        print(error_msg)
        return False
    
    print(f"✓ VLESS user {email} verified in {target_tag}")
    return True

def add_ss_user(password, name):
    """Add a Shadowsocks user with unique password for tracking."""
    should_reload = False
    with FileLock():
        should_reload = _add_ss_user_internal(password, name)
    
    if should_reload:
        reload_service()
        return True
    return False

def _add_ss_user_internal(password, name):
    config = load_config()
    
    try:
        # Find Shadowsocks inbound (tag: ss-in)
        ss_inbound = None
        for inbound in config.get('inbounds', []):
            if inbound.get('tag') == 'ss-in':
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
        
        # VERIFY the key was actually added by reading config back
        verify_config = load_config()
        found = False
        for inbound in verify_config.get('inbounds', []):
            if inbound.get('type') == 'shadowsocks':
                for user in inbound.get('users', []):
                    if user.get('password') == password:
                        found = True
                        break
        
        if not found:
            error_msg = f"CRITICAL: SS user {name} was NOT found in config after save!"
            print(error_msg)
            with open('/tmp/config_manager_errors.log', 'a') as log:
                import datetime
                log.write(f"{datetime.datetime.now()}: {error_msg}\n")
            return False
        
        print(f"✓ SS user {name} verified in config")
        return True
    except Exception as e:
        error_msg = f"Error adding SS user {name}: {e}"
        print(error_msg)
        with open('/tmp/config_manager_errors.log', 'a') as log:
            import datetime
            log.write(f"{datetime.datetime.now()}: {error_msg}\n")
        return False

def add_tuic_user(uuid, name):
    """Add a user to the TUIC inbound."""
    should_reload = False
    with FileLock():
        should_reload = _add_tuic_user_internal(uuid, name)
    
    if should_reload:
        reload_service()
        return True
    return False

def _add_tuic_user_internal(uuid, name):
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
                
                # VERIFY the key was actually added
                verify_config = load_config()
                found = False
                for inbound in verify_config.get('inbounds', []):
                    if inbound.get('tag') == 'tuic-in':
                        for user in inbound.get('users', []):
                            if user.get('uuid') == uuid:
                                found = True
                                break
                
                if not found:
                    error_msg = f"CRITICAL: TUIC user {name} NOT found in config after save!"
                    print(error_msg)
                    with open('/tmp/config_manager_errors.log', 'a') as log:
                        import datetime
                        log.write(f"{datetime.datetime.now()}: {error_msg}\n")
                    return False
                
                print(f"✓ TUIC user {name} verified in config")
                return True
        print("Warning: No TUIC inbound with tag 'tuic-in' found in config")
        return False
    except Exception as e:
        error_msg = f"Error adding TUIC user {name}: {e}"
        print(error_msg)
        with open('/tmp/config_manager_errors.log', 'a') as log:
            import datetime
            log.write(f"{datetime.datetime.now()}: {error_msg}\n")
        return False

def add_vless_plain_user(uuid, name):
    """Add a user to the Plain VLESS inbound."""
    should_reload = False
    with FileLock():
        should_reload = _add_vless_plain_user_internal(uuid, name)
    
    if should_reload:
        reload_service()
        return True
    return False

def _add_vless_plain_user_internal(uuid, name):
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
                
                # VERIFY the key was actually added
                verify_config = load_config()
                found = False
                for inbound in verify_config.get('inbounds', []):
                    if inbound.get('tag') == 'vless-plain-in':
                        for user in inbound.get('users', []):
                            if user.get('uuid') == uuid:
                                found = True
                                break
                
                if not found:
                    error_msg = f"CRITICAL: Plain VLESS user {name} NOT found in config after save!"
                    print(error_msg)
                    with open('/tmp/config_manager_errors.log', 'a') as log:
                        import datetime
                        log.write(f"{datetime.datetime.now()}: {error_msg}\n")
                    return False
                
                print(f"✓ Plain VLESS user {name} verified in config")
                return True
        print("Warning: No Plain VLESS inbound with tag 'vless-plain-in' found in config")
        return False
    except Exception as e:
        error_msg = f"Error adding Plain VLESS user {name}: {e}"
        print(error_msg)
        with open('/tmp/config_manager_errors.log', 'a') as log:
            import datetime
            log.write(f"{datetime.datetime.now()}: {error_msg}\n")
        return False

def remove_ss_user(password):
    """Remove a Shadowsocks user by password (UUID)."""
    should_reload = False
    with FileLock():
        should_reload = _remove_ss_user_internal(password)
    
    if should_reload:
        reload_service()
        return True
    return False

def _remove_ss_user_internal(password):
    config = load_config()
    
    try:
        # Find Shadowsocks inbound (tag: ss-in)
        ss_inbound = None
        for inbound in config.get('inbounds', []):
            if inbound.get('tag') == 'ss-in':
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
    should_reload = False
    with FileLock():
        should_reload = _remove_vless_user_internal(uuid)
    
    if should_reload:
        reload_service()
        return True
    return False

def _remove_vless_user_internal(uuid):
    config = load_config()
    
    try:
        inbound = config['inbounds'][0] # Assuming first inbound is VLESS
        users = inbound.get('users', [])
        initial_count = len(users)
        
        # Filter out user
        inbound['users'] = [u for u in users if u.get('uuid') != uuid]
        
        if len(inbound['users']) < initial_count:
            save_config(config)
            return True
            
        return False
    except Exception as e:
        print(f"Error removing VLESS user: {e}")
        return False
def add_admin_tuic_user(uuid, name):
    """Add a user to the Admin TUIC server (standalone)."""
    # Admin TUIC uses a separate config file and service
    TUIC_CONFIG_PATH = "/etc/tuic/server.json"
    
    try:
        # Load config
        with open(TUIC_CONFIG_PATH, 'r') as f:
            config = json.load(f)
            
        # Add user if not exists
        if uuid not in config['users']:
            config['users'][uuid] = uuid  # Password is same as UUID for simplicity
            
            # Save config (requires sudo)
            temp_path = "/tmp/tuic_server.json"
            with open(temp_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            subprocess.run(["sudo", "cp", temp_path, TUIC_CONFIG_PATH], check=True)
            subprocess.run(["rm", temp_path], check=True)
            
            # Reload service
            print("Reloading Admin TUIC service...")
            subprocess.run(["sudo", "systemctl", "restart", "tuic"], check=True)
            print(f"✓ Admin TUIC user {name} added and service restarted")
            return True
        else:
            print(f"Admin TUIC user {uuid} already exists")
            return False
            
    except Exception as e:
        print(f"Error adding Admin TUIC user: {e}")
        return False

