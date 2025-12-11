import sys
import time
import grpc
import os
import logging
from datetime import datetime, timedelta

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'v2ray-proto'))

try:
    import command_pb2
    import command_pb2_grpc
except ImportError as e:
    print(f"[FATAL] Failed to import generated proto files: {e}")
    sys.exit(1)

from db.database import (
    get_db_connection, update_usage, get_daily_usage, 
    expire_user, start_grace_period, end_grace_period,
    is_in_grace_period, get_grace_period_remaining,
    update_data_warning, has_warning_been_sent
)
from bot.config_manager import remove_vless_user
from bot.notifications import (
    notify_data_warning, notify_grace_period_start,
    notify_grace_period_ending, notify_key_expired
)

# Configuration
API_ENDPOINT = "127.0.0.1:10085"
CHECK_INTERVAL = 60  # Seconds
DATA_WARNING_THRESHOLDS = [30, 65, 95]  # Warning at 30%, 65%, 95%
VLESS_LIMITED_DATA_LIMIT_GB = 3.0  # 3 GB for VLESS Limited keys

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("Watchdog")

def get_all_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users WHERE is_active = 1').fetchall()
    conn.close()
    return users

def query_stats(stub, uuid, direction):
    try:
        pattern = f"user>>>{uuid}>>>traffic>>>{direction}"
        request = command_pb2.QueryStatsRequest(
            pattern=pattern,
            reset=True  # Reset stats after reading to get delta
        )
        response = stub.QueryStats(request, timeout=5)
        for stat in response.stat:
            if direction in stat.name:
                return stat.value
        return 0
    except grpc.RpcError as e:
        # It's normal to not find stats if user hasn't connected
        return 0
    except Exception as e:
        logger.error(f"Error querying {uuid} {direction}: {e}")
        return 0

def check_vless_limited_user(user, daily_gb):
    """
    Check and handle VLESS Limited user data usage with warnings and grace period.
    
    Args:
        user: User dict with all fields
        daily_gb: Current data usage in GB
    
    Returns:
        bool: True if user should be kept active, False if expired
    """
    uuid = user['uuid']
    telegram_id = user['telegram_id']
    limit_gb = VLESS_LIMITED_DATA_LIMIT_GB
    percentage = (daily_gb / limit_gb) * 100
    
    logger.info(f"VLESS Limited user {uuid}: {daily_gb:.2f}/{limit_gb} GB ({percentage:.1f}%)")
    
    # Check if in grace period
    if user.get('grace_period_start'):
        if is_in_grace_period(user):
            remaining = get_grace_period_remaining(user)
            hours_remaining = int(remaining.total_seconds() / 3600)
            logger.info(f"User {uuid} in grace period, {hours_remaining}h remaining")
            
            # Send warning when 2 hours remaining
            if hours_remaining <= 2 and not has_warning_been_sent(user, 'grace_2h'):
                notify_grace_period_ending(telegram_id, hours_remaining)
                update_data_warning(uuid, 'grace_2h')
            
            return True
        else:
            # Grace period expired
            logger.warning(f"User {uuid} grace period ended, expiring key")
            end_grace_period(uuid)
            remove_vless_user(uuid)
            notify_key_expired(telegram_id, reason='grace_period_ended')
            return False
    
    # Check if limit exceeded - start grace period
    if daily_gb >= limit_gb:
        if not user.get('grace_period_start'):
            logger.warning(f"User {uuid} exceeded limit: {daily_gb:.2f}/{limit_gb} GB - Starting grace period")
            start_grace_period(uuid)
            notify_grace_period_start(telegram_id, daily_gb, limit_gb)
            # Also send 100% warning
            if not has_warning_been_sent(user, 100):
                notify_data_warning(telegram_id, daily_gb, limit_gb, 100)
                update_data_warning(uuid, 100)
        return True
    
    # Check warning thresholds
    for threshold in DATA_WARNING_THRESHOLDS:
        if percentage >= threshold and not has_warning_been_sent(user, threshold):
            logger.info(f"Sending {threshold}% warning to user {uuid}")
            notify_data_warning(telegram_id, daily_gb, limit_gb, threshold)
            update_data_warning(uuid, threshold)
    
    return True

def main():
    logger.info("Starting Watchdog Service...")
    logger.info(f"VLESS Limited monitoring: {VLESS_LIMITED_DATA_LIMIT_GB} GB limit")
    logger.info(f"Warning thresholds: {DATA_WARNING_THRESHOLDS}%")
    logger.info(f"Grace period: 24 hours")
    
    try:
        channel = grpc.insecure_channel(API_ENDPOINT)
        stub = command_pb2_grpc.StatsServiceStub(channel)
    except Exception as e:
        logger.fatal(f"Failed to connect to API: {e}")
        return

    while True:
        try:
            users = get_all_users()
            logger.debug(f"Checking {len(users)} active users")
            
            for user_row in users:
                user = dict(user_row)
                uuid = user['uuid']
                protocol = user.get('protocol', 'ss')
                
                # Get traffic delta
                down = query_stats(stub, uuid, "downlink")
                up = query_stats(stub, uuid, "uplink")
                total_bytes = down + up
                
                if total_bytes > 0:
                    update_usage(uuid, total_bytes)
                    logger.debug(f"User {uuid} traffic: +{total_bytes/1024/1024:.2f} MB")
                    
                # Get daily usage
                daily_usage = get_daily_usage(uuid)
                daily_gb = daily_usage / (1024**3)
                
                # Only monitor VLESS Limited keys with data limits
                if protocol == 'vless_limited':
                    check_vless_limited_user(user, daily_gb)
                
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Shutting down watchdog service...")
            break
        except Exception as e:
            logger.error(f"Watchdog loop error: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
