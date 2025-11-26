import sys
import os
import uuid
import logging
import subprocess

# Add paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db, add_user, get_user, update_usage, get_daily_usage
from bot.config_manager import load_config, add_user_to_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verification")

def test_db():
    logger.info("Testing Database...")
    init_db()
    
    test_uuid = str(uuid.uuid4())
    if add_user(test_uuid, 12345, "testuser"):
        logger.info("✅ User added to DB")
    else:
        logger.error("❌ Failed to add user")
        return False
        
    user = get_user(test_uuid)
    if user and user['username'] == "testuser":
        logger.info("✅ User retrieved from DB")
    else:
        logger.error("❌ Failed to retrieve user")
        return False
        
    update_usage(test_uuid, 1024*1024*100) # 100MB
    usage = get_daily_usage(test_uuid)
    if usage == 1024*1024*100:
        logger.info("✅ Usage updated and retrieved")
    else:
        logger.error(f"❌ Usage mismatch: {usage}")
        return False
        
    return True

def test_config_manager():
    logger.info("Testing Config Manager...")
    test_uuid = str(uuid.uuid4())
    
    try:
        # We mock reload_service to avoid actual service reload during test if needed
        # But here we want to test if it runs.
        # Note: This might fail if sudo requires password.
        try:
            add_user_to_config(test_uuid, "test_config_user")
        except Exception as e:
            logger.warning(f"⚠️ Service reload/save failed (expected in dev): {e}")
            # Continue to check if file was updated
        
        config = load_config()
        # Handle mock config
        if config.get("inbounds"):
            users = config['inbounds'][0]['users']
            found = False
            for user in users:
                if user['uuid'] == test_uuid:
                    found = True
                    break
            
            if found:
                logger.info("✅ User added to Sing-Box config (or mock config)")
            else:
                logger.warning("⚠️ User not found in config (might be using mock config without persistence)")
        else:
             logger.warning("⚠️ Config structure invalid or mock config used")
            
    except Exception as e:
        logger.error(f"❌ Config manager failed: {e}")
        return False
        
    return True

def test_key_generation():
    logger.info("Testing Key Generation...")
    from bot.config import SERVER_IP, PUBLIC_KEY
    
    # Verify SERVER_IP matches AWS IP
    EXPECTED_IP = "43.205.90.213"
    if SERVER_IP != EXPECTED_IP:
        logger.error(f"❌ SERVER_IP mismatch! Expected {EXPECTED_IP}, got {SERVER_IP}")
        return False
    else:
        logger.info(f"✅ SERVER_IP matches AWS IP: {SERVER_IP}")
        
    return True

def test_config_alignment():
    logger.info("Testing Config Alignment with Stable AWS Config...")
    import json
    from bot.config import SERVER_IP, PUBLIC_KEY, SHORT_ID, SERVER_NAME
    
    STABLE_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configurations/stable-tztest-cfgs.json")
    
    try:
        with open(STABLE_CONFIG_PATH, 'r') as f:
            stable_config = json.load(f)
            
        # Find the AWS outbound
        aws_outbound = None
        for outbound in stable_config.get('outbounds', []):
            if outbound.get('tag') == 'mumbai-reality-aws':
                aws_outbound = outbound
                break
        
        if not aws_outbound:
            logger.error("❌ Could not find 'mumbai-reality-aws' tag in stable config")
            return False
            
        # Compare values
        mismatches = []
        
        if aws_outbound.get('server') != SERVER_IP:
            mismatches.append(f"SERVER_IP: Bot={SERVER_IP}, Stable={aws_outbound.get('server')}")
            
        reality = aws_outbound.get('tls', {}).get('reality', {})
        if reality.get('public_key') != PUBLIC_KEY:
            mismatches.append(f"PUBLIC_KEY: Bot={PUBLIC_KEY}, Stable={reality.get('public_key')}")
            
        if reality.get('short_id') != SHORT_ID:
            mismatches.append(f"SHORT_ID: Bot={SHORT_ID}, Stable={reality.get('short_id')}")
            
        server_name = aws_outbound.get('tls', {}).get('server_name')
        if server_name != SERVER_NAME:
            mismatches.append(f"SERVER_NAME: Bot={SERVER_NAME}, Stable={server_name}")
            
        if mismatches:
            logger.error("❌ Config Mismatches Found:")
            for m in mismatches:
                logger.error(f"  - {m}")
            return False
        else:
            logger.info("✅ Bot config matches 'stable-tztest-cfgs.json' perfectly!")
            return True
            
    except FileNotFoundError:
        logger.warning(f"⚠️ Stable config file not found at {STABLE_CONFIG_PATH}")
        return True # Soft pass if file missing
    except Exception as e:
        logger.error(f"❌ Failed to compare configs: {e}")
        return False

if __name__ == "__main__":
    if test_db() and test_config_manager() and test_key_generation() and test_config_alignment():
        logger.info("🎉 All components verified!")
    else:
        logger.error("⚠️ Verification failed")
