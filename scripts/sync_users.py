import sys
import os
import json
import logging

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../src")

from db.database import get_all_users
from bot.config_manager import load_config, save_config, reload_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sync_users():
    logger.info("Starting user synchronization...")
    
    # 1. Get all users from DB
    db_users = get_all_users()
    logger.info(f"Found {len(db_users)} users in database.")
    
    # 2. Load current config
    config = load_config()
    
    # 3. Map protocols to inbounds
    inbounds = {
        'ss': None,
        'vless': None,
        'tuic': None,
        'vlessplain': None
    }
    
    # Find inbounds
    for inbound in config.get('inbounds', []):
        if inbound.get('type') == 'shadowsocks':
            inbounds['ss'] = inbound
        elif inbound.get('type') == 'vless' and inbound.get('tag') == 'vless-in': # Reality
            inbounds['vless'] = inbound
        elif inbound.get('type') == 'tuic':
            inbounds['tuic'] = inbound
        elif inbound.get('type') == 'vless' and inbound.get('tag') == 'vless-plain-in':
            inbounds['vlessplain'] = inbound

    changes_made = False
    
    for user in db_users:
        uuid = user['uuid']
        protocol = user['protocol']
        username = user['username'] or f"User{user['telegram_id']}"
        
        # Normalize protocol names
        if protocol == 'admin_tuic':
            protocol = 'tuic'
            
        target_inbound = inbounds.get(protocol)
        
        if not target_inbound:
            logger.warning(f"Unknown protocol {protocol} for user {username} ({uuid})")
            continue
            
        # Check if user exists in inbound
        users_list = target_inbound.get('users', [])
        found = False
        
        for u in users_list:
            # Check based on protocol type
            if protocol == 'ss':
                if u.get('password') == uuid: # SS uses UUID as password
                    found = True
                    break
            elif protocol == 'tuic':
                if u.get('uuid') == uuid:
                    found = True
                    break
            else: # vless / vlessplain
                if u.get('uuid') == uuid:
                    found = True
                    break
        
        if not found:
            logger.info(f"Adding missing user {username} ({protocol}) to config.")
            
            new_user = {}
            if protocol == 'ss':
                new_user = {"password": uuid, "name": username}
            elif protocol == 'tuic':
                new_user = {"uuid": uuid, "password": uuid, "name": username}
            elif protocol == 'vless':
                new_user = {"uuid": uuid, "flow": "xtls-rprx-vision", "name": username}
            elif protocol == 'vlessplain':
                new_user = {"uuid": uuid, "name": username}
                
            if 'users' not in target_inbound:
                target_inbound['users'] = []
                
            target_inbound['users'].append(new_user)
            changes_made = True
            
    if changes_made:
        logger.info("Saving updated configuration...")
        if save_config(config):
            logger.info("Configuration saved.")
            reload_service()
            logger.info("Service reloaded.")
        else:
            logger.error("Failed to save configuration!")
    else:
        logger.info("No changes needed. Config is in sync.")

if __name__ == "__main__":
    sync_users()
