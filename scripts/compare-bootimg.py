#!/usr/bin/env python3
"""Compare two boot.img: size ratio and sanity checks."""
import os
import sys

orig = os.path.getsize(sys.argv[1])
new = os.path.getsize(sys.argv[2])
ratio = new / orig * 100
print(f'Original pmOS boot.img: {orig:,} B')
print(f'Kupfer boot.img:        {new:,} B')
print(f'Ratio: {ratio:.1f}%')
if ratio < 50:
    print('boot.img es <50% del original - puede faltar DTB o seccion recovery')
elif ratio > 150:
    print('boot.img es >150% del original - initramfs muy grande')
else:
    print('Tamano razonable vs original')
