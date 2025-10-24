# Quick Start: Create Golden Master Image

**Goal**: Create KXP2/RXP2 golden master image in 5-10 minutes using RonR direct network write.

---

## ✅ Server Setup (COMPLETED)

The Ubuntu deployment server is ready:
- ✅ NFS server installed and running
- ✅ `/opt/rpi-deployment/images` exported to management network (192.168.101.0/24)
- ✅ Export active and tested
- ✅ Registration script ready: `/opt/rpi-deployment/scripts/register_master_image.sh`

**Server IP**: 192.168.101.146
**NFS Export**: `/opt/rpi-deployment/images`

You can verify from the server:
```bash
showmount -e localhost
# Should show: /opt/rpi-deployment/images 192.168.101.0/24
```

---

## 📋 Reference Pi Checklist

### Prerequisites
- [ ] Reference Pi running Raspberry Pi OS
- [ ] KXP2 or RXP2 software fully installed and tested
- [ ] Reference Pi connected to management network (VLAN 101)
- [ ] Reference Pi has IP address 192.168.101.x
- [ ] Can ping deployment server: `ping 192.168.101.146`

---

## 🚀 Quick Setup (Copy-Paste Commands)

### Step 1: Install RonR Tools (5 min)

SSH to your reference Pi and run:

```bash
# Clone RonR repository
cd ~
git clone https://github.com/seamusdemora/RonR-RPi-image-utils.git

# Install utilities
cd ~/RonR-RPi-image-utils
sudo install --mode=755 image-* /usr/local/sbin/

# Verify installation
which image-backup
# Should output: /usr/local/sbin/image-backup
```

### Step 2: Install NFS Client (2 min)

```bash
# Install NFS client
sudo apt update
sudo apt install -y nfs-common

# Create mount point
sudo mkdir -p /mnt/deployment-server
```

### Step 3: Configure Permanent Mount (2 min)

```bash
# Back up fstab
sudo cp /etc/fstab /etc/fstab.backup

# Add NFS mount
sudo bash -c 'cat >> /etc/fstab << "EOF"

# RPi Deployment Server - Images Directory (NFS)
192.168.101.146:/opt/rpi-deployment/images /mnt/deployment-server nfs defaults,_netdev 0 0
EOF'

# Mount all
sudo mount -a

# Verify mount
df -h | grep deployment-server
ls /mnt/deployment-server/
# Should show existing test images
```

**If mount fails**:
```bash
# Try manual mount to diagnose
sudo mount -t nfs 192.168.101.146:/opt/rpi-deployment/images /mnt/deployment-server

# Check for errors
# Common issues:
# - Reference Pi not on 192.168.101.x network
# - NFS server not running (check on server)
# - Firewall blocking port 2049
```

### Step 4: Create Golden Master Image (5-10 min)

**THE MAGIC COMMAND:**

```bash
# For KXP2 product:
sudo image-backup /mnt/deployment-server/kxp2_master.img

# For RXP2 product:
sudo image-backup /mnt/deployment-server/rxp2_master.img
```

**What happens**:
1. RonR scans your running system
2. Calculates minimum size (only used space)
3. Creates partition table
4. Copies files via rsync
5. Automatically shrinks image
6. Writes directly to server over network
7. Done! (~5-10 minutes)

**Progress**: You'll see output like:
```
Creating image file...
Imaging /dev/mmcblk0 to /mnt/deployment-server/kxp2_master.img
Copying root filesystem... [===>    ] 45%
```

**Verify on server** (via SSH from Pi):
```bash
ssh captureworks@192.168.101.146 "ls -lh /opt/rpi-deployment/images/kxp2_master.img"
# Password: Jankycorpltd01
```

---

## 🔄 Back to Server: Register Image

After the image is created, SSH back to the deployment server:

```bash
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146
cd /opt/rpi-deployment
```

**Use the automated registration script:**

```bash
# For KXP2:
./scripts/register_master_image.sh KXP2 1.0.0 kxp2_master.img

# For RXP2:
./scripts/register_master_image.sh RXP2 1.0.0 rxp2_master.img
```

**What the script does**:
- ✅ Calculates SHA256 checksum
- ✅ Sets proper permissions (644)
- ✅ Registers in database with metadata
- ✅ Sets as active image
- ✅ Creates .sha256 checksum file

**Verify registration**:
```bash
sqlite3 /opt/rpi-deployment/database/deployment.db \
    "SELECT product_type, version, filename, size_bytes, is_active FROM master_images;"
```

---

## ✅ Success Criteria

You should now have:
- [ ] Image file on server: `/opt/rpi-deployment/images/kxp2_master.img`
- [ ] Checksum file: `/opt/rpi-deployment/images/kxp2_master.img.sha256`
- [ ] Database entry with `is_active = 1`
- [ ] Permissions: 644 (rw-r--r--)
- [ ] Image size: ~2-5GB (shrunk from 32GB)

---

## 🧪 Test Deployment

Deploy to a single test Pi to verify image works:

1. **Connect test Pi to VLAN 151** (deployment network)
2. **Monitor logs**:
   ```bash
   tail -f /opt/rpi-deployment/logs/deployment_$(date +%Y%m%d).log
   ```
3. **Power on test Pi** (network boot enabled in EEPROM)
4. **Watch for**:
   - DHCP assignment (192.168.151.100-250)
   - Hostname assignment (KXP2-VENUE-###)
   - Image download progress
   - Installation status (starting → downloading → verifying → success)
5. **Verify boot**: Test Pi should boot from SD card with new hostname

---

## 🐛 Quick Troubleshooting

### Reference Pi Can't Mount NFS Share

```bash
# Verify network connectivity
ping 192.168.101.146

# Check reference Pi IP (should be 192.168.101.x)
ip addr show

# Try manual mount with verbose output
sudo mount -v -t nfs 192.168.101.146:/opt/rpi-deployment/images /mnt/deployment-server
```

### Image Creation Fails

```bash
# Check free space on server
df -h /opt/rpi-deployment/images/

# Check NFS mount is still active
df -h | grep deployment-server

# Try again with different filename
sudo image-backup /mnt/deployment-server/kxp2_master_v2.img
```

### Image Won't Deploy

```bash
# Verify image exists
ls -lh /opt/rpi-deployment/images/kxp2_master.img

# Check database registration
sqlite3 /opt/rpi-deployment/database/deployment.db \
    "SELECT * FROM master_images WHERE filename='kxp2_master.img';"

# Check deployment API
curl http://192.168.151.1:5001/health

# Test API response
curl -X POST http://192.168.151.1:5001/api/config \
    -H "Content-Type: application/json" \
    -d '{"product_type": "KXP2", "venue_code": "TEST", "serial_number": "12345678"}'
# Should return JSON with image_url pointing to kxp2_master.img
```

---

## 📚 Full Documentation

**Detailed guide**: `/opt/rpi-deployment/docs/REFERENCE_PI_SETUP.md`

**Phase 11 docs**: `/opt/rpi-deployment/docs/phases/Phase_11_Master_Image.md` (to be created)

---

## ⏱️ Timeline Summary

| Task | Time | Status |
|------|------|--------|
| Server NFS setup | 10 min | ✅ COMPLETE |
| Reference Pi - Install RonR | 5 min | 📋 YOUR TURN |
| Reference Pi - Install NFS client | 2 min | 📋 YOUR TURN |
| Reference Pi - Configure mount | 2 min | 📋 YOUR TURN |
| Create golden image (RonR) | 5-10 min | 📋 YOUR TURN |
| Register on server | 2 min | 📋 YOUR TURN |
| **TOTAL** | **~25-30 min** | |

**Old method (dd + pishrink)**: ~45-60 minutes + SD card removal
**New method (RonR direct)**: ~25-30 minutes, no SD card removal! 🎉

---

## 🎯 Next Steps

1. **Complete reference Pi setup** (Steps 1-3 above)
2. **Create golden master image** (Step 4 above)
3. **Register image on server** (automated script)
4. **Test deployment** to single Pi
5. **Phase 12**: Mass deployment procedures

---

**Ready? Start with Step 1 on your reference Pi!** 🚀
