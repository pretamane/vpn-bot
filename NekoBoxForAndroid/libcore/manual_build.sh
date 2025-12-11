#!/bin/bash
set -e

export ANDROID_HOME=/home/guest/tzdump/vpn-bot/android-sdk
export ANDROID_NDK_HOME=$ANDROID_HOME/ndk/25.2.9519653
TOOLCHAIN=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64

# Define architectures
declare -A ARCH_MAP
ARCH_MAP=( ["arm64-v8a"]="android-arm64" ["armeabi-v7a"]="android-arm" ["x86"]="android-386" ["x86_64"]="android-amd64" )

declare -A CC_MAP
CC_MAP=( ["arm64-v8a"]="aarch64-linux-android21-clang" ["armeabi-v7a"]="armv7a-linux-androideabi21-clang" ["x86"]="i686-linux-android21-clang" ["x86_64"]="x86_64-linux-android21-clang" )

mkdir -p libs/jni

for abi in "${!ARCH_MAP[@]}"; do
    echo "Building for $abi..."
    target=${ARCH_MAP[$abi]}
    cc_target=${CC_MAP[$abi]}
    
    export GOOS=android
    export GOARCH=$(echo $target | cut -d'-' -f2)
    if [ "$GOARCH" == "arm" ]; then export GOARM=7; fi
    
    export CC="$TOOLCHAIN/bin/$cc_target"
    export CXX="$TOOLCHAIN/bin/${cc_target}++"
    export CGO_ENABLED=1
    
    mkdir -p libs/jni/$abi
    
    # Manual build
    echo "Compiling for $target..."
    
    # Use the generated sources in cmd/gobind
    # We need to ensure the output name is libgojni.so because that's what the Java code expects (System.loadLibrary("gojni"))
    
    go build -buildmode=c-shared -o libs/jni/$abi/libgojni.so -tags='with_conntrack,with_gvisor,with_quic,with_wireguard,with_utls,with_clash_api' ./cmd/gobind || echo "Build failed for $abi"
done

# Package into AAR
echo "Packaging into AAR..."
# We need to take the existing libcore.aar (from app/libs if available, or we need to find classes.jar)
# If we don't have classes.jar, we are in trouble.
# Let's assume app/libs/libcore.aar exists and has classes.jar.

if [ -f "../app/libs/libcore.aar" ]; then
    mkdir -p aar_temp
    unzip -o ../app/libs/libcore.aar -d aar_temp
    
    # Replace JNI libs
    cp -r libs/jni/* aar_temp/jni/
    
    # Create new AAR
    cd aar_temp
    zip -r ../libcore_new.aar .
    cd ..
    
    # Install
    cp libcore_new.aar ../app/libs/libcore.aar
    echo "Installed new libcore.aar"
    
    # Clean up
    rm -rf aar_temp libcore_new.aar
else
    echo "Error: ../app/libs/libcore.aar not found. Cannot package AAR."
    exit 1
fi


