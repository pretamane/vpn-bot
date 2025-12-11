import subprocess
import time
import sys
import os

# Add project root to path to find other tools if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

INSTANCE_ID = "i-071f6e8701ed1ad2c"
SERVICE_NAME = "api-server" # The service running on port 8082

def restart_remote_server():
    print(f"Restarting remote server service '{SERVICE_NAME}' on {INSTANCE_ID}...")
    cmd = [
        "aws", "ssm", "send-command",
        "--instance-ids", INSTANCE_ID,
        "--document-name", "AWS-RunShellScript",
        "--parameters", f'commands=["sudo systemctl restart {SERVICE_NAME}"]',
        "--output", "text"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("Server restart command sent successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to send server restart command: {e}")
        sys.exit(1)

def restart_local_app():
    print("Restarting Android App...")
    try:
        # Call the restart_app.py script
        subprocess.run([sys.executable, "tools/restart_app.py"], check=True)
        print("Android App restarted.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart Android App: {e}")

def main():
    restart_remote_server()
    print("Waiting 5 seconds for server to stabilize...")
    time.sleep(5)
    restart_local_app()
    print("\n=== Reload Complete ===")

if __name__ == "__main__":
    main()
