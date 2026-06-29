#!/usr/bin/env python3
"""
Repack Android boot.img for Arch Linux ARM on begonia.

Replaces the pmOS initramfs with a mkinitcpio-generated Arch initramfs
(or a fallback minimal busybox initramfs). Creates /etc/fstab in rootfs.

Usage:
  repack-bootimg.py --ramdisk <pmos-boot.img> <initramfs.cpio.gz> <output.img>
  repack-bootimg.py <pmos-boot.img> <rootfs-mount> <output.img>
"""

import struct, os, sys, gzip, math, shutil, subprocess, re

PAGE_SIZE = 2048


def read_bootimg_header(data):
    """Extract key fields from Android boot image header (v0-v2)."""
    if len(data) < PAGE_SIZE:
        raise ValueError(f"File too small: {len(data)} bytes")

    magic = data[0:8]
    if magic != b'ANDROID!':
        raise ValueError(f"Not an Android boot image: {magic!r}")

    h = {}
    h['kernel_size']    = struct.unpack('<I', data[8:12])[0]
    h['kernel_addr']    = struct.unpack('<I', data[12:16])[0]
    h['ramdisk_size']   = struct.unpack('<I', data[16:20])[0]
    h['ramdisk_addr']   = struct.unpack('<I', data[20:24])[0]
    h['second_size']    = struct.unpack('<I', data[24:28])[0]
    h['second_addr']    = struct.unpack('<I', data[28:32])[0]
    h['tags_addr']      = struct.unpack('<I', data[32:36])[0]
    h['page_size']      = struct.unpack('<I', data[36:40])[0]
    h['header_version'] = struct.unpack('<I', data[40:44])[0]
    h['os_version']     = struct.unpack('<I', data[44:48])[0]
    h['name']           = data[48:64].rstrip(b'\x00').decode('ascii', errors='replace')
    h['cmdline']        = data[64:576].split(b'\x00')[0].decode('ascii', errors='replace')
    h['recovery_dtbo_size']   = struct.unpack('<I', data[1632:1636])[0] if h['header_version'] >= 1 else 0
    h['recovery_dtbo_offset'] = struct.unpack('<Q', data[1636:1644])[0] if h['header_version'] >= 1 else 0
    h['header_size']          = struct.unpack('<I', data[1644:1648])[0] if h['header_version'] >= 1 else PAGE_SIZE
    h['dtb_size']             = struct.unpack('<I', data[1648:1652])[0] if h['header_version'] >= 2 else 0
    h['dtb_addr']             = struct.unpack('<Q', data[1652:1660])[0] if h['header_version'] >= 2 else 0
    return h


def page_align(sz, page=PAGE_SIZE):
    return ((sz + page - 1) // page) * page


def extract_parts(data):
    """Extract kernel, ramdisk, second, dtb from boot.img."""
    h = read_bootimg_header(data)
    ps = h['page_size']
    k_off = ps
    k_dat = data[k_off:k_off + h['kernel_size']]
    k_pgs = (h['kernel_size'] + ps - 1) // ps
    r_off = ps + k_pgs * ps
    r_dat = data[r_off:r_off + h['ramdisk_size']]
    r_pgs = (h['ramdisk_size'] + ps - 1) // ps
    s_off = r_off + r_pgs * ps
    s_dat = data[s_off:s_off + h['second_size']]
    s_pgs = (h['second_size'] + ps - 1) // ps
    d_off = s_off + s_pgs * ps
    d_dat = data[d_off:d_off + h['dtb_size']] if h['dtb_size'] > 0 else b''
    return h, k_dat, r_dat, s_dat, d_dat


def write_bootimg(kernel, ramdisk, dtb, overrides, page=2048):
    """Build a new Android boot.img from parts."""
    h = dict(
        kernel_size=len(kernel), kernel_addr=0x40080000,
        ramdisk_size=len(ramdisk), ramdisk_addr=0x47C80000,
        second_size=0, second_addr=0x40F00000,
        tags_addr=0x40000100, page_size=page, header_version=2,
        os_version=0x001D0007, name='', cmdline='',
        recovery_dtbo_size=0, recovery_dtbo_offset=0,
        header_size=1660, dtb_size=len(dtb), dtb_addr=0x40000000,
    )
    h.update(overrides)

    buf = bytearray(page)
    p = lambda off, fmt, val: struct.pack_into(fmt, buf, off, val)
    p(0, '<8s', b'ANDROID!')
    p(8, '<I', h['kernel_size']); p(12, '<I', h['kernel_addr'])
    p(16, '<I', h['ramdisk_size']); p(20, '<I', h['ramdisk_addr'])
    p(24, '<I', h['second_size']); p(28, '<I', h['second_addr'])
    p(32, '<I', h['tags_addr']); p(36, '<I', h['page_size'])
    p(40, '<I', h['header_version']); p(44, '<I', h['os_version'])
    name_b = h['name'].encode('ascii', errors='replace')[:15]
    buf[48:48+len(name_b)] = name_b
    cmd_b = h['cmdline'].encode('ascii', errors='replace')[:511]
    buf[64:64+len(cmd_b)] = cmd_b
    if h['header_version'] >= 1:
        p(1632, '<I', h['recovery_dtbo_size'])
        p(1636, '<Q', h['recovery_dtbo_offset'])
        p(1644, '<I', h['header_size'])
    if h['header_version'] >= 2:
        p(1648, '<I', h['dtb_size'])
        p(1652, '<Q', h['dtb_addr'])

    buf.extend(kernel)
    buf.extend(b'\x00' * (page_align(len(kernel), page) - len(kernel)))
    buf.extend(ramdisk)
    buf.extend(b'\x00' * (page_align(len(ramdisk), page) - len(ramdisk)))
    if dtb:
        buf.extend(dtb)
        buf.extend(b'\x00' * (page_align(len(dtb), page) - len(dtb)))
    return bytes(buf)


def build_minimal_initramfs(busybox_path, init_script_path, out_path):
    """Build a minimal cpio.gz initramfs with busybox + custom init."""
    build = '/tmp/initramfs_build'
    if os.path.exists(build):
        shutil.rmtree(build)
    for d in ('/bin', '/dev', '/proc', '/sys', '/run', '/lib/modules'):
        os.makedirs(build + d, exist_ok=True)

    shutil.copy2(busybox_path, build + '/bin/busybox')
    os.chmod(build + '/bin/busybox', 0o755)

    for a in ('sh', 'mount', 'umount', 'mkdir', 'ls', 'cat', 'echo',
              'sleep', 'lsblk', 'losetup', 'modprobe', 'dmesg',
              'blkid', 'grep', 'cut', 'tr', 'head', 'tail',
              'switch_root', 'mknod', 'ln', 'cp', 'mv', 'rm', 'chmod'):
        if not os.path.exists(build + '/' + a):
            os.symlink('/bin/busybox', build + '/' + a)
    if not os.path.exists(build + '/bin/sh'):
        os.symlink('busybox', build + '/bin/sh')

    shutil.copy2(init_script_path, build + '/init')
    os.chmod(build + '/init', 0o755)

    cwd = os.getcwd()
    os.chdir(build)
    cpio_raw = subprocess.run(
        ['find', '.', '-print0'],
        capture_output=True
    ).stdout
    cpio_out = subprocess.run(
        ['cpio', '--null', '--create', '--format=newc', '--quiet'],
        input=cpio_raw, capture_output=True
    ).stdout
    os.chdir(cwd)
    with gzip.open(out_path, 'wb', 9) as f:
        f.write(cpio_out)
    sz = os.path.getsize(out_path)
    shutil.rmtree(build)
    return sz


def create_fstab(rootfs):
    """Create /etc/fstab to prevent pmOS initramfs boot partition wait."""
    fstab = os.path.join(rootfs, 'etc', 'fstab')
    os.makedirs(os.path.dirname(fstab), exist_ok=True)
    with open(fstab, 'w') as f:
        f.write("""# /etc/fstab — static file system information
LABEL=pmOS_root  /  ext4  rw,noatime,nodiratime,data=ordered  0 1
tmpfs  /tmp  tmpfs  rw,nosuid,nodev,noexec,mode=1777  0 0
""")
    print("  ✓ /etc/fstab created in rootfs")


def fix_cmdline(cmdline):
    """Strip pmOS UUID references from cmdline."""
    c = re.sub(r'\s*pmos_root_uuid=[-a-f0-9]+\s*', ' ', cmdline)
    c = re.sub(r'\s*pmos_boot_uuid=[-a-f0-9]+\s*', ' ', c)
    c = re.sub(r'\s+', ' ', c).strip()
    return c


def main():
    if len(sys.argv) < 4:
        print(f"Usage:\n  {sys.argv[0]} --ramdisk <boot.img> <initramfs> <output>\n  {sys.argv[0]} <boot.img> <rootfs-mount> <output>")
        sys.exit(1)

    use_existing = sys.argv[1] == '--ramdisk'
    if use_existing:
        boot_img_path, initramfs_path, output_path = sys.argv[2], sys.argv[3], sys.argv[4]
        rootfs = None
    else:
        boot_img_path, rootfs, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
        initramfs_path = '/tmp/arch-initramfs.gz'

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"📖 Reading boot.img: {boot_img_path}")
    with open(boot_img_path, 'rb') as f:
        data = f.read()

    hdr, kernel, old_ramdisk, _, dtb = extract_parts(data)
    print(f"  Kernel: {len(kernel):,} B | Ramdisk: {len(old_ramdisk):,} B | DTB: {len(dtb):,} B | v{hdr['header_version']}")

    cf = fix_cmdline(hdr['cmdline'])
    print(f"  Cmdline fixed: {cf[:100]}...")

    if use_existing:
        print(f"📦 Using initramfs: {initramfs_path}")
        with open(initramfs_path, 'rb') as f:
            ramdisk = f.read()
    else:
        print(f"🔨 Building minimal initramfs from {rootfs}")
        bb = None
        for p in (rootfs + '/usr/bin/busybox', rootfs + '/bin/busybox'):
            if os.path.exists(p):
                with open(p, 'rb') as f:
                    if f.read(4).startswith(b'\x7fELF'):
                        bb = p
                        break
        if not bb:
            print("❌ No busybox found in rootfs")
            sys.exit(1)

        init_src = os.path.join(repo_dir, 'initramfs', 'init')
        if not os.path.exists(init_src):
            print(f"❌ Init script not found: {init_src}")
            sys.exit(1)

        sz = build_minimal_initramfs(bb, init_src, initramfs_path)
        print(f"  Built {sz:,} B → {initramfs_path}")
        with open(initramfs_path, 'rb') as f:
            ramdisk = f.read()
        create_fstab(rootfs)

    print("📦 Repacking boot.img...")
    new = write_bootimg(kernel, ramdisk, dtb, {
        'ramdisk_size': len(ramdisk),
        'cmdline': cf,
    }, page=hdr['page_size'])

    with open(output_path, 'wb') as f:
        f.write(new)

    v = read_bootimg_header(new)
    assert v['ramdisk_size'] == len(ramdisk), "Size mismatch"
    print(f"\n✅ boot.img repacked → {output_path}")
    print(f"   Total: {len(new):,} B | Kernel: {v['kernel_size']:,} B | Ramdisk: {v['ramdisk_size']:,} B | DTB: {v['dtb_size']:,} B")


if __name__ == '__main__':
    main()
