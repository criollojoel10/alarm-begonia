#!/bin/bash
# =============================================================================
# firstboot.sh — Ejecutar en primer arranque de Arch begonia
# =============================================================================
set -euo pipefail

# Sincronizar hora (crítico para pacman TLS)
timedatectl set-ntp true || true

# Inicializar keyring de pacman
pacman-key --init
pacman-key --populate archlinuxarm

# Regenerar initramfs con mkinitcpio
mkinitcpio -P || true

# Generar config de red
systemctl enable --now systemd-resolved
ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf

# Configurar NetworkManager
systemctl enable --now NetworkManager

# Configurar Tailscale
if command -v tailscale &>/dev/null; then
    systemctl enable --now tailscaled
fi

echo ""
echo "=== Arch Linux ARM begonia ready ==="
echo "  Hostname: $(hostname)"
echo "  Kernel: $(uname -r)"
echo "  Arch: $(uname -m)"
echo ""
echo "  For Tailscale:"
echo "    tailscale up --accept-routes"
echo ""
