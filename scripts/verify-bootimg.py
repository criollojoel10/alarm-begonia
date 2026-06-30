#!/usr/bin/env python3
"""Verify an Android boot.img: print header fields, sizes, file size."""
import os
import struct
import sys

with open(sys.argv[1], 'rb') as f:
    header = f.read(2048)  # read enough for v2 header

magic = header[0:8]
if magic != b'ANDROID!':
    print(f'WARNING: magic is {magic!r}, not ANDROID!')

k_size = struct.unpack('<I', header[8:12])[0]
k_addr = struct.unpack('<I', header[12:16])[0]
r_size = struct.unpack('<I', header[16:20])[0]
r_addr = struct.unpack('<I', header[20:24])[0]
s_size = struct.unpack('<I', header[24:28])[0]
page_size = struct.unpack('<I', header[36:40])[0]
hdr_ver = struct.unpack('<I', header[40:44])[0]
hdr_size = struct.unpack('<I', header[48:52])[0]
cmdline = header[56:568].rstrip(b'\x00').decode('ascii', 'replace')

print(f'Magic: {magic.decode()} {"✅" if magic == b"ANDROID!" else "❌"}')
print(f'Kernel size: {k_size:,} B')
print(f'Ramdisk size: {r_size:,} B')
print(f'Second size: {s_size:,} B')
print(f'Page size: {page_size:,}')
print(f'Header version: {hdr_ver}')
print(f'Header size: {hdr_size:,} B')
print(f'Cmdline: {cmdline}')
print(f'kupfer_root: {"kupfer_root" in cmdline}')

file_size = os.path.getsize(sys.argv[1])
print(f'File size: {file_size:,} B ({file_size/1024/1024:.1f} MiB)')

# Rough estimate
k_pages = ((k_size + page_size - 1) // page_size) * page_size
r_pages = ((r_size + page_size - 1) // page_size) * page_size
est_total = page_size + k_pages + r_pages + page_size  # header + kernel + ramdisk + extra page
print(f'Estimated minimum: {page_size + k_pages + r_pages:,} B (header + kernel + ramdisk)')

if file_size < k_size + r_size:
    print(f'ERROR: file size ({file_size:,}) < kernel+ramdisk ({k_size + r_size:,})')
    sys.exit(1)
