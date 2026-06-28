# Arch Linux ARM para Xiaomi Redmi Note 8 Pro (begonia)

> **Arch Linux ARM** corriendo como sistema operativo nativo en begonia, portado desde el **hardware enablement de postmarketOS** — kernel mainline, DTB, módulos y firmware — pero reemplazando completamente Alpine/musl por **glibc/pacman/systemd**.

## 📋 Arquitectura

```
Arch Linux ARM begonia
├── boot.img
│   ├── Kernel mainline 6.x (linux-postmarketos-mediatek-mt6785)
│   ├── DTB/DTBO correcto para begonia (MT6785 Helio G90T)
│   └── initramfs mínimo Arch (busca rootfs por label ArchRoot)
│
└── rootfs.img
    ├── Arch Linux ARM aarch64
    ├── glibc (libc 2.42+)
    ├── pacman
    ├── systemd (multi-user.target)
    ├── openssh
    ├── NetworkManager + tailscale
    └── módulos del kernel pmOS + firmware mediatek
```

### NO es ❌

- Arch dentro de postmarketOS
- chroot / proot / contenedor
- Alpine host + Arch userspace
- dualboot
- Termux

### SÍ es ✅

- Rootfs real Arch Linux ARM aarch64
- `/sbin/init` → systemd de Arch
- `pacman` → glibc
- USB OTG / dongle Ethernet USB funcionales
- Batería real (FGU MT6360 desde vendor kernel — opcional)

## 🧬 Origen

Este proyecto se inspira en el port **"Nothing Phone (1) Spacewar - ALARM"** (Arch Linux ARM Red Moon), que corre Arch Linux ARM aarch64 sobre el kernel y habilitación de postmarketOS.

El mismo enfoque se aplica aquí:

```
pmOS kernel + dtb → boot.img
Arch Linux ARM rootfs → systemd + glibc + pacman
Initramfs adaptado → puente entre ambos
```

## 🏗️ Pipeline de construcción

### Workflow 1: Build pmOS base (`01_build_pmos_base.yml`)

Construye una imagen postmarketOS de referencia para extraer:
- `boot.img` — kernel mainline 6.x + DTB + initramfs pmOS
- `modules.tar.zst` — módulos del kernel compilados
- `firmware.tar.zst` — firmware mediatek/MT6785
- `deviceinfo` y cmdline

Habilita drivers USB Ethernet (AX88179, RTL8152, SMSC95XX) y WiFi Realtek/MediaTek para soporte de dongles.

### Workflow 2: Build Arch ARM (`02_build_alarm_begonia.yml`)

Construye la imagen final:
1. Descarga `ArchLinuxARM-aarch64-latest.tar.gz`
2. Crea rootfs ext4 de 8 GB
3. Inyecta módulos y firmware desde pmOS
4. Configura systemd (multi-user, sshd, NetworkManager, tailscaled)
5. Construye initramfs Arch mínimo
6. Repackea boot.img con kernel pmOS + initramfs Arch
7. Publica `boot-begonia-arch.img` + `rootfs-archlinuxarm-begonia.img.xz`

## 📥 Descarga

Las imágenes nightly están en [Releases](https://github.com/criollojoel10/alarm-begonia/releases/tag/nightly):

| Archivo | Descripción |
|---|---|
| `boot-begonia-arch.img` | Boot image (kernel + initramfs Arch) |
| `rootfs-archlinuxarm-begonia.img.xz` | Rootfs Arch Linux ARM (8 GB, comprimido) |
| `SHA256SUMS.txt` | Checksums |

## 🔧 Instalación

### Requisitos

- Redmi Note 8 Pro (begonia) con bootloader desbloqueado
- PC con fastboot y cable USB
- ~10 minutos

### Pasos

```bash
# 1. Extraer los archivos
tar -xzf alarm-begonia-nightly.tar.gz
cd alarm-begonia-nightly

# 2. Decomprimir rootfs (si es .xz)
xz -d rootfs-archlinuxarm-begonia.img.xz

# 3. Bootear a fastboot
adb reboot bootloader
# o: apagar → Volumen ARRIBA + ENCENDIDO

# 4. Verificar conexión
fastboot devices

# 5. Flashear boot (kernel + initramfs)
fastboot flash boot boot-begonia-arch.img

# 6. Flashear rootfs (userdata)
fastboot flash userdata rootfs-archlinuxarm-begonia.img

# Opcional: borrar datos previos
fastboot erase userdata  # ⚠️ borra TODO

# 7. Reiniciar
fastboot reboot
```

### Primer arranque

El teléfono bootea directamente a **Arch Linux ARM console** (sin GUI). El initramfs busca:
1. Label `ArchRoot` (recomendado)
2. Label `pmOS_root` (compatibilidad)
3. Partición `userdata`

Para conectarse:
```bash
# USB Networking (PC)
sudo ip link set enp0s20f0u1 up
sudo dhclient enp0s20f0u1
ssh root@192.168.2.15  # IP asignada por DHCP

# USB Ethernet dongle (conecta a router)
ssh root@<IP>

# Credenciales
# Usuario: root
# Contraseña: root
```

Post-install:
```bash
# Inicializar keyring de pacman
pacman-key --init
pacman-key --populate archlinuxarm

# Regenerar initramfs local
mkinitcpio -P

# Configurar red
systemctl enable --now NetworkManager
nmtui  # o: nmcli dev wifi connect SSID password "PASS"

# Tailscale
systemctl enable --now tailscaled
tailscale up --accept-routes
```

## 📊 Estado del hardware

| Componente | Estado | Notas |
|---|---|---|
| **Booteo** | ✅ | Initramfs encuentra rootfs |
| **Kernel** | ✅ | Mainline 6.16.4+ |
| **RAM** | ✅ | 6 GB completos |
| **Almacenamiento** | ✅ | Partición userdata (64/128 GB) |
| **USB OTG** | ✅ | Ethernet dongles, teclados |
| **USB Ethernet** | ✅ | AX88179, RTL8152, SMSC95XX |
| **WiFi dongle** | ✅ | RTL8192EU (TP-Link WN821N) |
| **Pantalla** | ✅ | Framebuffer console |
| **Touchscreen** | ✅ | Input multitouch |
| **GPU** | ✅ | Panfrost (Mali-G76) |
| **WiFi interno** | ❌ | MT7663 — sin driver mainline |
| **Bluetooth** | ❌ | MT7663 — sin driver mainline |
| **Audio** | ❌ | En desarrollo |
| **Cámara** | ❌ | En desarrollo |
| **Módem 4G** | ❌ | MT6779 — sin driver mainline |
| **Batería (FGU)** | ⏳ | En port desde vendor kernel |

## 📁 Estructura del repo

```
alarm-begonia/
├── .github/workflows/
│   ├── 01_build_pmos_base.yml      # Extraer pmOS boot/modules/firmware
│   └── 02_build_alarm_begonia.yml  # Construir Arch ARM final
├── initramfs/
│   ├── init                        # Initramfs mínimo Arch
│   ├── build-initramfs.sh          # Script para crear initramfs
│   └── files.list                  # Archivos a incluir
├── rootfs/
│   ├── prepare-rootfs.sh           # Preparación del rootfs
│   ├── packages.txt                # Paquetes a instalar
│   ├── services.sh                 # Configuración de servicios
│   └── firstboot.sh                # Primer arranque
├── boot/
│   ├── repack-bootimg.sh           # Reconstruir boot.img
│   └── cmdline.txt                 # Kernel cmdline
├── flash/
│   └── flash-begonia-arch.sh       # Script de flasheo
└── README.md
```

## 🥭 Créditos

- **postmarketOS** — habilitación de hardware para begonia
- **Nothing Phone (1) ALARM** — inspiración del port
- **Arch Linux ARM** — rootfs base
- **Kupfer Linux** — documentación del enfoque Arch en dispositivos móviles
- **Vivi AI** — pipeline de construcción automatizado

## 📜 Licencia

MIT — construido sobre software libre de la comunidad.
