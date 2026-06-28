#!/bin/bash
# =============================================================================
# repack-bootimg.sh — Reconstruir boot.img con kernel pmOS + initramfs Arch
# =============================================================================
# Uso: repack-bootimg.sh <pmos-boot.img> <arch-initramfs.gz> <output.img>
# =============================================================================
set -euo pipefail

PMOS_BOOT="${1:-pmos-base/images/boot.img}"
ARCH_INITRAMFS="${2:-arch-initramfs.gz}"
OUTPUT="${3:-boot-begonia-arch.img}"

if [ ! -f "$PMOS_BOOT" ]; then
    echo "Error: pmOS boot.img not found: $PMOS_BOOT"
    exit 1
fi

if [ ! -f "$ARCH_INITRAMFS" ]; then
    echo "Warning: Arch initramfs not found, using pmOS initramfs"
    cp "$PMOS_BOOT" "$OUTPUT"
    echo "Output: $OUTPUT (pmOS original)"
    exit 0
fi

echo "=== Repacking boot.img for Arch begonia ==="

# Extract boot.img parameters using mkbootimg tools
WORKDIR=$(mktemp -d)
trap "rm -rf $WORKDIR" EXIT

cd "$WORKDIR"

# Try unpack_bootimg (Android SDK)
if command -v unpack_bootimg &>/dev/null; then
    echo "Using unpack_bootimg..."
    unpack_bootimg --boot_img "$OLDPWD/$PMOS_BOOT" --out extracted 2>&1 | head -5

    # Repack with new initramfs
    mkbootimg \
        --kernel extracted/kernel \
        --ramdisk "$OLDPWD/$ARCH_INITRAMFS" \
        --dtb extracted/dtb 2>/dev/null || \
    mkbootimg \
        --kernel extracted/kernel \
        --ramdisk "$OLDPWD/$ARCH_INITRAMFS" \
        --cmdline "$(cat extracted/cmdline 2>/dev/null || echo '')" \
        --base "$(cat extracted/base 2>/dev/null || echo '0x40000000')" \
        --pagesize "$(cat extracted/pagesize 2>/dev/null || echo '2048')" \
        --os_version "$(cat extracted/os_version 2>/dev/null || echo '15.0.0')" \
        --os_patch_level "$(cat extracted/os_patch_level 2>/dev/null || echo '2126-05-01')" \
        --output "$OLDPWD/$OUTPUT"
else
    # Fallback: use pmbootstrap bootimg_analyze and abootimg
    echo "Checking if abootimg is available..."
    if command -v abootimg &>/dev/null; then
        abootimg -x "$OLDPWD/$PMOS_BOOT"
        abootimg --create "$OLDPWD/$OUTPUT" -k zImage -r "$OLDPWD/$ARCH_INITRAMFS" -f bootimg.cfg ||
        abootimg -u "$OLDPWD/$PMOS_BOOT" -r "$OLDPWD/$ARCH_INITRAMFS" && \
          cp "$OLDPWD/$PMOS_BOOT" "$OLDPWD/$OUTPUT"
    else
        echo "No mkbootimg/abootimg available, using original boot.img with initramfs appended"
        # Last resort: copy original (pmOS initramfs stays)
        cp "$OLDPWD/$PMOS_BOOT" "$OLDPWD/$OUTPUT"
        echo "⚠️ Using original boot.img (pmOS initramfs, NOT Arch)"
    fi
fi

echo ""
echo "=== Boot image repacked ==="
ls -lh "$OLDPWD/$OUTPUT"
file "$OLDPWD/$OUTPUT"