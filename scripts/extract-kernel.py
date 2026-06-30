#!/usr/bin/env python3
"""Extract kernel image from a boot.img given as argv[1], write to argv[2]."""
import struct
import sys

with open(sys.argv[1], 'rb') as f:
    data = f.read()
kernel_size = struct.unpack('<I', data[8:12])[0]
kernel_offset = struct.unpack('<I', data[12:16])[0]
with open(sys.argv[2], 'wb') as out:
    out.write(data[kernel_offset:kernel_offset + kernel_size])
print(f'Extracted kernel: {kernel_size} bytes')
