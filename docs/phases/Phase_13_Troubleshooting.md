## Phase 13: Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: Pi not receiving IP from DHCP
```bash
# Check dnsmasq logs
tail -f /var/log/dnsmasq.log

# Verify dnsmasq is listening
sudo netstat -tulpn | grep dnsmasq

# Test DHCP manually
sudo nmap --script broadcast-dhcp-discover -e eth0
```

#### Issue 2: TFTP boot files not loading
```bash
# Check TFTP logs
tail -f /var/log/syslog | grep tftp

# Test TFTP manually
tftp 192.168.101.10
> get bootfiles/boot.ipxe
> quit

# Verify file permissions
ls -la /tftpboot/bootfiles/
```

#### Issue 3: Image download fails
```bash
# Check nginx logs
tail -f /var/log/nginx/deployment-error.log

# Test download manually
wget http://192.168.101.10/images/kxp_dualcam_master.img -O /tmp/test.img

# Check disk space
df -h /opt/rpi-deployment/images/
```

#### Issue 4: Installation verification fails
```bash
# Check image integrity
sha256sum /opt/rpi-deployment/images/kxp_dualcam_master.img

# Verify SD card is good
# On the Pi (if accessible):
sudo badblocks -v /dev/mmcblk0
```

---

