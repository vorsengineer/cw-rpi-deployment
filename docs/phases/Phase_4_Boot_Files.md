## Phase 4: Boot Files Preparation

### Step 4.1: Download Raspberry Pi Boot Files

```bash
# Clone Raspberry Pi firmware repository
cd /tmp
git clone --depth=1 https://github.com/raspberrypi/firmware

# Copy boot files to TFTP directory
sudo cp firmware/boot/bootcode.bin /tftpboot/
sudo cp firmware/boot/start*.elf /tftpboot/
sudo cp firmware/boot/fixup*.dat /tftpboot/
```

### Step 4.2: Get iPXE Boot Files for ARM64

```bash
# Download or build iPXE for ARM64
cd /tmp
git clone https://github.com/ipxe/ipxe.git
cd ipxe/src

# Build for ARM64
make bin-arm64-efi/ipxe.efi EMBED=boot.ipxe

# Copy to TFTP
sudo cp bin-arm64-efi/ipxe.efi /tftpboot/bootfiles/boot.ipxe
```

### Step 4.3: Create iPXE Boot Script

```bash
sudo nano /tftpboot/bootfiles/boot.ipxe
```

```ipxe
#!ipxe

echo ========================================
echo KXP/RXP Deployment System - Network Boot
echo ========================================

# Get network configuration
dhcp

# Set server IP (deployment network)
set server_ip 192.168.151.1

echo Server IP: ${server_ip}
echo Client IP: ${ip}
echo Starting installation...

# Download and execute Python installer
kernel http://${server_ip}/boot/vmlinuz
initrd http://${server_ip}/boot/initrd.img
imgargs vmlinuz root=/dev/ram0 rw init=/opt/installer/run_installer.sh server=${server_ip}
boot || goto failed

:failed
echo Boot failed! Press any key to retry...
prompt
goto retry

:retry
chain --autofree boot.ipxe
```

---

