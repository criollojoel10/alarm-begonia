#!/usr/bin/env python3
"""Extract kernel image from a boot.img (Android boot image format).

Usage: extract-kernel.py <boot.img> <output>

The kernel data starts at offset = page_size (the header occupies one page).
The kernel_offset field in the header is a load address, NOT a file offset.
"""
import struct
import sys

with open(sys.argv[1], 'rb') as f:
    data = f.read()

kernel_size = struct.unpack('<I', data[8:12])[0]
page_size = struct.unpack('<I', data[36:40])[0]
header_version = struct.unpack('<I', data[40:44])[0]

# Kernel data starts right after the first page (which contains the header)
kernel_offset = page_size

print(f'Header version: {header_version}')
print(f'Page size: {page_size}')
print(f'Kernel size: {kernel_size} bytes')
print(f'Kernel file offset: {kernel_offset}')

if kernel_size == 0:
    print('ERROR: kernel size is 0 — invalid boot.img?')
    sys.exit(1)

actual_size = min(kernel_size, len(data) - kernel_offset)
kernel_data = data[kernel_offset:kernel_offset + actual_size]

with open(sys.argv[2], 'wb') as out:
    out.write(kernel_data)

print(f'Extracted kernel: {len(kernel_data)} bytes → {sys.argv[2]}')
