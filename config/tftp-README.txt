# Phase 4 Boot Files - README

## Current Status: Boot Files Ready (Testing Phase)

This directory contains Raspberry Pi 5 network boot files.

### Boot Sequence (Designed)
1. Pi 5 EEPROM bootloader requests DHCP
2. dnsmasq responds with IP + Option 43 ("Raspberry Pi Boot")
3. Pi requests via TFTP (192.168.151.1):
   - config.txt (boot configuration)
   - kernel8.img (ARM64 Linux kernel, 9.5MB)
   - bcm2712-rpi-5-b.dtb (device tree)
   - cmdline.txt (kernel command line)
   - initrd.img (TO BE CREATED IN PHASE 5+)
4. Kernel boots with initrd containing pi_installer.py
5. Installer downloads master image via HTTP (Phase 5+)

### Files Present
- config.txt (312 bytes) - Pi 5 boot config
- kernel8.img (9.5MB) - ARM64 kernel
- bcm2712-rpi-5-b.dtb (77KB) - Device tree
- cmdline.txt - Kernel parameters (points to HTTP installer)

### Files Needed (Phase 5+)
- initrd.img - Initial RAM disk with Python installer
- /opt/installer/pi_installer.py - Custom deployment script

### Placeholders in cmdline.txt
- initrd=initrd.img (will be created)
- server=http://192.168.151.1:5001 (deployment API)
- installer=/opt/installer/pi_installer.py (will be embedded in initrd)

### Testing Commands
# Test TFTP serving
tftp 192.168.151.1
get config.txt
get kernel8.img
quit

# Monitor DHCP/TFTP requests
sudo tail -f /var/log/dnsmasq.log
sudo tcpdump -i eth1 port 67 or port 69

Created: 2025-10-23
Phase: 4 - Boot Files Preparation
Status: Ready for TFTP testing
