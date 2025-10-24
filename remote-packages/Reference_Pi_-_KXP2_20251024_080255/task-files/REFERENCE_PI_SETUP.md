# Reference Pi Setup Guide - RonR Network Image Creation

## Overview

This guide walks through setting up a reference Raspberry Pi to create golden master images using RonR-RPi-image-utils with direct network write to the deployment server.

**Goal**: Create optimized master images (5-10 minutes) directly on server without SD card removal.

## Architecture

```
Reference Pi (Raspberry Pi OS)
   ↓ Install RonR tools
   ↓ Mount server NFS share
   ↓ Run: sudo image-backup /mnt/deployment-server/kxp2_master.img
   ↓ Image written directly to server over network (5-10 min)
   ↓ Image ready to deploy immediately!
```

## Prerequisites

- Reference Pi running Raspberry Pi OS with fully configured KXP2/RXP2 software
- Reference Pi connected to management network (VLAN 101: 192.168.101.x)
- SSH access to reference Pi
- Ubuntu deployment server NFS export configured (completed)

---

## Part 1: Reference Pi - Install RonR Tools

**SSH to your reference Pi** (replace `<pi-ip>` with your Pi's IP address):

```bash
ssh pi@<pi-ip>
# Or: ssh captureworks@<pi-ip>
```

### Step 1: Clone RonR Repository

```bash
cd ~
git clone https://github.com/seamusdemora/RonR-RPi-image-utils.git
```

**Expected output:**
```
Cloning into 'RonR-RPi-image-utils'...
remote: Enumerating objects: ...
Receiving objects: 100% ...
```

### Step 2: Install RonR Utilities

```bash
cd ~/RonR-RPi-image-utils
sudo install --mode=755 image-* /usr/local/sbin/
```

### Step 3: Verify Installation

```bash
which image-backup
# Should output: /usr/local/sbin/image-backup

image-backup --help
# Should display usage information
```

---

## Part 2: Reference Pi - Install NFS Client

### Step 1: Install NFS Client Package

```bash
sudo apt update
sudo apt install -y nfs-common
```

### Step 2: Create Mount Point

```bash
sudo mkdir -p /mnt/deployment-server
```

### Step 3: Test Mount (Temporary)

```bash
# Mount server's images directory
sudo mount -t nfs 192.168.101.146:/opt/rpi-deployment/images /mnt/deployment-server

# Verify mount worked
df -h | grep deployment-server
# Should show: 192.168.101.146:/opt/rpi-deployment/images

# List contents (should see test images)
ls -lh /mnt/deployment-server/
# Expected: kxp2_test_v1.0.img, rxp2_test_v1.0.img
```

**If mount fails**, check:
- Reference Pi can ping server: `ping 192.168.101.146`
- NFS server is running: SSH to server and run `sudo systemctl status nfs-server`
- Firewall allows NFS: Check UFW or iptables

### Step 4: Unmount (We'll make it permanent next)

```bash
sudo umount /mnt/deployment-server
```

---

## Part 3: Reference Pi - Configure Permanent NFS Mount

### Option A: Automatic Mount in /etc/fstab (Recommended)

**Add mount to /etc/fstab for automatic mounting on boot:**

```bash
# Back up fstab first
sudo cp /etc/fstab /etc/fstab.backup

# Add NFS mount entry
sudo bash -c 'cat >> /etc/fstab << EOF

# RPi Deployment Server - Images Directory (NFS)
# Allows direct write of golden master images to server
192.168.101.146:/opt/rpi-deployment/images /mnt/deployment-server nfs defaults,_netdev 0 0
EOF'
```

**Mount all entries in fstab:**

```bash
sudo mount -a
```

**Verify mount:**

```bash
df -h | grep deployment-server
ls /mnt/deployment-server/
```

### Option B: Manual Mount (Alternative)

If you prefer to mount manually each time:

```bash
# Mount when needed
sudo mount -t nfs 192.168.101.146:/opt/rpi-deployment/images /mnt/deployment-server

# Unmount when done
sudo umount /mnt/deployment-server
```

---

## Part 4: Create Golden Master Image

### Preparation Checklist

Before creating the golden image, ensure:

- [ ] Reference Pi has all KXP2/RXP2 software installed and tested
- [ ] All configuration is complete (network, camera settings, etc.)
- [ ] System is updated: `sudo apt update && sudo apt upgrade`
- [ ] Unnecessary packages removed: `sudo apt autoremove`
- [ ] Temporary files cleaned: `sudo apt clean`
- [ ] Test images work correctly (record video, verify playback)
- [ ] NFS mount is active: `df -h | grep deployment-server`

### Create KXP2 Golden Master

**This is the magic command!**

```bash
# Ensure mount is active
df -h | grep deployment-server

# Create golden master image (5-10 minutes)
sudo image-backup /mnt/deployment-server/kxp2_master.img

# What happens:
# 1. RonR scans running system with rsync
# 2. Calculates minimum size needed (only used space)
# 3. Creates partition table and filesystems
# 4. Copies all files efficiently
# 5. Automatically shrinks to minimum size
# 6. Writes directly to server over NFS
# 7. Image ready on server immediately!
```

**Expected output:**
```
Creating image file...
Imaging /dev/mmcblk0 to /mnt/deployment-server/kxp2_master.img
Checking partition table...
Creating partitions...
Copying root filesystem...
Shrinking image...
Image creation complete!
Final size: 3.2GB (from 32GB SD card)
```

**Timing:**
- Small system (2-4GB used): ~5 minutes
- Medium system (4-6GB used): ~7 minutes
- Large system (6-8GB used): ~10 minutes

### Verify Image on Server

**From reference Pi, verify via SSH:**

```bash
ssh captureworks@192.168.101.146 "ls -lh /opt/rpi-deployment/images/kxp2_master.img"
```

**Or check locally:**

```bash
ls -lh /mnt/deployment-server/kxp2_master.img
```

---

## Part 5: Create RXP2 Golden Master (If Separate Reference Pi)

If you have a separate reference Pi configured with RXP2 software:

```bash
# Repeat all steps above on RXP2 reference Pi
# ...then create RXP2 image:

sudo image-backup /mnt/deployment-server/rxp2_master.img
```

---

## Part 6: Post-Creation Tasks (On Ubuntu Server)

**SSH back to the Ubuntu deployment server:**

```bash
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146
cd /opt/rpi-deployment
```

### Step 1: Verify Image Arrived

```bash
ls -lh /opt/rpi-deployment/images/kxp2_master.img
# Should show file size (typically 2-5GB)
```

### Step 2: Calculate Checksum

```bash
sha256sum /opt/rpi-deployment/images/kxp2_master.img \
    > /opt/rpi-deployment/images/kxp2_master.img.sha256

# View checksum
cat /opt/rpi-deployment/images/kxp2_master.img.sha256
```

### Step 3: Set Proper Permissions

```bash
chmod 644 /opt/rpi-deployment/images/kxp2_master.img
chown captureworks:captureworks /opt/rpi-deployment/images/kxp2_master.img
```

### Step 4: Register in Database

```bash
# Get image stats
IMAGE_SIZE=$(stat -c%s /opt/rpi-deployment/images/kxp2_master.img)
IMAGE_CHECKSUM=$(cat /opt/rpi-deployment/images/kxp2_master.img.sha256 | cut -d' ' -f1)

# Register in database
sqlite3 /opt/rpi-deployment/database/deployment.db <<EOF
INSERT INTO master_images
(product_type, version, filename, checksum, size_bytes, is_active, created_at, notes)
VALUES (
    'KXP2',
    '1.0.0',
    'kxp2_master.img',
    '${IMAGE_CHECKSUM}',
    ${IMAGE_SIZE},
    1,
    CURRENT_TIMESTAMP,
    'Created via RonR image-backup direct network write'
);
EOF

# Verify registration
sqlite3 /opt/rpi-deployment/database/deployment.db \
    "SELECT product_type, version, filename, size_bytes, is_active FROM master_images;"
```

### Step 5: Test Deployment

Deploy image to a test Pi to verify it boots and works correctly:

```bash
# Connect test Pi to VLAN 151 (deployment network)
# Monitor deployment:
tail -f /opt/rpi-deployment/logs/deployment_$(date +%Y%m%d).log

# Watch for:
# - DHCP assignment
# - Hostname assignment
# - Image download
# - Status reports (starting, downloading, verifying, success)
```

---

## Troubleshooting

### Mount Fails: "Connection refused"

**Problem**: NFS server not accessible

**Solutions**:
```bash
# On server, verify NFS is running:
sudo systemctl status nfs-server

# Verify export is active:
sudo exportfs -v

# Restart NFS if needed:
sudo systemctl restart nfs-server
sudo exportfs -ra
```

### Mount Fails: "Permission denied"

**Problem**: Network restrictions

**Solutions**:
```bash
# Verify reference Pi is on correct network:
ip addr  # Should show 192.168.101.x

# On server, verify export allows your network:
sudo exportfs -v
# Should show: 192.168.101.0/24
```

### Image Creation Fails: "No space left on device"

**Problem**: Not enough space on server

**Solutions**:
```bash
# On server, check available space:
df -h /opt/rpi-deployment/images/

# Free up space if needed:
# - Remove old test images
# - Clean up old backups
```

### Image Creation Very Slow

**Problem**: Network speed or Pi performance

**Solutions**:
- Verify 1 Gbps network connection
- Check network switch performance
- Ensure reference Pi is on same local network as server (VLAN 101)
- Close unnecessary applications on reference Pi

### Image Won't Boot on Test Pi

**Problem**: Incomplete or corrupted image

**Solutions**:
```bash
# Verify image integrity with checksum
sha256sum /opt/rpi-deployment/images/kxp2_master.img

# Re-create image if needed
# On reference Pi:
sudo image-backup /mnt/deployment-server/kxp2_master_v2.img
```

---

## Future Updates

### Incremental Image Updates

One of RonR's best features: **ultra-fast incremental updates**

```bash
# After updating software on reference Pi:
# Create new version in 30-60 seconds (only changed files!)
sudo image-backup /mnt/deployment-server/kxp2_master_v1.1.img

# RonR only copies changed files and re-shrinks
# Much faster than full re-image!
```

### Version Management

```bash
# Keep multiple versions on server:
kxp2_master_v1.0.img  # Original
kxp2_master_v1.1.img  # Bug fix
kxp2_master_v2.0.img  # Major update

# Register each in database with different version numbers
# Set is_active=1 for the version you want to deploy
```

---

## Summary

**Server Setup (One-time):**
- ✅ NFS server installed and configured
- ✅ /opt/rpi-deployment/images exported to 192.168.101.0/24
- ✅ Service enabled and running

**Reference Pi Setup (One-time per Pi):**
- ✅ RonR tools installed
- ✅ NFS client installed
- ✅ Permanent mount configured

**Image Creation (5-10 minutes per image):**
```bash
sudo image-backup /mnt/deployment-server/kxp2_master.img
```

**Result**: Optimized, bootable golden master image ready to deploy!

---

**Next Steps**: Test deployment to single Pi (Phase 10), then proceed to mass deployment (Phase 12)
