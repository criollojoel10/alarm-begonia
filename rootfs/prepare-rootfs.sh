#!/bin/bash
# =============================================================================
# prepare-rootfs.sh — Preparar rootfs Arch Linux ARM para begonia
# =============================================================================
set -euo pipefail

ROOTFS="${1:-mnt}"
SRC_MODULES="${2:-modules}"
SRC_FIRMWARE="${3:-firmware}"

if [ ! -d "$ROOTFS" ]; then
    echo "Error: $ROOTFS not found"
    exit 1
fi

echo "=== Preparing Arch Linux ARM rootfs for begonia ==="

# 1. Inject kernel modules
if [ -d "$SRC_MODULES" ]; then
    echo "--- Injecting kernel modules ---"
    KVER=$(ls "$SRC_MODULES" | grep -v '\.tar\.gz' | head -1)
    if [ -n "$KVER" ]; then
        sudo mkdir -p "$ROOTFS/usr/lib/modules/$KVER"
        sudo cp -a "$SRC_MODULES/$KVER"/* "$ROOTFS/usr/lib/modules/$KVER/" 2>/dev/null || true
        echo "Modules for kernel $KVER injected"
    fi
fi

# 2. Inject firmware
if [ -d "$SRC_FIRMWARE" ]; then
    echo "--- Injecting firmware ---"
    sudo mkdir -p "$ROOTFS/usr/lib/firmware"
    sudo cp -a "$SRC_FIRMWARE"/* "$ROOTFS/usr/lib/firmware/" 2>/dev/null || true
    echo "Firmware injected"
fi

# 3. Set console target and services
echo "--- Configuring services ---"
sudo systemd-nspawn -D "$ROOTFS" --pipe sh -c '
    systemctl set-default multi-user.target
    systemctl enable sshd
    systemctl enable NetworkManager
    systemctl enable systemd-resolved
    systemctl enable systemd-timesyncd

    # User setup
    echo -e "root\nroot\n" | passwd root 2>/dev/null || true
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
' || true

# 4. Set hostname
echo "begonia-alarm" | sudo tee "$ROOTFS/etc/hostname"

# 5. Firstboot config
if [ -f firstboot.sh ]; then
    sudo mkdir -p "$ROOTFS/etc/systemd/system"
    sudo cp firstboot.sh "$ROOTFS/root/"
fi

echo "=== Rootfs preparation complete ==="