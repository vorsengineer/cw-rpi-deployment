# Raspberry Pi Network Boot Testing Guide

**Date**: 2025-10-23
**Test**: Single Pi network boot on VLAN 151

---

## Multi-Terminal Monitoring Setup

Open **4 SSH sessions** to the deployment server (192.168.101.146) and run these commands:

### Terminal 1: Network Traffic Monitor 🌐
```bash
# Monitor ALL deployment network traffic (DHCP, TFTP, HTTP)
sudo /opt/rpi-deployment/scripts/monitor_deployment.sh --all
```

**What to watch for**:
- `DHCP Discover` from Pi (broadcast request for IP)
- `DHCP Offer` from server (offering 192.168.151.100-250)
- `DHCP Request` from Pi (accepting the offer)
- `DHCP ACK` from server (confirming lease)
- TFTP `RRQ` requests for config.txt, cmdline.txt, kernel8.img
- HTTP `GET /images/kxp2_test_v1.0.img` (50MB download)

---

### Terminal 2: Deployment Server Logs 📋
```bash
# Watch deployment API logs in real-time
sudo journalctl -u rpi-deployment -f --no-pager
```

**What to watch for**:
- `POST /api/config` request from Pi
- Hostname assignment message (e.g., "Assigned KXP2-CORO-010")
- MAC address and serial number logged
- Image serving started

**Alternative** (if you want deployment.log instead):
```bash
tail -f /opt/rpi-deployment/logs/deployment_$(date +%Y%m%d).log
```

---

### Terminal 3: System Logs (dnsmasq + nginx) 🔧
```bash
# Monitor dnsmasq DHCP/TFTP activity
sudo tail -f /var/log/dnsmasq.log
```

**What to watch for**:
- `DHCPDISCOVER` and `DHCPOFFER` messages
- DHCP lease assignment (IP address given to Pi)
- TFTP file transfers (sent /tftpboot/config.txt, kernel8.img)
- Option 43 delivery ("Raspberry Pi Boot")

**Alternative** (web server logs):
```bash
sudo tail -f /var/log/nginx/deployment-access.log
```

---

### Terminal 4: Database Watch (Optional) 💾
```bash
# Watch deployment history table update in real-time
watch -n 2 'sqlite3 /opt/rpi-deployment/database/deployment.db "SELECT id, hostname, deployment_status, started_at, completed_at FROM deployment_history ORDER BY started_at DESC LIMIT 3;"'
```

**What to watch for**:
- New row appears when Pi calls API
- `deployment_status` changes: started → downloading → installing → success
- `completed_at` timestamp when finished

---

## Testing Procedure

### Step 1: Start All Monitoring (in separate terminals)
- Open 4 SSH sessions
- Run the commands above in each terminal
- Arrange windows so you can see all 4 at once

### Step 2: Power On the Raspberry Pi
**⚠️ IMPORTANT**: Ensure Pi is:
- Connected to VLAN 151 switch port ✅
- Has blank/wiped SD card inserted ✅
- Powered off (ready to power on)

**Then**: Plug in power to the Pi

### Step 3: Observe Boot Sequence (Timeline)

#### Phase 1: DHCP Negotiation (0-10 seconds)
**Terminal 1** (Network): Watch for DHCP Discover/Offer/Request/ACK
**Terminal 3** (dnsmasq): Watch for DHCP lease assignment

**Expected Output (dnsmasq log)**:
```
DHCPDISCOVER(eth1) b8:27:eb:xx:xx:xx
DHCPOFFER(eth1) 192.168.151.100 b8:27:eb:xx:xx:xx
DHCPREQUEST(eth1) 192.168.151.100 b8:27:eb:xx:xx:xx
DHCPACK(eth1) 192.168.151.100 b8:27:eb:xx:xx:xx
```

✅ **Success**: Pi receives IP address (192.168.151.100-250)

#### Phase 2: TFTP Boot Files (10-40 seconds)
**Terminal 1** (Network): Watch for TFTP read requests (RRQ)
**Terminal 3** (dnsmasq): Watch for "sent /tftpboot/..." messages

**Expected Output (dnsmasq log)**:
```
sent /tftpboot/config.txt to 192.168.151.100
sent /tftpboot/cmdline.txt to 192.168.151.100
sent /tftpboot/kernel8.img to 192.168.151.100
sent /tftpboot/bcm2712-rpi-5-b.dtb to 192.168.151.100
```

✅ **Success**: All boot files transferred (~10MB total)

#### Phase 3: Kernel Boot (40-70 seconds)
**What happens**: Kernel loads, pi_installer.py starts
**Visible**: May see brief pause, then HTTP activity starts

#### Phase 4: Configuration Request (70-90 seconds)
**Terminal 1** (Network): Watch for HTTP POST to /api/config
**Terminal 2** (Deployment): Watch for API request and hostname assignment
**Terminal 4** (Database): Watch for new deployment_history row

**Expected Output (deployment logs)**:
```
INFO - POST /api/config - Hostname assignment request
INFO - Assigned hostname: KXP2-CORO-010
INFO - MAC: b8:27:eb:xx:xx:xx, Serial: xxxxxxxxx
INFO - Image: kxp2_test_v1.0.img (52428800 bytes)
```

✅ **Success**: Hostname assigned, config returned

#### Phase 5: Image Download (90-180 seconds)
**Terminal 1** (Network): Watch for HTTP GET /images/kxp2_test_v1.0.img
**Terminal 2** (Deployment): Watch for download progress

**Expected**: 50MB test image downloads at ~100 Mbps (~4-5 seconds actual transfer)

✅ **Success**: HTTP 200 OK, full image transferred

#### Phase 6: Installation (180-240 seconds)
**What happens**: Pi writes image to SD card
**Visible**: Pi installer reports status back to server via POST /api/status

**Expected Status Updates**:
- `status: downloading` → `status: verifying` → `status: installing` → `status: success`

**Terminal 4** (Database): Watch deployment_status column change

✅ **Success**: deployment_status = "success", completed_at timestamp set

#### Phase 7: Reboot (240+ seconds)
**What happens**: Pi reboots from SD card with assigned hostname
**Visible**: Network activity stops, Pi should boot from SD card

✅ **Success**: Pi boots, you can SSH to it (if networking configured in image)

---

## Verification After Boot

### Check Deployment History
```bash
sqlite3 /opt/rpi-deployment/database/deployment.db << EOF
SELECT
    id,
    hostname,
    mac_address,
    serial_number,
    deployment_status,
    started_at,
    completed_at
FROM deployment_history
ORDER BY started_at DESC
LIMIT 1;
EOF
```

**Expected Result**:
```
id: 3
hostname: KXP2-CORO-010
mac_address: b8:27:eb:xx:xx:xx
serial_number: <Pi serial>
deployment_status: success
started_at: 2025-10-23 HH:MM:SS
completed_at: 2025-10-23 HH:MM:SS
```

### Check Hostname Pool
```bash
sqlite3 /opt/rpi-deployment/database/deployment.db << EOF
SELECT hostname, mac_address, status, assigned_date
FROM hostname_pool
WHERE hostname LIKE 'KXP2-CORO-%'
ORDER BY assigned_date DESC
LIMIT 5;
EOF
```

**Expected Result**: Newly assigned hostname with status='assigned'

---

## Troubleshooting

### Problem: No DHCP Activity
**Symptoms**: No DHCP Discover in Terminal 1 or Terminal 3

**Checks**:
```bash
# Verify dnsmasq is running
sudo systemctl status dnsmasq

# Check dnsmasq is bound to eth1
sudo netstat -uln | grep :67

# Verify switch port is on VLAN 151
# (Check in UniFi controller)
```

**Fix**: Restart dnsmasq if needed: `sudo systemctl restart dnsmasq`

---

### Problem: DHCP Works, No TFTP
**Symptoms**: Pi gets IP but doesn't download boot files

**Checks**:
```bash
# Test TFTP manually
tftp 192.168.151.1
> get config.txt
> quit

# Check file permissions
ls -la /tftpboot/

# Verify Option 43 is configured
grep "dhcp-option=43" /etc/dnsmasq.conf
```

**Fix**: Ensure Option 43 is set and files are readable

---

### Problem: TFTP Works, No HTTP API Call
**Symptoms**: Boot files transfer but no /api/config request

**Possible Causes**:
- Kernel may not be compatible with Pi 5
- cmdline.txt may have wrong installer path
- Network configuration issue in kernel

**Checks**:
```bash
# Verify kernel is ARM64
file /tftpboot/kernel8.img
# Should show: "Linux kernel ARM64 boot executable Image"

# Check cmdline.txt
cat /tftpboot/cmdline.txt
# Should reference pi_installer.py or HTTP installer
```

---

### Problem: API Call Fails
**Symptoms**: HTTP POST to /api/config returns error

**Checks**:
```bash
# Test API manually
curl -X POST http://192.168.151.1:5001/api/config \
  -H "Content-Type: application/json" \
  -d '{"product_type": "KXP2", "venue_code": "CORO", "serial_number": "TEST", "mac_address": "b8:27:eb:11:22:33"}'

# Check deployment server logs
sudo journalctl -u rpi-deployment -n 50

# Verify test images exist and are active
sqlite3 /opt/rpi-deployment/database/deployment.db "SELECT * FROM master_images WHERE is_active=1;"
```

---

## Expected Timeline

| Time | Phase | What's Happening |
|------|-------|------------------|
| 0s | Power On | Pi boots, seeks network |
| 5s | DHCP | Pi gets IP address |
| 15s | TFTP | Downloads config.txt, cmdline.txt |
| 30s | TFTP | Downloads kernel8.img (9.5MB) |
| 45s | Boot | Kernel loads and starts |
| 60s | Init | pi_installer.py begins |
| 75s | API | Requests configuration, gets hostname |
| 80s | Download | Starts downloading test image (50MB) |
| 85s | Download | Image transfer complete (~5 seconds at 100Mbps) |
| 90s | Write | Writes image to SD card |
| 120s | Verify | Checks partial checksum |
| 130s | Finalize | Creates firstrun.sh, reports success |
| 140s | Reboot | Pi reboots from SD card |

**Total Time**: ~2-3 minutes (with 50MB test image)

---

## Success Indicators

✅ **DHCP**: Pi receives IP 192.168.151.100-250
✅ **TFTP**: All 4 boot files transferred successfully
✅ **API**: Hostname assigned (visible in logs and database)
✅ **Download**: 50MB image transferred via HTTP
✅ **Database**: deployment_history shows status='success'
✅ **Reboot**: Pi boots from SD card

---

## Ready to Begin?

1. ✅ Verify all 4 monitoring terminals are running
2. ✅ Ensure Pi is on VLAN 151, powered off
3. ✅ Blank SD card inserted
4. **Power on the Pi** and watch the magic happen! 🎉

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Next**: Document results in PHASE10_HARDWARE_TEST_RESULTS.md
