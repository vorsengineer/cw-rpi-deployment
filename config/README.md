# Configuration Files Backup

This directory contains backup copies of all system configuration files modified during the deployment server setup. These files are version controlled for disaster recovery and documentation purposes.

## System Configuration Files

### dnsmasq.conf
**Deployment Location**: `/etc/dnsmasq.conf`
**Purpose**: Main DHCP and TFTP server configuration
**Modified In**: Phase 3, Phase 4
**Key Features**:
- DHCP server for deployment network (192.168.151.100-250)
- Built-in TFTP server serving from /tftpboot
- DHCP Option 43 for Raspberry Pi 5 bootloader recognition
- Network isolation (eth1 only, no eth0)
- Logging to /var/log/dnsmasq.log

**Critical Settings**:
- `interface=eth1` - Only serve on deployment network
- `dhcp-option=43,"Raspberry Pi Boot"` - Required for Pi 5
- `dhcp-boot=tag:efi-arm64,config.txt` - Boot file for Pi 5
- `tftp-no-blocksize` - Compatibility for Pi firmware
- `#tftp-secure` - Disabled for isolated network

**To Deploy**:
```bash
sudo cp dnsmasq.conf /etc/dnsmasq.conf
sudo systemctl restart dnsmasq
sudo systemctl status dnsmasq
```

### 99-rpi-deployment-network.conf
**Deployment Location**: `/etc/sysctl.d/99-rpi-deployment-network.conf`
**Purpose**: Network performance tuning for concurrent Pi deployments
**Modified In**: Phase 3
**Key Features**:
- Increased socket buffer sizes to 8MB (from 208KB default)
- Network backlog queue increased to 5000
- Optimized for 10-20 concurrent TFTP connections

**To Deploy**:
```bash
sudo cp 99-rpi-deployment-network.conf /etc/sysctl.d/
sudo sysctl -p /etc/sysctl.d/99-rpi-deployment-network.conf
```

## TFTP Boot Files

### tftp-config.txt
**Deployment Location**: `/tftpboot/config.txt`
**Purpose**: Raspberry Pi 5 boot configuration
**Modified In**: Phase 4
**Key Features**:
- Specifies kernel8.img as boot kernel
- Enables ARM 64-bit mode
- Enables UART for debugging

**To Deploy**:
```bash
sudo cp tftp-config.txt /tftpboot/config.txt
sudo chmod 644 /tftpboot/config.txt
sudo chown root:nogroup /tftpboot/config.txt
```

### tftp-cmdline.txt
**Deployment Location**: `/tftpboot/cmdline.txt`
**Purpose**: Kernel command line parameters
**Modified In**: Phase 4
**Key Features**:
- Boot from RAM disk (initrd)
- DHCP network configuration
- HTTP installer server URL (192.168.151.1:5001)
- Custom Python installer script path

**⚠️ Note**: Contains placeholders for Phase 5+ components:
- `initrd=initrd.img` - To be created in Phase 5+
- `server=http://192.168.151.1:5001` - Deployment API (Phase 5+)
- `installer=/opt/installer/pi_installer.py` - Python installer (Phase 6+)

**To Deploy**:
```bash
sudo cp tftp-cmdline.txt /tftpboot/cmdline.txt
sudo chmod 644 /tftpboot/cmdline.txt
sudo chown root:nogroup /tftpboot/cmdline.txt
```

### tftp-README.txt
**Deployment Location**: `/tftpboot/README_PHASE4.txt`
**Purpose**: Documentation of boot files and sequence
**Modified In**: Phase 4

## Disaster Recovery Procedure

If the deployment server needs to be rebuilt from scratch:

1. **Provision VM** (Phase 1):
   - Use scripts from vm_provisioning/
   - Create VM with dual network interfaces

2. **Install Base Packages** (Phase 2):
   - Follow Phase 2 documentation
   - Install dnsmasq, nginx, tftpd-hpa, Python packages

3. **Restore Configurations**:
   ```bash
   # Clone repository
   git clone https://github.com/vorsengineer/cw-rpi-deployment.git
   cd cw-rpi-deployment

   # Deploy system configs
   sudo cp config/dnsmasq.conf /etc/dnsmasq.conf
   sudo cp config/99-rpi-deployment-network.conf /etc/sysctl.d/

   # Deploy TFTP boot files
   sudo cp config/tftp-config.txt /tftpboot/config.txt
   sudo cp config/tftp-cmdline.txt /tftpboot/cmdline.txt
   sudo cp config/tftp-README.txt /tftpboot/README_PHASE4.txt

   # Set permissions
   sudo chmod 644 /tftpboot/*.txt
   sudo chown root:nogroup /tftpboot/*.txt

   # Apply network tuning
   sudo sysctl -p /etc/sysctl.d/99-rpi-deployment-network.conf

   # Restart services
   sudo systemctl restart dnsmasq
   ```

4. **Download Boot Files** (Phase 4):
   ```bash
   cd /tftpboot
   sudo wget https://github.com/raspberrypi/firmware/raw/master/boot/kernel8.img
   sudo wget https://github.com/raspberrypi/firmware/raw/master/boot/bcm2712-rpi-5-b.dtb
   sudo chmod 644 kernel8.img bcm2712-rpi-5-b.dtb
   sudo chown root:nogroup kernel8.img bcm2712-rpi-5-b.dtb
   ```

5. **Validate** (Phase 3):
   ```bash
   /opt/rpi-deployment/scripts/validate_phase3.sh
   ```

## Configuration Change Log

| File | Date | Phase | Changes |
|------|------|-------|---------|
| dnsmasq.conf | 2025-10-23 | Phase 3 | Initial DHCP/TFTP configuration |
| dnsmasq.conf | 2025-10-23 | Phase 4 | Added Option 43, changed boot file, disabled tftp-secure |
| 99-rpi-deployment-network.conf | 2025-10-23 | Phase 3 | Network performance tuning |
| tftp-config.txt | 2025-10-23 | Phase 4 | Raspberry Pi 5 boot configuration |
| tftp-cmdline.txt | 2025-10-23 | Phase 4 | Kernel command line with HTTP installer placeholders |

## Important Notes

- **Always backup** current configs before deploying these: `sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup`
- **Test syntax** before restarting services: `sudo dnsmasq --test`
- **Check logs** after deployment: `sudo tail -f /var/log/dnsmasq.log`
- **UniFi DHCP**: Must be disabled on VLAN 151 to avoid conflicts
- **Network Isolation**: Deployment network (VLAN 151) has no routing to internet for security

---

**Last Updated**: 2025-10-23
**Phases Covered**: Phase 3 (DHCP/TFTP), Phase 4 (Boot Files)
**Next Phase**: Phase 5 (HTTP Server Configuration)
