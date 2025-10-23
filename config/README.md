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

### nginx Configuration Files

See `nginx/` subdirectory for complete nginx configuration backup.

**Deployment Location**: `/etc/nginx/`
**Purpose**: HTTP server for dual-network architecture
**Modified In**: Phase 5
**Key Features**:
- Management interface: 192.168.101.146:80 (reverse proxy to Flask apps)
- Deployment interface: 192.168.151.1:80 (static file serving for master images)
- Network isolation enforced (specific IP binding only)
- Large file support (8GB) with sendfile optimization
- WebSocket support for real-time dashboard updates

**Files Backed Up**:
- `nginx.conf` (1.5KB) - Main nginx configuration
- `sites-available/rpi-deployment` (7.8KB) - Dual-network site configuration
- `sites-available/default` (2.4KB) - Default site (disabled)
- `snippets/fastcgi-php.conf` (423B) - FastCGI PHP parameters
- `snippets/snakeoil.conf` (217B) - Self-signed SSL example

**To Deploy**:
```bash
# Deploy main configuration
sudo cp config/nginx/nginx.conf /etc/nginx/nginx.conf

# Deploy site configuration
sudo cp config/nginx/sites-available/rpi-deployment /etc/nginx/sites-available/rpi-deployment

# Enable site
sudo ln -sf /etc/nginx/sites-available/rpi-deployment /etc/nginx/sites-enabled/rpi-deployment

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
sudo systemctl status nginx
```

**See Also**: `nginx/BACKUP_INFO.txt` for detailed restore instructions

### Systemd Service Files

**Deployment Location**: `/etc/systemd/system/`
**Purpose**: Automated service management for deployment applications
**Modified In**: Phase 9
**Key Features**:
- Auto-start on boot
- Auto-restart on failure (10-second delay)
- Proper service dependencies
- Runs as non-root user (captureworks)
- Security hardening (NoNewPrivileges, PrivateTmp)

**Files Backed Up**:
- `rpi-deployment.service` (890B) - Deployment server API service (port 5001)
- `rpi-web.service` (928B) - Web management interface service (port 5000)

**To Deploy**:
```bash
# Deploy both service files
sudo cp config/rpi-deployment.service /etc/systemd/system/
sudo cp config/rpi-web.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services for auto-start on boot
sudo systemctl enable rpi-deployment rpi-web

# Start services
sudo systemctl start rpi-deployment rpi-web

# Verify services are running
sudo systemctl status rpi-deployment rpi-web

# Test endpoints
curl http://192.168.151.1:5001/health      # Deployment API
curl http://192.168.101.146:5000/          # Web interface
```

**Service Dependencies**:
- `rpi-deployment.service` - Starts first, provides deployment API
- `rpi-web.service` - Depends on rpi-deployment, provides web UI

**⚠️ Important**: Both services require PYTHONPATH environment variable to access Flask packages installed in user's home directory.

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

   # Deploy nginx configuration
   sudo cp config/nginx/nginx.conf /etc/nginx/nginx.conf
   sudo cp config/nginx/sites-available/rpi-deployment /etc/nginx/sites-available/rpi-deployment
   sudo ln -sf /etc/nginx/sites-available/rpi-deployment /etc/nginx/sites-enabled/rpi-deployment

   # Deploy systemd service files
   sudo cp config/rpi-deployment.service /etc/systemd/system/
   sudo cp config/rpi-web.service /etc/systemd/system/
   sudo systemctl daemon-reload

   # Apply network tuning
   sudo sysctl -p /etc/sysctl.d/99-rpi-deployment-network.conf

   # Restart services
   sudo systemctl restart dnsmasq nginx

   # Enable and start deployment services
   sudo systemctl enable rpi-deployment rpi-web
   sudo systemctl start rpi-deployment rpi-web
   ```

4. **Download Boot Files** (Phase 4):
   ```bash
   cd /tftpboot
   sudo wget https://github.com/raspberrypi/firmware/raw/master/boot/kernel8.img
   sudo wget https://github.com/raspberrypi/firmware/raw/master/boot/bcm2712-rpi-5-b.dtb
   sudo chmod 644 kernel8.img bcm2712-rpi-5-b.dtb
   sudo chown root:nogroup kernel8.img bcm2712-rpi-5-b.dtb
   ```

5. **Validate**:
   ```bash
   # Phase 3: DHCP/TFTP
   /opt/rpi-deployment/scripts/validate_phase3.sh

   # Phase 5: nginx HTTP serving
   curl http://192.168.101.146/nginx-health  # Management interface
   curl http://192.168.151.1/nginx-health    # Deployment interface
   sudo nginx -t                              # Configuration syntax
   sudo systemctl status nginx dnsmasq       # Service status

   # Phase 9: Deployment services
   sudo systemctl status rpi-deployment rpi-web  # Service status
   curl http://192.168.151.1:5001/health     # Deployment API health
   curl http://192.168.101.146:5000/         # Web interface
   ```

## Configuration Change Log

| File | Date | Phase | Changes |
|------|------|-------|---------|
| dnsmasq.conf | 2025-10-23 | Phase 3 | Initial DHCP/TFTP configuration |
| dnsmasq.conf | 2025-10-23 | Phase 4 | Added Option 43, changed boot file, disabled tftp-secure |
| 99-rpi-deployment-network.conf | 2025-10-23 | Phase 3 | Network performance tuning |
| tftp-config.txt | 2025-10-23 | Phase 4 | Raspberry Pi 5 boot configuration |
| tftp-cmdline.txt | 2025-10-23 | Phase 4 | Kernel command line with HTTP installer placeholders |
| nginx/sites-available/rpi-deployment | 2025-10-23 | Phase 5 | Dual-network HTTP server configuration |
| nginx/nginx.conf | 2025-10-23 | Phase 5 | Main nginx configuration (no changes from default) |
| rpi-deployment.service | 2025-10-23 | Phase 9 | Systemd service for deployment API (port 5001) |
| rpi-web.service | 2025-10-23 | Phase 9 | Systemd service for web interface (port 5000) |

## Important Notes

- **Always backup** current configs before deploying these: `sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup`
- **Test syntax** before restarting services: `sudo dnsmasq --test`
- **Check logs** after deployment: `sudo tail -f /var/log/dnsmasq.log`
- **UniFi DHCP**: Must be disabled on VLAN 151 to avoid conflicts
- **Network Isolation**: Deployment network (VLAN 151) has no routing to internet for security

---

**Last Updated**: 2025-10-23
**Phases Covered**: Phase 3 (DHCP/TFTP), Phase 4 (Boot Files), Phase 5 (HTTP Server), Phase 9 (Service Management)
**Next Phase**: Phase 10 (Testing and Validation)
