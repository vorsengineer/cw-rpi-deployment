# Alpine Netboot Quick Reference

**Quick commands for using Alpine Linux netboot with RPi deployment**

---

## Setup (One-Time)

```bash
# Run automated setup script
sudo /opt/rpi-deployment/scripts/setup_alpine_netboot.sh

# Or with options
sudo /opt/rpi-deployment/scripts/setup_alpine_netboot.sh \
  --ssh-key ~/.ssh/id_ed25519.pub \
  --auto-install
```

---

## Enable Alpine Boot

### Option 1: Always Boot Alpine (Testing)

```bash
# Edit dnsmasq config
sudo nano /etc/dnsmasq.conf

# Change line:
dhcp-boot=tag:efi-arm64,config-alpine.txt

# Restart dnsmasq
sudo systemctl restart dnsmasq
```

### Option 2: Boot Specific Pi (Production)

```bash
# Add to /etc/dnsmasq.conf:
dhcp-host=aa:bb:cc:dd:ee:ff,192.168.151.200,set:alpine
dhcp-boot=tag:alpine,config-alpine.txt
dhcp-boot=tag:efi-arm64,config.txt  # Others use standard boot

sudo systemctl restart dnsmasq
```

---

## Using Alpine

### Connect to Pi

```bash
# Find Pi IP (check dnsmasq logs)
sudo grep DHCPACK /var/log/syslog | tail -5

# SSH to Pi
ssh root@192.168.151.100
```

### Run Installer

```bash
# On Alpine Pi - Manual execution
/installer/run_deployment.sh

# Or download and run directly
wget http://192.168.151.1/installer/pi_installer.py
python3 pi_installer.py
```

### Monitor Installation

```bash
# Watch logs
tail -f /var/log/deployment.log

# In another terminal - monitor from server
ssh root@192.168.151.100 'tail -f /var/log/deployment.log'
```

### Debug

```bash
# Network tests
ping 192.168.151.1
curl http://192.168.151.1/health
ip addr
ip route

# Check SD card
lsblk
fdisk -l /dev/mmcblk0

# System info
free -h
df -h
ps aux
```

---

## Switch Back to Standard Boot

```bash
# Edit /etc/dnsmasq.conf
dhcp-boot=tag:efi-arm64,config.txt

sudo systemctl restart dnsmasq
```

---

## Monitoring (Server Side)

```bash
# Watch DHCP/TFTP
sudo tcpdump -i eth1 port 67 or port 68 or port 69

# Watch TFTP transfers
sudo tail -f /var/log/syslog | grep TFTP

# Watch dnsmasq
sudo tail -f /var/log/syslog | grep dnsmasq
```

---

## Troubleshooting

### Pi won't boot Alpine

```bash
# Check files exist
ls -lh /tftpboot/alpine/boot/

# Verify dnsmasq config
grep dhcp-boot /etc/dnsmasq.conf
sudo dnsmasq --test
```

### Can't SSH to Pi

```bash
# Wait 30 seconds after boot for SSH to start
# Find actual IP address
sudo grep "DHCPACK.*192.168.151" /var/log/syslog | tail -1

# Test connectivity
ping 192.168.151.100
```

### Installer fails

```bash
# SSH to Pi and run manually
ssh root@192.168.151.100

# Install dependencies
apk add --no-cache python3 py3-pip

# Run installer
python3 /installer/pi_installer.py
```

---

## Files

| File | Purpose |
|------|---------|
| `/tftpboot/config-alpine.txt` | Alpine boot config |
| `/tftpboot/alpine/boot/vmlinuz-rpi` | Kernel |
| `/tftpboot/alpine/boot/initramfs-rpi` | Init RAM filesystem |
| `/tftpboot/alpine/deployment.apkovl.tar.gz` | SSH overlay |

---

**Full Documentation**: `/opt/rpi-deployment/docs/ALPINE_NETBOOT_SSH_SETUP.md`
