#!/bin/bash

# Dump UI hierarchy to device storage
echo "📸 Capturing UI snapshot..."
adb shell uiautomator dump /sdcard/window_dump.xml

# Pull the dump file to local machine
echo "⬇️  Pulling dump file..."
if adb pull /sdcard/window_dump.xml ./window_dump.xml; then
    echo "✅ Dump pulled successfully."
else
    echo "❌ Failed to pull dump file."
    exit 1
fi

# Run the inspection script
if [ -f "./inspect_ui.py" ]; then
    echo "🔍 Analyzing UI..."
    chmod +x ./inspect_ui.py
    ./inspect_ui.py ./window_dump.xml
else
    echo "❌ Error: inspect_ui.py not found!"
fi
