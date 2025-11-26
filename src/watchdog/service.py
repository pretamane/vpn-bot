import sys
import time
import grpc
import os
import logging
from datetime import datetime

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'v2ray-proto'))

try:
    import command_pb2
    import command_pb2_grpc
except ImportError as e:
    print(f"[FATAL] Failed to import generated proto files: {e}")
    sys.exit(1)

from db.database import get_db_connection, update_usage, get_daily_usage
from bot.config_manager import remove_ss_user

# Configuration
API_ENDPOINT = "127.0.0.1:10085"
CHECK_INTERVAL = 60 # Seconds

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
            reset=True # Reset stats after reading to get delta
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

def main():
    logger.info("Starting Watchdog Service...")
    
    try:
        channel = grpc.insecure_channel(API_ENDPOINT)
        stub = command_pb2_grpc.StatsServiceStub(channel)
    except Exception as e:
        logger.fatal(f"Failed to connect to API: {e}")
        return

    while True:
        try:
            users = get_all_users()
            for user in users:
                uuid = user['uuid']
                limit_gb = user['data_limit_gb']
                
                # Get traffic delta
                down = query_stats(stub, uuid, "downlink")
                up = query_stats(stub, uuid, "uplink")
                total_bytes = down + up
                
                if total_bytes > 0:
                    update_usage(uuid, total_bytes)
                    
                # Check daily limit
                daily_usage = get_daily_usage(uuid)
                daily_gb = daily_usage / (1024**3)
                
                if daily_gb > limit_gb:
                    logger.warning(f"User {uuid} exceeded limit: {daily_gb:.2f}GB / {limit_gb}GB")
                    # Block user by setting inactive
                    conn = get_db_connection()
                    conn.execute('UPDATE users SET is_active = 0 WHERE uuid = ?', (uuid,))
                    conn.commit()
                    conn.close()
                    logger.info(f"User {uuid} deactivated due to limit exceed")
                    
                    logger.info(f"User {uuid} deactivated due to limit exceed")
                    
                    # Remove from Sing-Box config dynamically
                    if remove_ss_user(uuid):
                        logger.info(f"User {uuid} removed from Sing-Box config")
                    else:
                        logger.error(f"Failed to remove user {uuid} from Sing-Box config")
                    
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Watchdog loop error: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
