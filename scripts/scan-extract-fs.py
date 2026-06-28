#!/usr/bin/env python3
"""Scan raw disk image for ext4 partitions and extract modules/firmware."""

import struct, os, subprocess, sys, json

raw_path = sys.argv[1] if len(sys.argv) > 1 else "system-raw.img"
out_dir = sys.argv[2] if len(sys.argv) > 2 else "out"

raw_size = os.path.getsize(raw_path)
print(f"Scanning {raw_size/1e9:.1f} GB for ext4 partitions...")

found = []
with open(raw_path, 'rb') as f:
    step = 1048576  # 1 MB — ext4 blocks are aligned
    max_scan = min(raw_size, 3 * 1024**3)
    for start_off in range(0, max_scan, step):
        check_off = start_off + 1024
        if check_off + 58 > raw_size:
            break
        f.seek(check_off)
        data = f.read(200)
        if len(data) < 136:
            continue

        magic = struct.unpack_from('<H', data, 56)[0]
        if magic != 0xEF53:
            continue

        blocks_count = struct.unpack_from('<I', data, 4)[0]
        rev_level = struct.unpack_from('<I', data, 76)[0]
        vol_name_raw = struct.unpack_from('16s', data, 120)[0]
        vol_name = vol_name_raw.decode('ascii', errors='replace').strip('\x00')

        if blocks_count < 1000 or blocks_count > 10000000:
            continue

        total_gb = blocks_count * 1024 / 1024 / 1024
        print(f"  EXT4 at offset {start_off} (label='{vol_name}', {total_gb:.1f} GB)")
        found.append((start_off, vol_name, blocks_count))

if not found:
    print("ERROR: No ext4 partitions found!")
    sys.exit(1)

print(f"\nTotal partitions: {len(found)}")

os.makedirs(out_dir, exist_ok=True)

for i, (offset, label, blocks) in enumerate(found):
    print(f"\n{'='*60}")
    print(f"Partition {i+1}: '{label}' at offset {offset} ({offset/1024/1024:.0f} MB)")
    print(f"{'='*60}")

    os.makedirs('mnt', exist_ok=True)

    result = subprocess.run(
        ['sudo', 'mount', '-o', f'loop,ro,offset={offset}', raw_path, 'mnt'],
        capture_output=True, text=True, timeout=10
    )

    if result.returncode != 0:
        print(f"  Mount failed: {result.stderr[:200]}")
        continue

    print("  Mounted!")

    entries = os.listdir('mnt')
    print(f"  Root entries: {entries[:10]}...")

    # Kernel modules
    if os.path.isdir('mnt/lib/modules'):
        kvers = sorted(os.listdir('mnt/lib/modules'))
        for kver in kvers:
            mod_dir = os.path.join('mnt/lib/modules', kver)
            mod_count = sum(len(files) for _, _, files in os.walk(mod_dir))
            print(f"  Kernel modules: {kver} ({mod_count} files)")

        subprocess.run(
            ['sudo', 'tar', '-czf', os.path.join(out_dir, 'modules.tar.gz'),
             '-C', 'mnt/lib', 'modules'],
            capture_output=True, timeout=120
        )
        size = os.path.getsize(os.path.join(out_dir, 'modules.tar.gz'))
        count_r = subprocess.run(['tar', '-tzf', os.path.join(out_dir, 'modules.tar.gz')],
                                 capture_output=True, text=True, timeout=30)
        file_count = len(count_r.stdout.strip().split('\n')) if count_r.stdout.strip() else 0
        print(f"  modules.tar.gz: {size/1024/1024:.0f} MB ({file_count} files)")

    # Firmware
    if os.path.isdir('mnt/lib/firmware'):
        fw_count = sum(len(files) for _, _, files in os.walk('mnt/lib/firmware'))
        print(f"  Firmware: {fw_count} files")

        subprocess.run(
            ['sudo', 'tar', '-czf', os.path.join(out_dir, 'firmware.tar.gz'),
             '-C', 'mnt/lib', 'firmware'],
            capture_output=True, timeout=120
        )
        size = os.path.getsize(os.path.join(out_dir, 'firmware.tar.gz'))
        print(f"  firmware.tar.gz: {size/1024/1024:.0f} MB")

    # OS release
    os_release = os.path.join('mnt', 'usr/lib/os-release')
    if os.path.isfile(os_release):
        with open(os_release) as rf:
            for line in rf:
                if line.startswith('PRETTY_NAME='):
                    print(f"  OS: {line.strip()}")
                    break

    # dtbs (on boot partition)
    if label == 'pmOS_boot' and os.path.isdir('mnt/dtbs'):
        print("  dtbs found, copying...")
        subprocess.run(['sudo', 'cp', '-a', 'mnt/dtbs', out_dir], capture_output=True, timeout=30)

    subprocess.run(['sudo', 'umount', 'mnt'], capture_output=True, timeout=10)
    subprocess.run(['rmdir', 'mnt'], capture_output=True)

print(f"\n{'='*60}")
print("Final output:")
subprocess.run(['ls', '-lh', out_dir], timeout=5)
