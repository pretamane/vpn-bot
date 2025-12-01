import threading
import time
import sys
import os
import uuid

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from bot.config_manager import add_ss_user, remove_ss_user

SUCCESS_COUNT = 0
FAILURE_COUNT = 0
LOCK = threading.Lock()

def worker(worker_id):
    global SUCCESS_COUNT, FAILURE_COUNT
    user_uuid = str(uuid.uuid4())
    name = f"StressTest-User-{worker_id}"
    
    print(f"Worker {worker_id} starting...")
    try:
        if add_ss_user(user_uuid, name):
            with LOCK:
                SUCCESS_COUNT += 1
            print(f"Worker {worker_id} SUCCESS")
            # Cleanup
            remove_ss_user(user_uuid)
        else:
            with LOCK:
                FAILURE_COUNT += 1
            print(f"Worker {worker_id} FAILED")
    except Exception as e:
        print(f"Worker {worker_id} EXCEPTION: {e}")
        with LOCK:
            FAILURE_COUNT += 1

def run_stress_test():
    threads = []
    num_workers = 2  # Simulate 2 concurrent users
    
    print(f"Starting stress test with {num_workers} concurrent workers...")
    
    for i in range(num_workers):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    print("-" * 20)
    print(f"Test Complete.")
    print(f"Successful additions: {SUCCESS_COUNT}")
    print(f"Failed additions: {FAILURE_COUNT}")
    
    if FAILURE_COUNT == 0:
        print("✅ LOCKING TEST PASSED: No race conditions detected.")
    else:
        print("❌ LOCKING TEST FAILED: Failures detected.")

if __name__ == "__main__":
    # This script is intended to be run on the server where config_manager works
    # We will simulate it by running it remotely via SSH
    run_stress_test()
