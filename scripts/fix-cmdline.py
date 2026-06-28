#!/usr/bin/env python3
"""Fix boot.img cmdline: remove pmos_root_uuid and pmos_boot_uuid.

The original pmOS boot.img has hardcoded UUIDs from the build #25 rootfs.
When initramfs find_partition() is called with a UUID that doesn't match,
it returns EMPTY without falling back to filesystem label detection.
Removing the UUIDs lets the initramfs find the root by label (pmOS_root).
"""
import struct
import re
import sys

def main():
    with open('pmos-base/boot.img', 'rb') as f:
        data = bytearray(f.read())

    magic = data[:8]
    if magic != b'ANDROID!':
        print("ERROR: not an Android boot.img", file=sys.stderr)
        sys.exit(1)

    # Read cmdline at fixed offset 64, length 512, null-terminated
    cmdline_old = data[64:576].split(b'\x00')[0].decode('ascii', 'replace')
    print(f"Old: {cmdline_old}")

    # Remove UUID params so initramfs falls through to label detection
    cmdline_new = re.sub(r'\s*pmos_root_uuid=[-a-f0-9]+\s*', ' ', cmdline_old)
    cmdline_new = re.sub(r'\s*pmos_boot_uuid=[-a-f0-9]+\s*', ' ', cmdline_new)
    cmdline_new = re.sub(r'\s+', ' ', cmdline_new).strip()
    print(f"New: {cmdline_new}")

    new_bytes = cmdline_new.encode('ascii')
    new_bytes = new_bytes.ljust(512, b'\x00')
    data[64:576] = new_bytes[:512]

    with open('pmos-base/boot.img', 'wb') as f:
        f.write(data)

    print("boot.img cmdline fixed!")

if __name__ == '__main__':
    main()
