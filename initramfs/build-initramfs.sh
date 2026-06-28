#!/bin/bash
# =============================================================================
# build-initramfs.sh — Construir initramfs para Arch Linux ARM begonia
# =============================================================================
# Uso: build-initramfs.sh <rootfs-mount-point>
# =============================================================================
set -euo pipefail

ROOTFS="${1:-mnt}"
OUTDIR="${2:-.}"

if [ ! -d "$ROOTFS" ]; then
    echo "Error: rootfs mount point not found: $ROOTFS"
    exit 1
fi

echo "=== Building Arch initramfs for begonia ==="

BUILD_DIR=$(mktemp -d)
trap "rm -rf $BUILD_DIR" EXIT

# Copy init script
cp "$(dirname "$0")/init" "$BUILD_DIR/init"
chmod +x "$BUILD_DIR/init"

# Copy busybox (must be static)
if [ -f "$ROOTFS/usr/bin/busybox" ]; then
    cp "$ROOTFS/usr/bin/busybox" "$BUILD_DIR/busybox"
elif [ -f "$ROOTFS/bin/busybox" ]; then
    cp "$ROOTFS/bin/busybox" "$BUILD_DIR/busybox"
fi

# Copy minimal busybox applet symlinks
for applet in sh mount umount mkdir ls cat echo sleep lsblk losetup modprobe; do
    ln -sf busybox "$BUILD_DIR/$applet" 2>/dev/null || true
done

# Kernel modules storage (optional, for mount helpers)
mkdir -p "$BUILD_DIR/lib/modules"

# Make device nodes
mkdir -p "$BUILD_DIR/dev"
mkdir -p "$BUILD_DIR/proc" "$BUILD_DIR/sys" "$BUILD_DIR/run"

# Create cpio archive
cd "$BUILD_DIR"
find . -print0 | cpio --null --create --format=newc --quiet | gzip -9 > "$OUTDIR/arch-initramfs.gz"

echo "=== Initramfs built ==="
echo "  Size: $(wc -c < "$OUTDIR/arch-initramfs.gz") bytes ($(du -h "$OUTDIR/arch-initramfs.gz" | cut -f1))"
echo "  Path: $OUTDIR/arch-initramfs.gz"
ls -lh "$OUTDIR/arch-initramfs.gz"