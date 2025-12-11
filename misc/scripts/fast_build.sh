#!/bin/bash
export JAVA_HOME=/home/guest/.vscode/extensions/redhat.java-1.45.0-linux-x64/jre/21.0.8-linux-x86_64
export ANDROID_HOME=/home/guest/tzdump/vpn-bot/android-sdk
export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH

# Optimized build command
cd NekoBoxForAndroid
./gradlew assembleDebug --offline --parallel --configuration-cache

# Install and launch
cd ..
adb install -r -t NekoBoxForAndroid/app/build/outputs/apk/oss/debug/NekoBox-1.4.1-arm64-v8a-debug.apk
adb shell am start -n io.nekohasekai.sagernet/io.nekohasekai.sagernet.ui.LoginActivity
