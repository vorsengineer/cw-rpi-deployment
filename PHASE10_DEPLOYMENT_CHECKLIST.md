# Phase 10 - First Pi Deployment Checklist

**Date**: 2025-10-24
**Test Pis**: 2x Raspberry Pi 5 with blank SD cards
**Network**: VLAN 151 (deployment network)
**Test Image**: kxp2_test_v1.0.img (50MB) and rxp2_test_v1.0.img (50MB)

---

## ✅ Pre-Boot Checklist

### Infrastructure Status
- [x] **dnsmasq** running (DHCP + TFTP server)
- [x] **nginx** running (HTTP image server)
- [x] **rpi-deployment** running (Deployment API on port 5001)
- [x] **rpi-web** running (Web dashboard on port 5000)

### Network Configuration
- [x] **Deployment network**: 192.168.151.1/24 configured on eth1
- [x] **UniFi DHCP**: DISABLED on VLAN 151 (verified by user)
- [x] **Test Pis**: Connected to VLAN 151 ports

### Master Images
- [x] **KXP2 test image**: kxp2_test_v1.0.img (50MB) - ACTIVE
- [x] **RXP2 test image**: rxp2_test_v1.0.img (50MB) - ACTIVE
- [x] **KXP2 golden master**: kxp2_master.img (25GB) - Available for later testing
- [x] **Database**: All images registered and accessible

### Boot Files (TFTP)
- [x] **/tftpboot/config.txt** - Pi 5 boot configuration
- [x] **/tftpboot/kernel8.img** - ARM64 Linux kernel (9.5MB)
- [x] **/tftpboot/bcm2712-rpi-5-b.dtb** - Device tree for Pi 5
- [x] **/tftpboot/cmdline.txt** - Kernel command line with installer script URL

### Test Batches
- [x] **Batch #6**: KXP2 @ BRPA (1 device, priority 100) - ACTIVE
- [x] **Batch #7**: RXP2 @ ARIA (1 device, priority 90) - ACTIVE

### Monitoring Setup
- [x] **Tmux session**: phase10-monitor created with 3 windows
  - Window 0: Network traffic (tcpdump + dnsmasq logs)
  - Window 1: Deployment logs (application + systemd)
  - Window 2: Live status (batches, deployments, services)

---

## 📋 Expected Deployment Timeline (Per Pi)

### Phase 1: Network Boot (0-30 seconds)
**What happens:**
- Pi powers on, EEPROM initiates network boot
- **DHCP DISCOVER** broadcast on VLAN 151
- Server responds with **DHCP OFFER** (IP: 192.168.151.100-250)
- Pi sends **DHCP REQUEST**, server sends **DHCP ACK** with:
  - IP address assignment
  - Option 43: "Raspberry Pi Boot" (CRITICAL for Pi 5)
  - TFTP server: 192.168.151.1
  - Boot filename: config.txt

**What to monitor:**
```bash
# In tmux window 0 (Network), watch for:
- "DHCP request from [MAC]" in dnsmasq.log
- "DHCP, Request from [MAC]" in tcpdump
- IP assignment confirmation
```

**Success indicators:**
- ✅ DHCP request appears in logs
- ✅ IP assigned (192.168.151.100-250)
- ✅ Option 43 delivered
- ✅ No DHCP timeouts or retries

**Failure indicators:**
- ❌ No DHCP request (check Pi connection to VLAN 151)
- ❌ DHCP conflict (UniFi DHCP still active)
- ❌ Pi requests iPXE/PXE instead of config.txt (wrong DHCP options)

---

### Phase 2: TFTP Boot File Download (30-60 seconds)
**What happens:**
- Pi requests **config.txt** via TFTP
- Pi downloads **kernel8.img** (9.5MB) via TFTP
- Pi downloads **bcm2712-rpi-5-b.dtb** via TFTP
- Pi reads cmdline.txt for kernel parameters

**What to monitor:**
```bash
# In tmux window 0, watch for:
- "sent /tftpboot/config.txt" in dnsmasq.log
- "sent /tftpboot/kernel8.img" in dnsmasq.log
- "sent /tftpboot/bcm2712-rpi-5-b.dtb" in dnsmasq.log
```

**Success indicators:**
- ✅ config.txt downloaded (small file, instant)
- ✅ kernel8.img download starts (9.5MB, ~5-10 seconds)
- ✅ bcm2712-rpi-5-b.dtb downloaded
- ✅ No TFTP timeouts

**Failure indicators:**
- ❌ "file not found" errors in dnsmasq
- ❌ TFTP timeouts (check file permissions: 644, root:nogroup)
- ❌ Pi stuck in TFTP loop (check boot file paths in dnsmasq.conf)

---

### Phase 3: Kernel Boot (60-90 seconds)
**What happens:**
- Linux kernel boots on Pi
- Network drivers initialize
- Pi requests DHCP again (kernel network stack)
- Installer script starts: **pi_installer.py**

**What to monitor:**
```bash
# In tmux window 1 (Deployment), watch for:
- New HTTP requests to deployment server
- "Installer started" messages (if logging enabled)
```

**Success indicators:**
- ✅ Second DHCP request from same MAC (kernel requesting IP)
- ✅ HTTP activity to port 5001 (deployment API)
- ✅ Installer script starts

**Failure indicators:**
- ❌ Kernel panic (check cmdline.txt syntax)
- ❌ No network after kernel boot (driver issue)
- ❌ Installer script doesn't start (check cmdline.txt URL)

---

### Phase 4: Hostname Assignment (90-95 seconds)
**What happens:**
- Installer calls **POST /api/config** with:
  - Product type (KXP2 or RXP2)
  - Venue code (from batch)
  - Serial number (from /proc/cpuinfo)
- Server assigns hostname from pool
- For KXP2: Sequential from batch (e.g., KXP2-BRPA-333)
- For RXP2: Serial-based (e.g., RXP2-ARIA-ABC12345)

**What to monitor:**
```bash
# In tmux window 1, watch for:
- POST /api/config request
- Hostname assignment log entry
- Response with assigned hostname

# In tmux window 2 (Status), watch for:
- Batch remaining_count decrement
- New entry in deployment_history
```

**Success indicators:**
- ✅ POST /api/config returns 200 OK
- ✅ Hostname assigned and logged
- ✅ Batch counter decrements
- ✅ deployment_history entry created

**Failure indicators:**
- ❌ 400 Bad Request (check request format)
- ❌ 500 Internal Server Error (check database connection)
- ❌ "No available hostnames" error (check hostname pool)

---

### Phase 5: Image Download (95 seconds - 2 minutes)
**What happens:**
- Installer downloads test image via HTTP
- **kxp2_test_v1.0.img** (50MB) or **rxp2_test_v1.0.img** (50MB)
- Download from: http://192.168.151.1/images/[filename]
- Progress logged every 10MB

**What to monitor:**
```bash
# In tmux window 1, watch for:
- "Downloading image: [filename]"
- Download progress updates
- "Download complete" message

# In nginx logs:
- GET /images/kxp2_test_v1.0.img
```

**Success indicators:**
- ✅ Download starts
- ✅ Progress updates appear
- ✅ Download completes (50MB in ~30-60 seconds on 1Gbps)
- ✅ No HTTP errors

**Failure indicators:**
- ❌ 404 Not Found (image file missing)
- ❌ 403 Forbidden (check nginx permissions)
- ❌ Download stalls (network issue, check eth1)
- ❌ Checksum mismatch (corrupted download)

---

### Phase 6: SD Card Write (2-3 minutes)
**What happens:**
- Installer writes image to **/dev/mmcblk0**
- Uses dd with 4MB blocks
- Progress logged every 10MB
- Sync and flush to ensure data integrity

**What to monitor:**
```bash
# In tmux window 1, watch for:
- "Writing image to SD card..."
- Write progress updates (MB written)
- "Write complete" message
- fsync operation
```

**Success indicators:**
- ✅ Write starts immediately after download
- ✅ Progress updates every ~5 seconds
- ✅ Write completes successfully
- ✅ fsync completes (data flushed to SD card)

**Failure indicators:**
- ❌ "No SD card detected" (check if SD card inserted)
- ❌ "SD card write-protected" (check SD card lock switch)
- ❌ Write errors (bad SD card)
- ❌ Progress stalls (corrupted SD card)

---

### Phase 7: Hostname Customization (3 minutes)
**What happens:**
- Installer mounts boot partition
- Modifies **/boot/firstrun.sh** to set hostname
- Hostname injected: KXP2-BRPA-333 or RXP2-ARIA-ABC12345
- Unmounts partition

**What to monitor:**
```bash
# In tmux window 1, watch for:
- "Customizing hostname..."
- "Hostname set to: [hostname]"
- firstrun.sh modification success
```

**Success indicators:**
- ✅ Boot partition mounted
- ✅ firstrun.sh modified
- ✅ Hostname injected correctly
- ✅ Partition unmounted safely

**Failure indicators:**
- ❌ Mount failed (check partition table)
- ❌ firstrun.sh not found (image issue)
- ❌ Write failed (SD card issue)

---

### Phase 8: Status Report & Reboot (3-4 minutes)
**What happens:**
- Installer sends **POST /api/status** with "success"
- Logs deployment completion
- Database updated (deployment_history)
- Pi reboots from SD card

**What to monitor:**
```bash
# In tmux window 1, watch for:
- POST /api/status with status="success"
- "Deployment complete" message
- "Rebooting..." message

# In tmux window 2 (Status), watch for:
- deployment_history new entry
- Batch status update (completed if last device)
```

**Success indicators:**
- ✅ Status "success" reported
- ✅ Deployment logged in database
- ✅ Batch updated
- ✅ Pi reboots

**Failure indicators:**
- ❌ Status "failed" reported
- ❌ Error in deployment_history
- ❌ Pi doesn't reboot

---

### Phase 9: First Boot from SD Card (4-5 minutes)
**What happens:**
- Pi boots from SD card (not network)
- firstrun.sh executes on first boot
- Hostname set to assigned value
- System configured and ready

**What to monitor:**
```bash
# Optional: Connect monitor/keyboard to Pi
# Or SSH after boot (if SSH enabled in image)

# Check hostname:
ssh kxp@[IP-from-DHCP]
hostname  # Should show: KXP2-BRPA-333
```

**Success indicators:**
- ✅ Pi boots from SD card (no network boot)
- ✅ Hostname correctly set
- ✅ System operational

**Failure indicators:**
- ❌ Pi tries to network boot again (SD card not bootable)
- ❌ Hostname not set (firstrun.sh didn't execute)
- ❌ Boot errors

---

## 🚀 Ready to Deploy!

### Final Pre-Boot Steps:

1. **Attach to monitoring session:**
   ```bash
   tmux attach -t phase10-monitor
   ```

2. **Open web dashboard in browser:**
   ```
   http://192.168.101.146:5000
   ```
   Navigate to "Batches" page to watch live updates.

3. **Verify test batches are active:**
   ```bash
   # In a separate terminal:
   curl -s http://192.168.101.146:5000/api/batches?status=active | python3 -m json.tool
   ```

4. **Ready to power on Pi #1 (KXP2)**

---

## 🎯 What to Watch For (Quick Reference)

### In Tmux Window 0 (Network):
- DHCP request → IP assignment → TFTP downloads

### In Tmux Window 1 (Deployment):
- Hostname assignment → Image download → SD write → Success report

### In Tmux Window 2 (Status):
- Batch counter decrements → deployment_history entry appears

### In Web Dashboard:
- Real-time batch progress updates (if WebSocket working)

---

## 📸 Capturing Evidence

For Phase 10 documentation:

1. **Screenshot web dashboard** showing active batches
2. **Save tcpdump output** (first 100 packets)
3. **Save deployment log** snippet showing complete workflow
4. **Take photo of Pi** with monitor showing boot process (optional)
5. **SSH to Pi** after boot and run:
   ```bash
   hostname
   ip addr
   df -h
   uname -a
   ```

---

## ⚠️ Troubleshooting Quick Guide

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| No DHCP request | Pi not on VLAN 151 | Check cable connection |
| DHCP conflict | UniFi DHCP active | Disable UniFi DHCP on VLAN 151 |
| TFTP file not found | Wrong path in dnsmasq | Check /tftpboot/ files exist |
| Hostname assignment fails | Empty hostname pool | Import kart numbers for venue |
| Image download fails | nginx not serving | Check nginx config and restart |
| SD write fails | Bad SD card | Try different SD card |
| Pi network boots again | SD write incomplete | Check SD card integrity |

---

**YOU ARE NOW READY TO POWER ON THE FIRST TEST PI!** 🚀

When ready, simply:
1. Attach to tmux: `tmux attach -t phase10-monitor`
2. Power on Pi #1
3. Watch the magic happen! ✨

Expected total time: **3-5 minutes** from power-on to successful boot from SD card.
