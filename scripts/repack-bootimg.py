#!/usr/bin/env python3
"""
Android boot.img repacker — pure Python, no external deps.

Used as fallback when mkbootimg is not available.
Supports v2/v3 boot image headers.

Usage:
  repack-bootimg.py <input-boot.img> <initramfs> <cmdline> <output.img>
"""
import struct, sys, os

PAGE_SIZE = 4096

def round_to_page(size):
    return ((size + PAGE_SIZE - 1) // PAGE_SIZE) * PAGE_SIZE

def main():
    if len(sys.argv) < 5:
        print(f"Usage: {sys.argv[0]} <input.img> <initramfs> <cmdline> <output.img>")
        sys.exit(1)

    in_path = sys.argv[1]
    initrd_path = sys.argv[2]
    cmdline = sys.argv[3].strip()
    out_path = sys.argv[4]

    with open(in_path, 'rb') as f:
        data = f.read()

    magic = data[0:8]
    if magic not in (b'ANDROID!',):
        print(f"❌ Not Android boot image: {magic!r}")
        sys.exit(1)

    header_version = struct.unpack('<I', data[40:44])[0] if len(data) > 44 else 0
    page_size = struct.unpack('<I', data[32:36])[0] if len(data) > 36 else PAGE_SIZE
    if page_size < 2048:
        page_size = PAGE_SIZE

    # Read existing kernel, ramdisk
    k_offset = page_size
    k_size = struct.unpack('<I', data[8:12])[0]
    kernel = data[k_offset:k_offset + k_size]

    # We replace the ramdisk
    with open(initrd_path, 'rb') as f:
        initrd = f.read()

    # Calculate new offsets
    k_pages = round_to_page(k_size)
    r_pages = round_to_page(len(initrd))

    # Build header
    buf = bytearray(64 + 512)  # header + cmdline
    
    # Magic
    buf[0:8] = b'ANDROID!'
    # Kernel size
    struct.pack_into('<I', buf, 8, k_size)
    # Ramdisk size (new)
    struct.pack_into('<I', buf, 16, len(initrd))
    # Page size
    struct.pack_into('<I', buf, 32, page_size)
    # Header version
    struct.pack_into('<I', buf, 40, header_version)
    # OS version (23.0.0)
    os_version = (23 << 14) | (0 << 7) | 0
    struct.pack_into('<I', buf, 36, os_version)

    # Copy other header fields from original
    for field_offset in [12, 20, 24, 28]:  # second, dtb, tags sizes
        val = struct.unpack('<I', data[field_offset:field_offset+4])[0]
        struct.pack_into('<I', buf, field_offset, val)
    
    # Copy offsets from original (base, kernel_offset, etc.)
    for field_offset in range(44, min(64, len(data))):
        buf[field_offset] = data[field_offset]
    # If >= v3, use different layout
    if header_version >= 3:
        buf[48:52] = struct.pack('<I', k_pages + r_pages)  # dtb/additional size
    
    # Cmdline (bytes 64-576 or shorter for v3+)
    cmd_bytes = cmdline.encode('ascii', errors='replace')[:511]
    # Clear cmdline area
    for i in range(64, 576):
        buf[i] = 0
    buf[64:64+len(cmd_bytes)] = cmd_bytes

    out = bytearray(buf)

    # Add page padding after header
    header_pages = round_to_page(len(out))
    out.extend(b'\x00' * (header_pages - len(out)))

    # Write kernel at page boundary
    out.extend(kernel)
    k_pad = round_to_page(k_size) - k_size
    out.extend(b'\x00' * k_pad)

    # Write ramdisk
    out.extend(initrd)
    r_pad = round_to_page(len(initrd)) - len(initrd)
    out.extend(b'\x00' * r_pad)

    with open(out_path, 'wb') as f:
        f.write(out)

    print(f"✅ Boot image: {out_path}")
    print(f"   Kernel: {k_size:,} B → {k_pages:,} B")
    print(f"   Ramdisk: {len(initrd):,} B → {r_pages:,} B")
    print(f"   Cmdline: {cmdline[:80]}...")
    print(f"   Total: {len(out):,} B")


if __name__ == '__main__':
    main()
