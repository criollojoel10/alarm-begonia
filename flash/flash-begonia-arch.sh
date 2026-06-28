#!/bin/bash
# flash-begonia-arch.sh — Flash Arch Linux ARM on Xiaomi Redmi Note 8 Pro (begonia)
#
# Usage:
#   1. Put device in fastboot mode (Volume Down + Power)
#   2. Run this script from the directory with the images
#   3. Reboot when done

set -e

echo "=== Flashing Arch Linux ARM on begonia ==="
echo ""

# Check files exist
if [ ! -f boot-begonia-arch.img ]; then
    echo "❌ boot-begonia-arch.img not found!"
    exit 1
fi

if [ ! -f rootfs-archlinuxarm-begonia-console.img ]; then
    echo "⚠️  rootfs-archlinuxarm-begonia-console.img not found!"
    if [ -f rootfs-archlinuxarm-begonia-console.img.xz ]; then
        echo "   Decompressing..."
        unxz rootfs-archlinuxarm-begonia-console.img.xz
    else
        exit 1
    fi
fi

echo "📱 Checking fastboot connection..."
fastboot devices

echo ""
echo "📦 Formatting userdata (ext4)..."
fastboot format:ext4 userdata

echo ""
echo "🔧 Flashing boot..."
fastboot flash boot boot-begonia-arch.img

echo ""
echo "💾 Flashing rootfs (this may take a while)..."
fastboot flash userdata rootfs-archlinuxarm-begonia-console.img

echo ""
echo "🔄 Rebooting..."
fastboot reboot

echo ""
echo "✅ Done!"
echo ""
echo "After boot (5-10 min first boot), login:"
echo "  ssh alarm@<device-ip>"
echo "  Password: alarm"
echo ""
echo "First boot takes longer — systemd generates machine-id,"
echo "regenerates SSH host keys, etc."
