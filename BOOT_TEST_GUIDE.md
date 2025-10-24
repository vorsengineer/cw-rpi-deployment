# Raspberry Pi Network Boot Test Guide

## Current Status

✅ **ALL BOOT FILES READY** (22/22 validation checks passed)

### What Was Fixed

The kernel panic issue has been resolved:

**Problem**: Kernel was trying to mount `/dev/ram0` as a filesystem
```
Kernel panic - not syncing: VFS: Unable to mount root fs on "/dev/ram0"
```

**Solution**: Updated `/tftpboot/cmdline.txt` to use modern initramfs

**Old cmdline.txt** (broken):
```
root=/dev/ram0 init=/usr/bin/python3 ...
```

**New cmdline.txt** (fixed):
```
console=serial0,115200 console=tty1 rw initrd=initrd.img ip=dhcp
```

## Quick Start - Boot Testing

### Method 1: Live Monitoring (Recommended)

```bash
# Terminal 1: Start boot monitor
sudo /opt/rpi-deployment/scripts/monitor_pi_boot.sh

# Terminal 2 (optional): Watch deployment logs
/opt/rpi-deployment/logs/tail-all.sh

# Power on your Raspberry Pi on VLAN 151
```

### Method 2: Manual Monitoring

```bash
# Watch DHCP/TFTP traffic
sudo tcpdump -i eth1 -n 'port 67 or port 68 or port 69'

# Watch dnsmasq logs
sudo tail -f /var/log/dnsmasq.log

# Watch deployment server logs
tail -f /opt/rpi-deployment/logs/deployment_$(date +%Y%m%d).log
```

## Expected Boot Sequence

1. **DHCP Request** (5-10 seconds)
   - Pi broadcasts DHCP DISCOVER
   - Server responds with OFFER (IP: 192.168.151.100-250)
   - Pi accepts with DHCP REQUEST
   - Server confirms with DHCP ACK
   - Look for: `DHCP DISCOVER` → `DHCP OFFER` in monitor

2. **TFTP Boot Files** (30-60 seconds)
   - Pi requests config.txt (312 bytes)
   - Pi requests kernel8.img (9.5 MB) ⏳
   - Pi requests bcm2712-rpi-5-b.dtb (77 KB)
   - Pi requests initrd.img (95 MB) ⏳⏳
   - Look for: `TFTP REQUEST: config.txt` in monitor

3. **Kernel Boot** (10-15 seconds)
   - Kernel loads into RAM
   - Kernel extracts initrd.img to tmpfs (automatic with modern kernels)
   - Kernel runs `/init` script
   - Look for: Kernel messages on serial/HDMI console

4. **Init Script** (20-30 seconds)
   - Mounts proc, sys, dev filesystems
   - Configures network with dhclient
   - Tests connectivity to 192.168.151.1
   - Banner: `RPi5 Network Deployment System v2.0`
   - Look for: Network configuration messages

5. **Deployment Installer** (5-10 minutes depending on image size)
   - Checks for SD card
   - Requests hostname from server (API call to :5001/api/config)
   - Downloads master image via HTTP
   - Writes image to SD card
   - Configures hostname
   - Reboots to production OS
   - Look for: HTTP requests to 192.168.151.1:5001 in monitor

## What To Watch For

### Success Indicators ✅

- DHCP lease assigned (192.168.151.100-250)
- All 5 TFTP files downloaded successfully
- No kernel panic
- Init script banner appears
- Network configured (eth0 gets IP from DHCP)
- Can ping 192.168.151.1
- Installer starts and connects to API

### Failure Indicators ❌

- No DHCP response (check VLAN 151 connection)
- TFTP timeout (check dnsmasq service)
- Kernel panic (check cmdline.txt - should NOT have root=/dev/ram0)
- Init script doesn't run (check /init exists in initrd.img)
- Network fails (check dhclient in init script)
- Can't reach server (check eth1 on server: 192.168.151.1)
- API connection fails (check rpi-deployment service)

## Troubleshooting Commands

```bash
# Check system readiness
sudo /opt/rpi-deployment/scripts/validate_boot_ready.sh

# View TFTP boot files
ls -lh /tftpboot/

# Check cmdline.txt
cat /tftpboot/cmdline.txt
# Should show: console=serial0,115200 console=tty1 rw initrd=initrd.img ip=dhcp

# Test TFTP manually (from another machine on VLAN 151)
tftp 192.168.151.1
get config.txt
get kernel8.img

# Check dnsmasq status
sudo systemctl status dnsmasq
sudo journalctl -u dnsmasq -f

# Check deployment server
sudo systemctl status rpi-deployment
curl http://192.168.151.1:5001/health

# View network configuration
ip addr show eth1
sudo netstat -uln | grep -E ':(67|69)'
```

## Log Files

All logs are saved to:
- Boot monitor: `/opt/rpi-deployment/logs/pi_boot_YYYYMMDD_HHMMSS.log`
- Deployment: `/opt/rpi-deployment/logs/deployment_YYYYMMDD.log`
- dnsmasq: `/var/log/dnsmasq.log`
- systemd services: `journalctl -u rpi-deployment -u rpi-web`

## Next Steps After Successful Boot

1. **Check deployment history**:
   ```bash
   sqlite3 /opt/rpi-deployment/database/deployment.db \
     "SELECT * FROM deployment_history ORDER BY started_at DESC LIMIT 5;"
   ```

2. **Verify hostname assignment**:
   ```bash
   sqlite3 /opt/rpi-deployment/database/deployment.db \
     "SELECT * FROM hostname_pool WHERE status='assigned';"
   ```

3. **Check image writing progress** (if installer running):
   - Watch deployment logs for progress messages (every 100MB)
   - Monitor SD card write activity on Pi

4. **Wait for reboot**:
   - Pi will automatically reboot after successful deployment
   - Should boot into production OS from SD card

## Known Issues

- **SD Card Not Formatted**: This is EXPECTED. The installer will format and write to the SD card.
- **First Boot Slow**: Initial TFTP download of 95MB initrd.img takes 30-60 seconds depending on network.
- **Image Download**: Master image download can take 5-10 minutes for 4-8GB images.

---

**Last Updated**: 2025-10-24
**System Status**: ✅ READY (22/22 validation checks passed)
**cmdline.txt**: ✅ FIXED (removed root=/dev/ram0 and init=/usr/bin/python3)
