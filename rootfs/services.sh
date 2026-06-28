#!/bin/bash
# =============================================================================
# services.sh — Configurar servicios para begonia console
# =============================================================================
set -euo pipefail

ROOTFS="${1:-mnt}"
SCRIPT_DIR="$(dirname "$0")"

if [ ! -d "$ROOTFS" ]; then
    echo "Error: $ROOTFS not found"
    exit 1
fi

echo "=== Configuring Arch services for begonia ==="

sudo systemd-nspawn -D "$ROOTFS" --pipe bash -c '
    echo "--- Setting default target ---"
    systemctl set-default multi-user.target

    echo "--- Enabling services ---"
    systemctl enable sshd
    systemctl enable NetworkManager
    systemctl enable systemd-resolved
    systemctl enable systemd-timesyncd

    echo "--- Disabling network-online wait (speeds boot) ---"
    systemctl disable systemd-networkd-wait-online 2>/dev/null || true

    echo "--- SSH config ---"
    sed -i "s/#PermitRootLogin.*/PermitRootLogin yes/" /etc/ssh/sshd_config
    sed -i "s/#PasswordAuthentication.*/PasswordAuthentication yes/" /etc/ssh/sshd_config

    echo "--- Hostname ---"
    echo "begonia-alarm" > /etc/hostname

    echo "--- Locale ---"
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
    locale-gen 2>/dev/null || true
    echo "LANG=en_US.UTF-8" > /etc/locale.conf
' || echo "Warning: some services may have issues in nspawn"

echo "=== Service configuration complete ==="