#!/bin/bash
# =============================================================================
# flash-begonia-arch.sh — Flashear Arch Linux ARM en Redmi Note 8 Pro (begonia)
# =============================================================================
# Uso: ./flash-begonia-arch.sh [--wipe]
# =============================================================================
set -euo pipefail

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${G}[+]${NC} $1"; }
warn()  { echo -e "${Y}[!]${NC} $1"; }
err()   { echo -e "${R}[-]${NC} $1"; }

WIPE="${1:-}"

# Verificar fastboot
if ! command -v fastboot &>/dev/null; then
    err "fastboot no encontrado. Instalar android-tools."
    exit 1
fi

# Archivos necesarios
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOOT_IMG="$SCRIPT_DIR/boot-begonia-arch.img"
ROOTFS_XZ="$SCRIPT_DIR/rootfs-archlinuxarm-begonia.img.xz"
ROOTFS_IMG="$SCRIPT_DIR/rootfs-archlinuxarm-begonia.img"

# Verificar archivos
if [ ! -f "$BOOT_IMG" ]; then
    err "No encontrado: boot-begonia-arch.img"
    exit 1
fi

if [ ! -f "$ROOTFS_IMG" ] && [ ! -f "$ROOTFS_XZ" ]; then
    err "No encontrado: rootfs-archlinuxarm-begonia.img (.xz)"
    exit 1
fi

# Descomprimir rootfs si es necesario
if [ ! -f "$ROOTFS_IMG" ] && [ -f "$ROOTFS_XZ" ]; then
    info "Descomprimiendo rootfs..."
    xz -d -v "$ROOTFS_XZ"
fi

info "=== Arch Linux ARM para begonia ==="
info "Boot:  $BOOT_IMG ($(du -h "$BOOT_IMG" | cut -f1))"
info "Root:  $ROOTFS_IMG ($(du -h "$ROOTFS_IMG" | cut -f1))"

echo ""
info "1. Apaga el teléfono"
info "2. Conecta USB a la PC"
info "3. Mantén VOLUMEN ARRIBA + ENCENDIDO (modo fastboot)"
echo ""

read -p "¿Teléfono en fastboot? (ENTER para continuar) " -r

info "Verificando dispositivo..."
FASTBOOT_DEV=$(fastboot devices 2>&1 | head -1)
if [ -z "$FASTBOOT_DEV" ]; then
    err "No se detecta dispositivo en fastboot"
    err "Conecta el USB y verifica drivers"
    exit 1
fi
info "Dispositivo: $FASTBOOT_DEV"

if [ "$WIPE" = "--wipe" ]; then
    warn "⚠️  Borrando userdata (TODOS LOS DATOS SE PERDERÁN)"
    fastboot erase userdata 2>/dev/null || true
fi

info "Flasheando boot.img..."
fastboot flash boot "$BOOT_IMG"

info "Flasheando rootfs..."
fastboot flash userdata "$ROOTFS_IMG"

info "Reiniciando..."
fastboot reboot

echo ""
echo -e "${G}✅ Arch Linux ARM instalado en begonia${NC}"
echo ""
echo "Después del primer boot:"
echo "  1. Conéctate por SSH (usb networking o ethernet dongle)"
echo "  2. Usuario: root / Contraseña: root"
echo "  3. Ejecuta: /root/firstboot.sh"
echo ""
echo "Opciones de red:"
echo "  - USB Networking: conecta USB a PC, ejecuta 'sudo ip link set enp0s20f0u1 up && sudo dhclient enp0s20f0u1' en PC"
echo "  - Ethernet dongle: conecta adaptador USB-C → Ethernet"
echo "  - Tailscale: tailscale up --accept-routes"