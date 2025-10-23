## Phase 3: DHCP and TFTP Configuration

### Step 3.1: Configure dnsmasq for DHCP/TFTP

Create dnsmasq configuration for the deployment network:

```bash
# Backup original config
sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup

# Create new config
sudo nano /etc/dnsmasq.conf
```

```conf
# Interface to listen on - DEPLOYMENT NETWORK ONLY
interface=eth1
bind-interfaces

# Never forward queries for deployment network
no-dhcp-interface=eth0
except-interface=eth0

# DHCP range for deployment network
dhcp-range=192.168.151.100,192.168.151.250,12h

# No gateway for isolated deployment network
# dhcp-option=3,192.168.151.1  # Commented out - no external routing

# DNS servers (for temporary use during imaging)
dhcp-option=6,8.8.8.8,8.8.4.4

# Enable TFTP
enable-tftp
tftp-root=/tftpboot

# Boot file for Raspberry Pi 5 (UEFI)
dhcp-match=set:efi-x86_64,option:client-arch,7
dhcp-match=set:efi-x86_64,option:client-arch,9
dhcp-match=set:efi-arm64,option:client-arch,11
dhcp-boot=tag:efi-arm64,bootfiles/boot.ipxe

# TFTP server IP (deployment network)
dhcp-option=66,192.168.151.1

# Logging
log-dhcp
log-queries
log-facility=/var/log/dnsmasq.log
```

Enable and start dnsmasq:
```bash
sudo systemctl enable dnsmasq
sudo systemctl restart dnsmasq
sudo systemctl status dnsmasq
```

### Step 3.2: Configure TFTP Server

```bash
# Edit TFTP configuration
sudo nano /etc/default/tftpd-hpa
```

```conf
TFTP_USERNAME="tftp"
TFTP_DIRECTORY="/tftpboot"
TFTP_ADDRESS="192.168.151.1:69"
TFTP_OPTIONS="--secure --create"
```

```bash
# Restart TFTP service
sudo systemctl restart tftpd-hpa
sudo systemctl enable tftpd-hpa
```

---

