#!/usr/bin/env python3
import subprocess
import os
import sys

PROJECT_ROOT = "/home/guest/tzdump/vpn-bot/NekoBoxForAndroid"

def run_command(command, cwd=None):
    try:
        print(f"Running: {command}")
        subprocess.run(command, shell=True, check=True, cwd=cwd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False

def find_apk():
    # Search for the debug APK
    search_path = os.path.join(PROJECT_ROOT, "app/build/outputs/apk")
    for root, dirs, files in os.walk(search_path):
        for file in files:
            if file.endswith("-debug.apk") and "unaligned" not in file:
                return os.path.join(root, file)
    return None

def main():
    print("=== Building Android App ===")
    
    # 1. Build
    # Using assemblePlayDebug as confirmed previously
    if not run_command("./gradlew assemblePlayDebug", cwd=PROJECT_ROOT):
        print("Build failed.")
        sys.exit(1)
    
    print("Build successful.")
    
    # 2. Find APK
    apk = find_apk()
    if not apk:
        print("Could not find generated APK.")
        sys.exit(1)
    
    print(f"Found APK: {apk}")
    
    # 3. Install
    print("Installing APK...")
    if run_command(f"adb install -r \"{apk}\""):
        print("Install successful.")
    else:
        print("Install failed.")
        sys.exit(1)

    # 4. Launch (using existing restart script logic)
    print("Launching App...")
    run_command("adb shell monkey -p io.nekohasekai.sagernet -c android.intent.category.LAUNCHER 1")

if __name__ == "__main__":
    main()
