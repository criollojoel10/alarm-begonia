#!/usr/bin/env python3
"""
Update Android boot.img cmdline with real partition UUIDs.

The original pmOS boot.img has stale UUIDs from the build server.
This script replaces them with the real UUIDs of the partitions
we create in the Arch build, so the pmOS initramfs finds them
deterministically.

Usage:
  update-cmdline-uuid.py <input-boot.img> <root-uuid> <boot-uuid> <output.img>
"""

import struct, sys, re, os

PAGE_SIZE = 2048


def main():
    if len(sys.argv) < 5:
        print(f"Usage: {sys.argv[0]} <input.img> <root-uuid> <boot-uuid> <output.img>")
        sys.exit(1)

    in_path = sys.argv[1]
    root_uuid = sys.argv[2].strip()
    boot_uuid = sys.argv[3].strip()
    out_path = sys.argv[4]

    with open(in_path, 'rb') as f:
        data = f.read()

    # Read header
    if data[0:8] != b'ANDROID!':
        print(f"❌ Not an Android boot image: {data[0:8]!r}")
        sys.exit(1)

    cmdline = data[64:576].rstrip(b'\x00').decode('ascii', errors='replace')
    print(f"Old cmdline: {cmdline}")

    # Remove old UUID entries
    new_cmdline = re.sub(r'\s*pmos_root_uuid=[-a-f0-9]+\s*', ' ', cmdline)
    new_cmdline = re.sub(r'\s*pmos_boot_uuid=[-a-f0-9]+\s*', ' ', new_cmdline)
    new_cmdline = re.sub(r'\s+', ' ', new_cmdline).strip()

    # Inject real UUIDs
    new_cmdline = f"pmos_root_uuid={root_uuid} pmos_boot_uuid={boot_uuid} {new_cmdline}"
    print(f"New cmdline: {new_cmdline}")

    cmd_bytes = new_cmdline.encode('ascii', errors='replace')[:511]

    # Write output
    buf = bytearray(data)
    # Zero out cmdline area first
    for i in range(64, 576):
        buf[i] = 0
    buf[64:64+len(cmd_bytes)] = cmd_bytes

    with open(out_path, 'wb') as f:
        f.write(buf)

    # Verify
    with open(out_path, 'rb') as f:
        verify = f.read(1648)
    v_cmdline = verify[64:576].rstrip(b'\x00').decode('ascii', 'replace')
    print(f"\n✅ boot.img updated → {out_path}")
    print(f"   Cmdline: {v_cmdline[:100]}...")
    print(f"   root_uuid={root_uuid}")
    print(f"   boot_uuid={boot_uuid}")

    assert root_uuid in v_cmdline, "Root UUID not found in cmdline!"
    assert boot_uuid in v_cmdline, "Boot UUID not found in cmdline!"


if __name__ == '__main__':
    main()
