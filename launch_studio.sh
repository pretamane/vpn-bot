#!/bin/bash

# Set up environment variables for Android SDK and Java
export JAVA_HOME=/home/guest/tzdump/vpn-bot/jdk-17.0.2
export ANDROID_HOME=/home/guest/tzdump/vpn-bot/android-sdk
export PATH=$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH

# Launch Android Studio
echo "🚀 Launching Android Studio..."
echo "If you are using SSH, make sure you connected with 'ssh -X' or 'ssh -Y' to see the GUI."
/opt/android-studio/bin/studio.sh
