import subprocess
import time
import sys

PACKAGE_NAME = "io.nekohasekai.sagernet"

def run_adb_command(command):
    try:
        result = subprocess.run(f"adb {command}", shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running adb command '{command}': {e}")
        print(f"Stderr: {e.stderr}")
        return None

def restart_app():
    print(f"Restarting Android App...")
    
    # 1. Force Stop
    print(f"Stopping {PACKAGE_NAME}...")
    run_adb_command(f"shell am force-stop {PACKAGE_NAME}")
    
    time.sleep(1)
    
    # 2. Start (Launch Main Activity)
    print(f"Starting {PACKAGE_NAME}...")
    # Using monkey to launch the app is often more reliable than guessing the activity class if not known
    # Alternatively: shell monkey -p io.nekohasekai.sagernet -c android.intent.category.LAUNCHER 1
    run_adb_command(f"shell monkey -p {PACKAGE_NAME} -c android.intent.category.LAUNCHER 1")
    
    print("App restarted successfully.")

if __name__ == "__main__":
    restart_app()
