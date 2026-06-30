#!/usr/bin/env python3
"""Verify a boot.img: print cmdline, sizes, header version."""
import struct
import sys

with open(sys.argv[1], 'rb') as f:
    data = f.read(576)
c = data[64:576].rstrip(b'\x00').decode('ascii', 'replace')
has_label = 'kupfer_root' in c
print(f'Cmdline: {c}')
print(f'kupfer_root: {has_label}')
r_size = struct.unpack('<I', data[16:20])[0]
print(f'Ramdisk size: {r_size:,} B')
k_size = struct.unpack('<I', data[8:12])[0]
print(f'Kernel size: {k_size:,} B')
hdr_ver = struct.unpack('<I', data[36:40])[0]
print(f'Header version: {hdr_ver}')
print(f'Total size: {len(data):,} B')
