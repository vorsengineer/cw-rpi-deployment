# Alpine Linux Netboot with SSH - RPi5 Deployment System

**Document Version**: 1.0
**Date**: 2025-10-24
**Purpose**: Enable SSH access to Raspberry Pi during network boot (RAM kernel stage) for installation monitoring and debugging

---

## Overview

This guide explains how to configure Alpine Linux netboot for Raspberry Pi 5, providing SSH access during the deployment process **before** the image is written to the SD card.

### Why Alpine Linux?

- **Lightweight**: ~50MB download (boots in seconds on 1Gbps network)
- **SSH included**: OpenSSH available immediately after boot
- **Python support**: Can run pi_installer.py for deployment
- **Low RAM usage**: ~100-150MB, leaves plenty for installation
- **Debugging tools**: Package manager (apk) for additional tools
- **Production-ready**: Used extensively in containers, embedded systems

### What You Gain

```
During Pi Boot:
├── Pi boots Alpine Linux into RAM
├── Network configured from DHCP
├── SSH server starts automatically
├── YOU SSH INTO PI → Monitor/debug installation
├── Run installer manually or automatically
└── Full control over deployment process
```

**Use Cases:**
- 🔍 Monitor installation progress in real-time
- 🐛 Debug connection issues from Pi side
- 📊 Run diagnostic scripts on Pi
- ⚙️ Test installer without SD card writes
- 📡 Capture network traffic on Pi side
- 🔧 Troubleshoot deployment failures

---

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Download Alpine Linux](#download-alpine-linux)
4. [Configure TFTP Boot Files](#configure-tftp-boot-files)
5. [Create SSH Overlay](#create-ssh-overlay)
6. [Testing Alpine Boot](#testing-alpine-boot)
7. [Integrate Installer](#integrate-installer)
8. [Usage Workflow](#usage-workflow)
9. [Troubleshooting](#troubleshooting)

---

## Architecture

### Current Boot Flow (Standard Deployment)

```
Pi boots → DHCP → TFTP (kernel8.img) → Boots kernel →
Runs pi_installer.py → Downloads image → Writes SD card → Reboots
```

**Problem:** No access to Pi during installation, can't see what's happening

### New Boot Flow (Alpine with SSH)

```
Pi boots → DHCP → TFTP (Alpine kernel) → Boots Alpine into RAM →
SSH available → Run installer (manual or auto) → Monitor progress
→ Download image → Write SD card → Reboot (or stay in Alpine for debugging)
```

**Benefit:** Full SSH access during entire installation process

---

## Prerequisites

### On Deployment Server

- ✅ TFTP server running (dnsmasq)
- ✅ DHCP server configured (192.168.151.1)
- ✅ TFTP root: `/tftpboot/`
- ✅ Disk space: ~100MB for Alpine files

### Required Tools

```bash
# Install tools for creating Alpine overlay
sudo apt-get install cpio gzip wget

# Verify TFTP is running
sudo systemctl status dnsmasq
```

### Network Requirements

- Pi must be on VLAN 151 (deployment network)
- Pi will get IP from dnsmasq (192.168.151.100-250)
- SSH port 22 accessible on deployment network

---

## Download Alpine Linux

### Option 1: Latest Release (Recommended)

```bash
# Create Alpine directory in TFTP root
sudo mkdir -p /tftpboot/alpine
cd /tftpboot/alpine

# Download Alpine Linux ARM64 netboot files
# Visit: https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/aarch64/

# Download these specific files (example for Alpine 3.19):
sudo wget https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/aarch64/alpine-netboot-3.19.0-aarch64.tar.gz

# Extract
sudo tar -xzf alpine-netboot-3.19.0-aarch64.tar.gz

# Files extracted:
# - boot/vmlinuz-rpi              (kernel)
# - boot/initramfs-rpi            (initramfs)
# - boot/modloop-rpi              (kernel modules)
# - boot/dtbs-rpi/                (device trees)
```

### Option 2: Use Setup Script (Automated)

```bash
# Use the automated setup script (created below)
sudo /opt/rpi-deployment/scripts/setup_alpine_netboot.sh
```

### Verify Download

```bash
ls -lh /tftpboot/alpine/boot/
# Should see:
# vmlinuz-rpi         (~9MB)
# initramfs-rpi       (~30MB)
# modloop-rpi         (~10MB)
# dtbs-rpi/           (directory)
```

---

## Configure TFTP Boot Files

### Step 1: Create Alpine Boot Configuration

Create `/tftpboot/config-alpine.txt`:

```ini
# Raspberry Pi 5 Alpine Linux Netboot Configuration
# This boots Alpine Linux into RAM for deployment with SSH access

[pi5]
kernel=alpine/boot/vmlinuz-rpi
initramfs alpine/boot/initramfs-rpi followkernel
device_tree=bcm2712-rpi-5-b.dtb

[all]
# Enable UART for debugging (optional)
enable_uart=1

# Increase GPU memory (minimal for headless)
gpu_mem=16

# Network boot parameters
boot_delay=1

# Alpine boot parameters
cmdline=alpine/cmdline.txt
```

### Step 2: Create Alpine Command Line

Create `/tftpboot/alpine/cmdline.txt`:

```
modules=loop,squashfs,sd-mod,usb-storage quiet console=tty1 modloop=alpine/boot/modloop-rpi
```

### Step 3: Update dnsmasq for Alpine Boot

You can switch between standard boot and Alpine boot by changing DHCP/TFTP configuration.

**Option A: Always boot Alpine** (for testing phase)

Edit `/etc/dnsmasq.conf`:
```conf
# Use Alpine config for Pi 5
dhcp-boot=tag:efi-arm64,config-alpine.txt
```

**Option B: Conditional boot** (advanced - based on MAC address)

```conf
# Standard boot for most Pis
dhcp-boot=tag:efi-arm64,config.txt

# Alpine boot for specific test Pi (replace with actual MAC)
dhcp-host=dc:a6:32:xx:xx:xx,192.168.151.200,set:alpine
dhcp-boot=tag:alpine,config-alpine.txt
```

### Step 4: Restart dnsmasq

```bash
sudo systemctl restart dnsmasq

# Verify configuration
sudo dnsmasq --test
```

---

## Create SSH Overlay

Alpine Linux uses **apkovl** (Alpine Package Overlay) for persistent configuration. We'll create one with SSH keys and auto-start scripts.

### Step 1: Generate SSH Key (if you don't have one)

```bash
# On your workstation or deployment server
ssh-keygen -t ed25519 -C "rpi-deployment" -f ~/.ssh/rpi_deployment_key

# Copy public key
cat ~/.ssh/rpi_deployment_key.pub
```

### Step 2: Create Overlay Directory Structure

```bash
# Create overlay working directory
mkdir -p /tmp/alpine-overlay/etc/ssh
mkdir -p /tmp/alpine-overlay/root/.ssh
mkdir -p /tmp/alpine-overlay/etc/local.d
mkdir -p /tmp/alpine-overlay/installer
```

### Step 3: Add SSH Authorized Keys

```bash
# Add your public key
cat > /tmp/alpine-overlay/root/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAAC3... your-key-here rpi-deployment
EOF

chmod 600 /tmp/alpine-overlay/root/.ssh/authorized_keys
```

### Step 4: Configure SSH Server

```bash
# Create SSH config
cat > /tmp/alpine-overlay/etc/ssh/sshd_config << 'EOF'
# Minimal SSH config for Alpine netboot
PermitRootLogin yes
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no
X11Forwarding no
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/ssh/sftp-server
EOF
```

### Step 5: Create Auto-Start Script

```bash
# Create startup script that runs after boot
cat > /tmp/alpine-overlay/etc/local.d/deployment.start << 'EOF'
#!/bin/sh
# RPi Deployment Network Boot Startup Script

# Wait for network
sleep 2

# Log boot information
echo "=== RPi Deployment Alpine Boot ===" > /var/log/deployment.log
echo "Booted at: $(date)" >> /var/log/deployment.log
echo "IP Address: $(ip -4 addr show eth0 | grep inet | awk '{print $2}')" >> /var/log/deployment.log
echo "Gateway: $(ip route | grep default | awk '{print $3}')" >> /var/log/deployment.log

# Test connectivity to deployment server
if ping -c 1 -W 2 192.168.151.1 > /dev/null 2>&1; then
    echo "✓ Deployment server reachable" >> /var/log/deployment.log
else
    echo "✗ Cannot reach deployment server!" >> /var/log/deployment.log
fi

# Optional: Auto-run installer
# Uncomment to automatically start installation on boot
# python3 /installer/pi_installer.py >> /var/log/deployment.log 2>&1 &

echo "SSH server started, ready for connections" >> /var/log/deployment.log
echo "Connect with: ssh root@$(ip -4 addr show eth0 | grep inet | awk '{print $2}' | cut -d'/' -f1)" >> /var/log/deployment.log
EOF

chmod +x /tmp/alpine-overlay/etc/local.d/deployment.start
```

### Step 6: Create Installer Integration Script

```bash
# Script to run installer from Alpine
cat > /tmp/alpine-overlay/installer/run_deployment.sh << 'EOF'
#!/bin/sh
# Run RPi deployment installer from Alpine

echo "=== Starting RPi Deployment ==="
echo "Downloading installer from server..."

# Download installer from deployment server
wget http://192.168.151.1/installer/pi_installer.py -O /installer/pi_installer.py

# Install Python dependencies if needed
apk add --no-cache python3 py3-pip

# Run installer
python3 /installer/pi_installer.py

echo "=== Deployment Complete ==="
EOF

chmod +x /tmp/alpine-overlay/installer/run_deployment.sh
```

### Step 7: Package Overlay

```bash
# Create apkovl tarball
cd /tmp/alpine-overlay
tar -czf /tftpboot/alpine/deployment.apkovl.tar.gz .

# Set permissions
sudo chown -R root:root /tftpboot/alpine/deployment.apkovl.tar.gz
sudo chmod 644 /tftpboot/alpine/deployment.apkovl.tar.gz

# Clean up
cd /
rm -rf /tmp/alpine-overlay
```

### Step 8: Configure Alpine to Load Overlay

Update `/tftpboot/alpine/cmdline.txt`:

```
modules=loop,squashfs,sd-mod,usb-storage quiet console=tty1 modloop=alpine/boot/modloop-rpi apkovl=http://192.168.151.1/alpine/deployment.apkovl.tar.gz
```

**Note:** Alpine will download and apply this configuration on every boot

---

## Testing Alpine Boot

### Step 1: Configure Test Pi

1. Connect Pi to VLAN 151 (deployment network)
2. Ensure blank SD card inserted (optional for testing)
3. Power on Pi

### Step 2: Watch Server Logs

```bash
# Terminal 1: Monitor DHCP/TFTP
sudo tcpdump -i eth1 -n -v port 67 or port 68 or port 69

# Terminal 2: Monitor dnsmasq
sudo tail -f /var/log/syslog | grep dnsmasq

# Terminal 3: Monitor TFTP transfers
sudo tail -f /var/log/syslog | grep TFTP
```

### Step 3: Boot Sequence

```
Expected output:
1. Pi requests DHCP → Gets 192.168.151.x from dnsmasq
2. Pi requests config-alpine.txt via TFTP
3. Pi downloads vmlinuz-rpi, initramfs-rpi, modloop-rpi
4. Pi downloads deployment.apkovl.tar.gz
5. Alpine boots (10-15 seconds)
6. SSH server starts
```

### Step 4: Connect via SSH

```bash
# Find Pi IP (check dnsmasq logs or use nmap)
nmap -sn 192.168.151.0/24

# SSH to Pi (using your private key)
ssh -i ~/.ssh/rpi_deployment_key root@192.168.151.100

# You should see:
Welcome to Alpine Linux
rpi-alpine:~#
```

### Step 5: Verify Environment

```bash
# On Alpine Pi
ip addr                          # Check network config
ping 192.168.151.1               # Test server connectivity
curl http://192.168.151.1/health # Test deployment API
cat /var/log/deployment.log      # View boot log
free -h                          # Check RAM usage (~100MB used)
df -h                            # Check filesystem (all in RAM)
```

---

## Integrate Installer

### Option 1: Manual Execution (Recommended for Testing)

```bash
# SSH to Pi
ssh root@192.168.151.100

# Download and run installer manually
wget http://192.168.151.1/installer/pi_installer.py
python3 pi_installer.py

# Monitor in real-time
tail -f /var/log/deployment.log
```

### Option 2: Automatic Execution on Boot

Uncomment the auto-run line in `/etc/local.d/deployment.start`:

```bash
# This will auto-start installer on boot
python3 /installer/pi_installer.py >> /var/log/deployment.log 2>&1 &
```

### Option 3: HTTP-Triggered Execution

Create a simple web endpoint that the Pi polls:

```python
# On server: Add to deployment_server.py
@app.route('/trigger/<mac_address>', methods=['POST'])
def trigger_deployment(mac_address):
    # Trigger deployment for specific Pi
    return jsonify({'action': 'start_deployment'})
```

```bash
# On Pi: Poll for trigger
while true; do
    curl -X POST http://192.168.151.1/trigger/$(cat /sys/class/net/eth0/address)
    sleep 5
done
```

---

## Usage Workflow

### Typical Deployment Session

```bash
# 1. Power on Pi (boots Alpine)
# 2. Pi gets IP from DHCP, boots Alpine, starts SSH

# 3. SSH into Pi from workstation
ssh root@192.168.151.100

# 4. Verify connectivity
rpi-alpine:~# ping 192.168.151.1
rpi-alpine:~# curl http://192.168.151.1/health

# 5. Run connectivity test
rpi-alpine:~# wget http://192.168.151.1/scripts/test_deployment_connectivity.sh
rpi-alpine:~# sh test_deployment_connectivity.sh

# 6. Run installer (manual monitoring)
rpi-alpine:~# /installer/run_deployment.sh

# 7. In another terminal: Watch progress
ssh root@192.168.151.100 'tail -f /var/log/deployment.log'

# 8. After installation complete, reboot to SD card
rpi-alpine:~# reboot
```

### Debugging Session

```bash
# SSH into Pi during failed installation
ssh root@192.168.151.100

# Check what went wrong
rpi-alpine:~# cat /var/log/deployment.log
rpi-alpine:~# dmesg | tail -50
rpi-alpine:~# ip route
rpi-alpine:~# curl -v http://192.168.151.1/api/config

# Test network
rpi-alpine:~# ping -c 5 192.168.151.1
rpi-alpine:~# tcpdump -i eth0 -n port 80

# Check SD card
rpi-alpine:~# lsblk
rpi-alpine:~# fdisk -l /dev/mmcblk0

# Fix and retry without reboot
rpi-alpine:~# python3 /installer/pi_installer.py
```

---

## Troubleshooting

### Pi doesn't boot Alpine

**Symptom:** Pi hangs at "Loading..." or rainbow screen

**Check:**
```bash
# Verify files exist
ls -lh /tftpboot/alpine/boot/

# Check TFTP logs
sudo tail -f /var/log/syslog | grep TFTP

# Verify dnsmasq config
grep dhcp-boot /etc/dnsmasq.conf
```

**Solution:**
- Ensure all Alpine files downloaded correctly
- Verify config-alpine.txt syntax
- Check cmdline.txt has correct paths

---

### SSH connection refused

**Symptom:** `ssh: connect to host 192.168.151.100 port 22: Connection refused`

**Check:**
```bash
# Find Pi's actual IP
sudo grep "DHCPACK" /var/log/syslog | tail -5

# Test if Pi is reachable
ping 192.168.151.100
```

**Solution:**
- Verify SSH overlay was applied (check apkovl downloaded)
- Ensure SSH server started (may take 30 seconds after boot)
- Check firewall on deployment network

---

### Can't connect to deployment server from Alpine

**Symptom:** `curl: Failed to connect to 192.168.151.1`

**Check on Pi:**
```bash
ip route           # Should have default via 192.168.151.1
ping 192.168.151.1 # Should get replies
```

**Solution:**
- Verify DHCP gave correct gateway
- Check deployment server services running
- Test with diagnostic script

---

### Installer fails in Alpine

**Symptom:** Python errors or missing dependencies

**Solution:**
```bash
# Install Python and dependencies
apk add --no-cache python3 py3-pip
apk add --no-cache py3-requests py3-cryptography

# Update installer with Alpine-specific paths
```

---

## Advanced Configuration

### Custom Alpine Packages

Add to overlay's `/etc/apk/world`:
```
python3
py3-pip
curl
wget
tcpdump
nano
```

### Persistent Logs

Mount tmpfs for logs:
```bash
mkdir -p /tmp/alpine-overlay/etc/fstab
echo "tmpfs /var/log tmpfs defaults,size=100m 0 0" > /tmp/alpine-overlay/etc/fstab
```

### Custom Welcome Message

```bash
cat > /tmp/alpine-overlay/etc/motd << 'EOF'
═══════════════════════════════════════════════════════
 RPi5 Deployment System - Alpine Linux Network Boot
═══════════════════════════════════════════════════════

 Connected to deployment network: 192.168.151.1

 Commands:
   /installer/run_deployment.sh  - Start deployment
   cat /var/log/deployment.log   - View boot log

 Documentation:
   /opt/rpi-deployment/docs/ALPINE_NETBOOT_SSH_SETUP.md

═══════════════════════════════════════════════════════
EOF
```

---

## Security Considerations

### SSH Key Management

- ✅ Use SSH keys only (no passwords)
- ✅ Different key per deployment environment
- ✅ Rotate keys regularly
- ❌ Never commit private keys to git

### Network Isolation

- VLAN 151 is isolated (no internet access recommended)
- Only deployment server accessible
- SSH only from management network (192.168.101.x)

### Temporary Nature

- Alpine environment is temporary (RAM only)
- No persistence between boots
- Perfect for secure deployment scenarios

---

## Comparison: Alpine vs Standard Boot

| Feature | Standard Boot | Alpine Boot |
|---------|---------------|-------------|
| Boot time | ~30 seconds | ~15 seconds |
| Download size | ~9MB (kernel only) | ~50MB (full OS) |
| SSH access | ❌ No | ✅ Yes |
| Debugging | ❌ Limited | ✅ Full access |
| RAM usage | ~50MB | ~150MB |
| Flexibility | Run installer only | Full Linux environment |
| Use case | Production deployment | Testing, debugging |

---

## Next Steps

1. **Test Alpine boot** with single Pi
2. **Verify SSH access** and connectivity
3. **Run installer manually** and monitor
4. **Debug any issues** with full access
5. **Switch to auto-deployment** once tested
6. **Document any customizations** for your environment

---

## Files Created

```
/tftpboot/
├── config-alpine.txt              (Alpine boot config)
├── alpine/
│   ├── boot/
│   │   ├── vmlinuz-rpi            (kernel)
│   │   ├── initramfs-rpi          (initramfs)
│   │   ├── modloop-rpi            (modules)
│   │   └── dtbs-rpi/              (device trees)
│   ├── cmdline.txt                (kernel command line)
│   └── deployment.apkovl.tar.gz   (SSH overlay)
```

---

**Document Last Updated**: 2025-10-24
**Alpine Version**: 3.19 (latest stable)
**Raspberry Pi**: Pi 5 (ARM64/aarch64)
**Deployment System**: v2.0
