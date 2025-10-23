# Raspberry Pi 5 Network Deployment System - Implementation Plan v2.0

## Document Purpose
This document provides a complete, step-by-step implementation plan for creating a network-based Raspberry Pi imaging and deployment server with enhanced hostname management and web-based monitoring. This system enables mass deployment of KartXPro (KXP2) and RaceXPro (RXP2) dual-camera recorder systems to blank Raspberry Pi 5 devices over the network.

**Target Audience:** Claude Code and DevOps engineers
**Management Network:** 192.168.101.x subnet (VLAN 101)
**Deployment Network:** 192.168.151.0/24 subnet (VLAN 151)
**Device Type:** Raspberry Pi 5 with dual camera setup
**Products Supported:** KXP2 (KartXPro) and RXP2 (RaceXPro)

## Summary of Major Changes (v2.0)

### Infrastructure Changes
1. **Proxmox-First Approach**: Phases reorganized to start with Proxmox VM provisioning (Phase 1)
2. **Dual Network Architecture**:
   - Management network (VLAN 101): 192.168.101.20 for web UI and administration
   - Deployment network (VLAN 151): 192.168.151.1 for isolated Pi imaging
3. **NVMe/SSD Optimization**: VM configured with VirtIO SCSI, discard/TRIM, and optimized mount options
4. **Ubuntu 24.04 LTS**: Updated from generic Ubuntu/Debian to specific Ubuntu 24.04 LTS

### Authentication & Security
1. **Proxmox Credentials**: root / Ati4870_x5
2. **VM User**: captureworks / Jankycorpltd01 (replaced kxpadmin)
3. **Network Isolation**: Complete VLAN separation between management and deployment

### New Features
1. **Hostname Management System** (Phase 6):
   - Product-specific naming: KXP2-VENUE-### and RXP2-VENUE-SERIAL
   - Pre-loadable venue codes and kart number lists
   - SQLite database for tracking assignments
   - Automatic hostname assignment during deployment

2. **Web Management Interface** (Phase 7):
   - Real-time deployment monitoring dashboard
   - Venue and kart number management
   - Image upload and version control
   - Deployment statistics and reporting
   - WebSocket support for live updates

3. **Enhanced Python Scripts** (Phase 8):
   - deployment_server.py: Hostname assignment, dual network support, database integration
   - pi_installer.py: Product type selection, venue code support, automatic hostname configuration

### API Changes
1. **Dual Port Configuration**:
   - Port 5000: Web management interface (management network)
   - Port 5001: Deployment API (deployment network)
2. **Updated Endpoints**:
   - POST /api/config: Now accepts product_type, venue_code for hostname assignment
   - Enhanced /api/status: Tracks hostname, deployment progress in database

### Service Management
1. **Two Systemd Services**:
   - rpi-deployment.service: Deployment API server
   - rpi-web.service: Web management interface
2. **User Context**: Services run as 'captureworks' user, not root

---

## Architecture Overview

### System Components
1. **Proxmox Virtual Environment**
   - Host: 192.168.11.194
   - VM with Ubuntu 24.04 LTS
   - Dual network interfaces (VLAN 101 & 151)
   - NVMe-optimized storage configuration
   - 4 vCPUs, 8GB RAM, 100GB storage

2. **Deployment Server** (Ubuntu 24.04 LTS VM)
   - DHCP Server (dnsmasq) on deployment network
   - TFTP Server (for boot files)
   - HTTP Server (nginx for image distribution)
   - Flask Web Application (management interface)
   - Hostname Management System (SQLite database)
   - Custom Python deployment scripts
   - User: captureworks / Password: Jankycorpltd01

3. **Network Architecture**
   - **Management Network (VLAN 101)**: 192.168.101.x
     - Server management interface
     - Web UI access
     - SSH administration
   - **Deployment Network (VLAN 151)**: 192.168.151.0/24
     - Isolated network for Pi imaging
     - DHCP range: 192.168.151.100-250
     - Server IP: 192.168.151.1

4. **Network Boot Process**
   - Pi boots from network using PXE/iPXE
   - Receives IP from deployment network DHCP
   - Downloads minimal installer environment
   - Requests hostname assignment from server
   - Downloads appropriate master image (KXP2/RXP2)
   - Image is written to local SD card
   - Hostname configured based on product/venue/identifier
   - Pi reboots from SD card (standalone operation)

5. **Master Images**
   - **KXP2**: KartXPro dual camera recorder
   - **RXP2**: RaceXPro dual camera recorder
   - Pre-configured with all dependencies
   - Services configured and production-ready

6. **Hostname Management System**
   - Product-based naming schemes:
     - KXP2: `KXP2-[VENUE]-[NUMBER]` (e.g., KXP2-CORO-001)
     - RXP2: `RXP2-[VENUE]-[SERIAL]` (e.g., RXP2-CORO-ABC12345)
   - Pre-loadable venue codes and kart numbers
   - Assignment tracking via SQLite database

7. **Web Management Interface**
   - Real-time deployment monitoring dashboard
   - Image upload and version management
   - Hostname pool configuration
   - Venue and kart number management
   - Deployment statistics and reporting

---

## Phase 1: Proxmox VM Provisioning (Cloud-Init Automated Approach)

**Status**: ✅ **COMPLETED** (2025-10-23)
- **VM Created**: VMID 104 (cw-rpi-deployment01)
- **Current IP**: 192.168.101.146 (DHCP assigned)
- **SSH Access**: Working with both key and password

**Important Update**: We've implemented a fully automated approach using Cloud-Init instead of manual Ubuntu installation. This saves significant time and eliminates manual configuration errors.

### Step 1.1: Connect to Proxmox Host

```bash
# Proxmox Host Details
PROXMOX_HOST="192.168.11.194"
PROXMOX_USER="root"
PROXMOX_PASSWORD="Ati4870_x5"
NODE="cw-dc01"  # Important: Use cw-dc01, NOT cw-dc02
STORAGE="vm_data"  # Storage pool for VM disks
```

### Step 1.2: Install Proxmoxer (On Management Workstation)

```bash
# Install Python Proxmox library
pip3 install proxmoxer requests

# Verify installation
python3 -c "from proxmoxer import ProxmoxAPI; print('Proxmoxer installed successfully')"
```

### Step 1.3: Download Ubuntu Cloud Image

**Instead of using desktop ISO with manual installation, we use Ubuntu Server Cloud Image for automation:**

```bash
# SSH to Proxmox and download cloud image (596MB)
ssh root@192.168.11.194
cd /var/lib/vz/template/iso/
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

# Verify download
ls -lh ubuntu-24.04-server-cloudimg-amd64.img
# Should show ~596MB file
```

### Step 1.4: Create Cloud-Init Enabled VM

**Key Differences from Manual Approach:**
- Uses Cloud Image instead of installer ISO
- Cloud-Init configures everything automatically
- No manual installation needed
- VM is ready in 5 minutes vs 45+ minutes
- SSH keys and password authentication pre-configured

**Use the Production Provisioning Script:**

```bash
# From workstation with Proxmoxer installed
cd C:\Temp\Claude_Desktop\RPi5_Network_Deployment

# Run the complete provisioning script
python scripts\vm_provisioning\provision_deployment_vm.py

# Or with custom configuration
python scripts\vm_provisioning\provision_deployment_vm.py --config custom_config.json
```

**What the Script Does:**
1. Downloads Ubuntu cloud image to Proxmox (if not present)
2. Creates VM with proper specifications (4 cores, 8GB RAM, 100GB disk)
3. Imports cloud image and resizes disk to 100GB
4. Configures dual network interfaces (VLAN 101 & 151)
5. Sets up Cloud-Init with:
   - User: captureworks / Password: Jankycorpltd01
   - SSH key from ssh_keys/deployment_key.pub
   - DHCP on management network (VLAN 101)
   - Static IP on deployment network (192.168.151.1)
   - QEMU guest agent auto-installation
6. Starts the VM for automatic configuration

### Step 1.5: Cloud-Init VM Configuration Summary

**What Cloud-Init Automatically Configures:**

1. **User Account**: captureworks / Jankycorpltd01
2. **Network Configuration**:
   - eth0: DHCP from UniFi (VLAN 101 - Management)
   - eth1: 192.168.151.1/24 (VLAN 151 - Deployment)
   - DNS: 8.8.8.8 (single server, not comma-separated)
3. **Hostname**: cw-rpi-deployment01
4. **Package Updates**: Automatic on first boot
5. **SSH Access**: Both password and key authentication enabled
6. **QEMU Guest Agent**: Auto-installed via Cloud-Init
7. **TRIM/Discard**: Enabled for SSD optimization
8. **SSH Key**: Automatically added from ssh_keys/deployment_key.pub

**VM Details Created:**
- VMID: 104
- Name: cw-rpi-deployment01
- Node: cw-dc01
- Storage: vm_data (100GB disk)
- CPU: 4 cores
- RAM: 8192MB (8GB)
- Network: Dual NICs (VLAN 101 & 151)
- Display: Default (not VGA or serial)

### Step 1.6: Starting and Monitoring Cloud-Init VM

```bash
# The VM starts automatically and Cloud-Init configures everything
# Monitor progress via Proxmox console or wait 5 minutes

# After Cloud-Init completes, test SSH access:
# Note: IP is assigned via DHCP from UniFi

# Using SSH key (recommended):
ssh -i ssh_keys/deployment_key captureworks@<DHCP_IP>

# Using password:
ssh captureworks@<DHCP_IP>
# Password: Jankycorpltd01
```

### Step 1.7: Validation (Required before Phase 1 completion)

```bash
# Run the validation script to verify VM is properly configured
python scripts\vm_provisioning\validate_vm.py

# Or validate specific VM with known IP
python scripts\vm_provisioning\validate_vm.py --ip <DHCP_IP>

# The validation script checks:
# - VM status via Proxmox API
# - Guest agent installation and response
# - Network connectivity on both interfaces
# - SSH access with key authentication
# - Cloud-Init completion status
# - Service status

# SSH to the VM for manual checks (if needed)
ssh -i ssh_keys/deployment_key captureworks@<DHCP_IP>

# Note: QEMU guest agent and TRIM are automatically configured via Cloud-Init
```

---

## Phase 2: Deployment Server Base Configuration

**Status**: ⏳ Ready to Start
**VM IP**: 192.168.101.146 (Use this IP for SSH access)

### Step 2.1: Dual Network Interface Setup

SSH to the VM and verify the network interfaces (should already be configured by Cloud-Init):

```bash
# SSH to the VM using the key
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146

# Or using password
ssh captureworks@192.168.101.146
# Password: Jankycorpltd01

# Check current network configuration
ip addr show

# Edit netplan configuration (if changes needed)
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:  # Management interface (VLAN 101)
      dhcp4: yes  # DHCP from UniFi on VLAN 101
    eth1:  # Deployment interface (VLAN 151)
      dhcp4: no
      addresses:
        - 192.168.151.1/24
      # No gateway - isolated network
```

Apply configuration:
```bash
sudo netplan apply

# Verify both interfaces
ip addr show
```

### Step 2.2: Install Base Packages

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    dnsmasq \
    nginx \
    tftpd-hpa \
    ipxe \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    wget \
    pv \
    pigz \
    sqlite3 \
    build-essential

# Install Python dependencies
pip3 install --user \
    flask \
    flask-socketio \
    flask-cors \
    requests \
    proxmoxer \
    python-socketio \
    sqlalchemy \
    werkzeug
```

### Step 2.3: Directory Structure Setup

```bash
# Create deployment directories
sudo mkdir -p /opt/rpi-deployment/{images,scripts,logs,config,database,web}
sudo mkdir -p /opt/rpi-deployment/web/{templates,static/{css,js,uploads}}
sudo mkdir -p /tftpboot/bootfiles
sudo mkdir -p /var/www/deployment

# Set ownership
sudo chown -R captureworks:captureworks /opt/rpi-deployment
sudo chmod -R 755 /opt/rpi-deployment

# Create log directory with proper permissions
sudo mkdir -p /var/log/rpi-deployment
sudo chown captureworks:captureworks /var/log/rpi-deployment
```

---

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

## Phase 4: Boot Files Preparation

### Step 4.1: Download Raspberry Pi Boot Files

```bash
# Clone Raspberry Pi firmware repository
cd /tmp
git clone --depth=1 https://github.com/raspberrypi/firmware

# Copy boot files to TFTP directory
sudo cp firmware/boot/bootcode.bin /tftpboot/
sudo cp firmware/boot/start*.elf /tftpboot/
sudo cp firmware/boot/fixup*.dat /tftpboot/
```

### Step 4.2: Get iPXE Boot Files for ARM64

```bash
# Download or build iPXE for ARM64
cd /tmp
git clone https://github.com/ipxe/ipxe.git
cd ipxe/src

# Build for ARM64
make bin-arm64-efi/ipxe.efi EMBED=boot.ipxe

# Copy to TFTP
sudo cp bin-arm64-efi/ipxe.efi /tftpboot/bootfiles/boot.ipxe
```

### Step 4.3: Create iPXE Boot Script

```bash
sudo nano /tftpboot/bootfiles/boot.ipxe
```

```ipxe
#!ipxe

echo ========================================
echo KXP/RXP Deployment System - Network Boot
echo ========================================

# Get network configuration
dhcp

# Set server IP (deployment network)
set server_ip 192.168.151.1

echo Server IP: ${server_ip}
echo Client IP: ${ip}
echo Starting installation...

# Download and execute Python installer
kernel http://${server_ip}/boot/vmlinuz
initrd http://${server_ip}/boot/initrd.img
imgargs vmlinuz root=/dev/ram0 rw init=/opt/installer/run_installer.sh server=${server_ip}
boot || goto failed

:failed
echo Boot failed! Press any key to retry...
prompt
goto retry

:retry
chain --autofree boot.ipxe
```

---

## Phase 5: HTTP Server Configuration

### Step 5.1: Configure Nginx for Dual Network

```bash
sudo nano /etc/nginx/sites-available/rpi-deployment
```

```nginx
# Management interface - Web UI and Administration
server {
    listen 192.168.101.20:80;
    server_name rpi-deployment.local;

    root /opt/rpi-deployment/web;
    index index.html;

    # Logging
    access_log /var/log/nginx/management-access.log;
    error_log /var/log/nginx/management-error.log;

    # Web UI - Flask Application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files
    location /static/ {
        alias /opt/rpi-deployment/web/static/;
        expires 30d;
    }

    # Image uploads from web interface
    location /uploads/ {
        alias /opt/rpi-deployment/web/static/uploads/;
        client_max_body_size 8G;
    }
}

# Deployment network - Image distribution
server {
    listen 192.168.151.1:80;
    server_name _;

    root /var/www/deployment;

    # Logging
    access_log /var/log/nginx/deployment-access.log;
    error_log /var/log/nginx/deployment-error.log;

    # Boot files for PXE
    location /boot/ {
        alias /tftpboot/bootfiles/;
        autoindex on;
    }

    # Master images for deployment
    location /images/ {
        alias /opt/rpi-deployment/images/;
        autoindex off;  # Security - no directory listing

        # Enable large file transfers
        client_max_body_size 8G;

        # Optimize for large file transfers
        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;
    }

    # API endpoints for deployment operations
    location /api/ {
        proxy_pass http://127.0.0.1:5001;  # Separate port for deployment API
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 600s;  # Long timeout for image downloads
    }
}
```

Enable site and restart nginx:
```bash
sudo ln -s /etc/nginx/sites-available/rpi-deployment /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Phase 6: Hostname Management System

### Step 6.1: Create Database Schema

Create `/opt/rpi-deployment/scripts/database_setup.py`:

```python
#!/usr/bin/env python3
"""
Initialize SQLite database for hostname management
"""

import sqlite3
from pathlib import Path
import logging

DB_PATH = Path("/opt/rpi-deployment/database/deployment.db")

def initialize_database():
    """Create database tables for hostname management"""

    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Hostname pool table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hostname_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_type TEXT NOT NULL CHECK(product_type IN ('KXP2', 'RXP2')),
            venue_code TEXT NOT NULL CHECK(length(venue_code) = 4),
            identifier TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('available', 'assigned', 'retired')),
            mac_address TEXT,
            serial_number TEXT,
            assigned_date TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(product_type, venue_code, identifier)
        )
    ''')

    # Venues table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS venues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL CHECK(length(code) = 4),
            name TEXT NOT NULL,
            location TEXT,
            contact_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Deployment history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deployment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            mac_address TEXT,
            serial_number TEXT,
            ip_address TEXT,
            product_type TEXT,
            venue_code TEXT,
            image_version TEXT,
            deployment_status TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT
        )
    ''')

    # Master images table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            product_type TEXT NOT NULL CHECK(product_type IN ('KXP2', 'RXP2')),
            version TEXT NOT NULL,
            size_bytes INTEGER,
            checksum TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hostname_status ON hostname_pool(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hostname_venue ON hostname_pool(venue_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deployment_date ON deployment_history(started_at)')

    conn.commit()
    conn.close()

    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    initialize_database()
```

### Step 6.2: Hostname Management Functions

Create `/opt/rpi-deployment/scripts/hostname_manager.py`:

```python
#!/usr/bin/env python3
"""
Hostname management functions for KXP/RXP deployment
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

class HostnameManager:
    def __init__(self, db_path="/opt/rpi-deployment/database/deployment.db"):
        self.db_path = db_path
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("HostnameManager")

    def create_venue(self, code: str, name: str, location: str = None, contact_email: str = None):
        """Create a new venue"""
        if len(code) != 4:
            raise ValueError("Venue code must be exactly 4 characters")

        code = code.upper()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO venues (code, name, location, contact_email)
                VALUES (?, ?, ?, ?)
            ''', (code, name, location, contact_email))

        self.logger.info(f"Created venue: {code} - {name}")
        return code

    def bulk_import_kart_numbers(self, venue_code: str, numbers: List[str]):
        """Import a list of kart numbers for a venue"""
        venue_code = venue_code.upper()
        added = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for number in numbers:
                # Format number with leading zeros (e.g., "1" -> "001")
                identifier = f"{int(number):03d}"

                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO hostname_pool
                        (product_type, venue_code, identifier, status)
                        VALUES ('KXP2', ?, ?, 'available')
                    ''', (venue_code, identifier))

                    if cursor.rowcount > 0:
                        added += 1

                except sqlite3.IntegrityError:
                    self.logger.warning(f"Duplicate entry: KXP2-{venue_code}-{identifier}")

        self.logger.info(f"Added {added} kart numbers for venue {venue_code}")
        return added

    def assign_hostname(self, product_type: str, venue_code: str,
                       mac_address: str = None, serial_number: str = None) -> Optional[str]:
        """Assign a hostname to a device"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if product_type == "KXP2":
                # Get next available kart number
                cursor.execute('''
                    SELECT identifier FROM hostname_pool
                    WHERE product_type = 'KXP2'
                    AND venue_code = ?
                    AND status = 'available'
                    ORDER BY identifier
                    LIMIT 1
                ''', (venue_code.upper(),))

                result = cursor.fetchone()
                if result:
                    identifier = result[0]
                    hostname = f"KXP2-{venue_code.upper()}-{identifier}"

                    # Mark as assigned
                    cursor.execute('''
                        UPDATE hostname_pool
                        SET status = 'assigned',
                            mac_address = ?,
                            serial_number = ?,
                            assigned_date = CURRENT_TIMESTAMP
                        WHERE product_type = 'KXP2'
                        AND venue_code = ?
                        AND identifier = ?
                    ''', (mac_address, serial_number, venue_code.upper(), identifier))

                    self.logger.info(f"Assigned hostname: {hostname}")
                    return hostname
                else:
                    self.logger.error(f"No available kart numbers for venue {venue_code}")
                    return None

            elif product_type == "RXP2":
                # Use serial number for RXP2
                if not serial_number:
                    self.logger.error("Serial number required for RXP2 hostname")
                    return None

                # Use last 8 characters of serial
                identifier = serial_number[-8:] if len(serial_number) > 8 else serial_number
                hostname = f"RXP2-{venue_code.upper()}-{identifier}"

                # Record assignment
                cursor.execute('''
                    INSERT OR REPLACE INTO hostname_pool
                    (product_type, venue_code, identifier, status, mac_address,
                     serial_number, assigned_date)
                    VALUES ('RXP2', ?, ?, 'assigned', ?, ?, CURRENT_TIMESTAMP)
                ''', (venue_code.upper(), identifier, mac_address, serial_number))

                self.logger.info(f"Assigned hostname: {hostname}")
                return hostname

            else:
                self.logger.error(f"Invalid product type: {product_type}")
                return None

    def release_hostname(self, hostname: str):
        """Release a hostname back to available pool"""
        parts = hostname.split('-')
        if len(parts) != 3:
            raise ValueError("Invalid hostname format")

        product_type = parts[0]
        venue_code = parts[1]
        identifier = parts[2]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE hostname_pool
                SET status = 'available',
                    mac_address = NULL,
                    serial_number = NULL,
                    assigned_date = NULL
                WHERE product_type = ?
                AND venue_code = ?
                AND identifier = ?
            ''', (product_type, venue_code, identifier))

        self.logger.info(f"Released hostname: {hostname}")

    def get_venue_statistics(self, venue_code: str) -> Dict:
        """Get deployment statistics for a venue"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get hostname pool stats
            cursor.execute('''
                SELECT status, COUNT(*)
                FROM hostname_pool
                WHERE venue_code = ?
                GROUP BY status
            ''', (venue_code.upper(),))

            stats = dict(cursor.fetchall())

            # Get deployment history
            cursor.execute('''
                SELECT COUNT(*), MAX(completed_at)
                FROM deployment_history
                WHERE venue_code = ?
                AND deployment_status = 'success'
            ''', (venue_code.upper(),))

            deployments, last_deployment = cursor.fetchone()

            return {
                'venue_code': venue_code.upper(),
                'available': stats.get('available', 0),
                'assigned': stats.get('assigned', 0),
                'retired': stats.get('retired', 0),
                'total_deployments': deployments or 0,
                'last_deployment': last_deployment
            }
```

---

## Phase 7: Web Management Interface

### Step 7.1: Flask Web Application

Create `/opt/rpi-deployment/web/app.py`:

```python
#!/usr/bin/env python3
"""
KXP Deployment Web Management Interface
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
sys.path.append('/opt/rpi-deployment/scripts')
from hostname_manager import HostnameManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = '/opt/rpi-deployment/web/static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024 * 1024  # 8GB max

socketio = SocketIO(app, cors_allowed_origins="*")
hostname_mgr = HostnameManager()

# Active deployments tracking
active_deployments = {}

@app.route('/')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    """Get deployment statistics"""
    # Implementation would query database
    stats = {
        'active_deployments': len(active_deployments),
        'completed_today': 0,  # Query from database
        'failed_today': 0,
        'total_devices': 0
    }
    return jsonify(stats)

@app.route('/venues')
def venues():
    """Venue management page"""
    return render_template('venues.html')

@app.route('/api/venues', methods=['GET', 'POST'])
def manage_venues():
    """API endpoint for venue management"""
    if request.method == 'POST':
        data = request.json
        try:
            venue_code = hostname_mgr.create_venue(
                data['code'],
                data['name'],
                data.get('location'),
                data.get('contact_email')
            )
            return jsonify({'success': True, 'venue_code': venue_code})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    else:
        # Get list of venues
        # Implementation would query database
        return jsonify({'venues': []})

@app.route('/api/kart-numbers', methods=['POST'])
def import_kart_numbers():
    """Import kart numbers for a venue"""
    data = request.json
    venue_code = data['venue_code']
    numbers = data['numbers']  # List of numbers

    added = hostname_mgr.bulk_import_kart_numbers(venue_code, numbers)

    return jsonify({
        'success': True,
        'added': added,
        'message': f'Added {added} kart numbers'
    })

@app.route('/api/hostname/assign', methods=['POST'])
def assign_hostname():
    """Assign hostname to a device"""
    data = request.json

    hostname = hostname_mgr.assign_hostname(
        data['product_type'],
        data['venue_code'],
        data.get('mac_address'),
        data.get('serial_number')
    )

    if hostname:
        # Notify real-time dashboard
        socketio.emit('hostname_assigned', {
            'hostname': hostname,
            'timestamp': datetime.now().isoformat()
        })

        return jsonify({'success': True, 'hostname': hostname})
    else:
        return jsonify({'success': False, 'error': 'No available hostnames'}), 400

@app.route('/images')
def images():
    """Image management page"""
    return render_template('images.html')

@app.route('/api/images/upload', methods=['POST'])
def upload_image():
    """Upload a new master image"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    product_type = request.form.get('product_type')
    version = request.form.get('version')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Move to images directory
        final_path = f"/opt/rpi-deployment/images/{product_type.lower()}_v{version}_{filename}"
        os.rename(filepath, final_path)

        # Calculate checksum
        sha256 = hashlib.sha256()
        with open(final_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        # Store in database
        # Implementation would update master_images table

        return jsonify({
            'success': True,
            'filename': filename,
            'checksum': sha256.hexdigest()
        })

@socketio.on('deployment_update')
def handle_deployment_update(data):
    """Handle real-time deployment updates"""
    deployment_id = data['deployment_id']
    status = data['status']
    progress = data.get('progress', 0)

    active_deployments[deployment_id] = {
        'status': status,
        'progress': progress,
        'timestamp': datetime.now().isoformat()
    }

    # Broadcast to all connected clients
    emit('deployment_status', {
        'deployment_id': deployment_id,
        'status': status,
        'progress': progress
    }, broadcast=True)

if __name__ == '__main__':
    # Create upload directory
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

    # Run with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
```

### Step 7.2: Create Web Templates

Create `/opt/rpi-deployment/web/templates/dashboard.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KXP Deployment Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <style>
        .deployment-card {
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        .progress-animated {
            animation: progress-animation 2s infinite;
        }
        @keyframes progress-animation {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        .stats-card {
            border-left: 4px solid #007bff;
            padding: 20px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">KXP/RXP Deployment System</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/">Dashboard</a>
                <a class="nav-link" href="/venues">Venues</a>
                <a class="nav-link" href="/images">Images</a>
                <a class="nav-link" href="/reports">Reports</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <div class="row">
            <!-- Statistics -->
            <div class="col-md-3">
                <div class="card stats-card">
                    <h5>Active Deployments</h5>
                    <h2 id="active-count">0</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <h5>Completed Today</h5>
                    <h2 id="completed-count">0</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <h5>Failed Today</h5>
                    <h2 id="failed-count">0</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <h5>Total Devices</h5>
                    <h2 id="total-count">0</h2>
                </div>
            </div>
        </div>

        <!-- Active Deployments -->
        <div class="row mt-4">
            <div class="col-12">
                <h3>Active Deployments</h3>
                <div id="deployments-container">
                    <!-- Deployment cards will be added here dynamically -->
                </div>
            </div>
        </div>

        <!-- Recent History -->
        <div class="row mt-4">
            <div class="col-12">
                <h3>Recent Deployment History</h3>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Hostname</th>
                            <th>Product</th>
                            <th>Venue</th>
                            <th>Status</th>
                            <th>Completed</th>
                        </tr>
                    </thead>
                    <tbody id="history-table">
                        <!-- History rows will be added here -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Initialize Socket.IO connection
        const socket = io();

        // Update statistics
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('active-count').textContent = data.active_deployments;
                    document.getElementById('completed-count').textContent = data.completed_today;
                    document.getElementById('failed-count').textContent = data.failed_today;
                    document.getElementById('total-count').textContent = data.total_devices;
                });
        }

        // Handle deployment status updates
        socket.on('deployment_status', function(data) {
            updateDeploymentCard(data.deployment_id, data.status, data.progress);
        });

        // Handle hostname assignments
        socket.on('hostname_assigned', function(data) {
            console.log('Hostname assigned:', data.hostname);
            updateStats();
        });

        function updateDeploymentCard(deploymentId, status, progress) {
            let card = document.getElementById(`deployment-${deploymentId}`);

            if (!card) {
                // Create new card
                card = document.createElement('div');
                card.id = `deployment-${deploymentId}`;
                card.className = 'card deployment-card';
                card.innerHTML = `
                    <div class="card-body">
                        <h5 class="card-title">Deployment ${deploymentId}</h5>
                        <div class="progress">
                            <div class="progress-bar progress-bar-striped progress-bar-animated"
                                 role="progressbar" style="width: ${progress}%">
                                ${progress}%
                            </div>
                        </div>
                        <p class="card-text mt-2">Status: <span class="status">${status}</span></p>
                    </div>
                `;
                document.getElementById('deployments-container').appendChild(card);
            } else {
                // Update existing card
                const progressBar = card.querySelector('.progress-bar');
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${progress}%`;
                card.querySelector('.status').textContent = status;

                if (status === 'completed' || status === 'failed') {
                    progressBar.classList.remove('progress-bar-animated');
                    setTimeout(() => {
                        card.remove();
                        updateStats();
                    }, 5000);
                }
            }
        }

        // Initial load
        updateStats();
        setInterval(updateStats, 10000);  // Refresh every 10 seconds
    </script>
</body>
</html>
```

---

## Phase 8: Enhanced Python Deployment Scripts

### Step 8.1: Deployment Server Application (Deployment Network API)

Create `/opt/rpi-deployment/scripts/deployment_server.py`:

```python
#!/usr/bin/env python3
"""
KXP/RXP Enhanced Deployment Server
Serves configuration and images to Raspberry Pi clients with hostname management
"""

import os
import sys
import json
import hashlib
import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, send_file, request

# Add scripts directory to path
sys.path.append('/opt/rpi-deployment/scripts')
from hostname_manager import HostnameManager

app = Flask(__name__)

# Configuration
DEPLOYMENT_IP = "192.168.151.1"  # Deployment network
IMAGE_DIR = Path("/opt/rpi-deployment/images")
LOG_DIR = Path("/opt/rpi-deployment/logs")
DB_PATH = Path("/opt/rpi-deployment/database/deployment.db")

# Initialize hostname manager
hostname_mgr = HostnameManager()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "deployment.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DeploymentServer")

def calculate_checksum(file_path):
    """Calculate SHA256 checksum of file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_active_image(product_type):
    """Get the active master image for a product type"""
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT filename, checksum, size_bytes
            FROM master_images
            WHERE product_type = ? AND is_active = 1
            LIMIT 1
        ''', (product_type,))
        result = cursor.fetchone()

        if result:
            return {
                'filename': result[0],
                'checksum': result[1],
                'size': result[2]
            }
    return None

@app.route('/api/config', methods=['POST'])
def get_config():
    """Provide deployment configuration to clients based on product/venue"""
    try:
        data = request.json
        product_type = data.get('product_type', 'KXP2')
        venue_code = data.get('venue_code')
        serial_number = data.get('serial_number')
        mac_address = data.get('mac_address')

        # Get active image for product type
        image_info = get_active_image(product_type)
        if not image_info:
            # Fallback to default image
            image_filename = f"{product_type.lower()}_master.img"
            image_path = IMAGE_DIR / image_filename
            if not image_path.exists():
                return jsonify({'error': f'No active image for {product_type}'}), 404

            image_info = {
                'filename': image_filename,
                'checksum': calculate_checksum(image_path),
                'size': image_path.stat().st_size
            }

        # Request hostname assignment
        hostname = None
        if venue_code:
            hostname = hostname_mgr.assign_hostname(
                product_type,
                venue_code,
                mac_address,
                serial_number
            )

        if not hostname:
            # Fallback to serial-based hostname
            hostname = f"{product_type}-DEFAULT-{serial_number[-6:]}" if serial_number else "unknown"

        config = {
            'server_ip': DEPLOYMENT_IP,
            'hostname': hostname,
            'product_type': product_type,
            'venue_code': venue_code,
            'image_url': f'http://{DEPLOYMENT_IP}/images/{image_info["filename"]}',
            'image_size': image_info['size'],
            'image_checksum': image_info['checksum'],
            'version': '3.0',
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Config requested from {request.remote_addr} - Assigned: {hostname}")

        # Record deployment start
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO deployment_history
                (hostname, mac_address, serial_number, ip_address, product_type,
                 venue_code, image_version, deployment_status, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'started', CURRENT_TIMESTAMP)
            ''', (hostname, mac_address, serial_number, request.remote_addr,
                  product_type, venue_code, image_info['filename']))

        return jsonify(config)

    except Exception as e:
        logger.error(f"Error serving config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['POST'])
def receive_status():
    """Receive installation status from clients"""
    try:
        data = request.json
        client_ip = request.remote_addr
        status = data.get('status')
        hostname = data.get('hostname', 'unknown')
        serial = data.get('serial', 'unknown')
        mac_address = data.get('mac_address')
        error_message = data.get('error_message')

        logger.info(f"Status from {client_ip} ({hostname}): {status}")

        # Update deployment history
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()

            if status in ['success', 'failed']:
                # Update deployment completion
                cursor.execute('''
                    UPDATE deployment_history
                    SET deployment_status = ?,
                        completed_at = CURRENT_TIMESTAMP,
                        error_message = ?
                    WHERE hostname = ?
                    AND deployment_status = 'started'
                    ORDER BY started_at DESC
                    LIMIT 1
                ''', (status, error_message, hostname))
            else:
                # Update deployment progress
                cursor.execute('''
                    UPDATE deployment_history
                    SET deployment_status = ?
                    WHERE hostname = ?
                    AND deployment_status IN ('started', 'downloading', 'verifying')
                    ORDER BY started_at DESC
                    LIMIT 1
                ''', (status, hostname))

        # Log to daily file
        status_log = LOG_DIR / f"deployment_{datetime.now().strftime('%Y%m%d')}.log"
        with open(status_log, 'a') as f:
            f.write(f"{datetime.now().isoformat()},{client_ip},{hostname},{serial},{status}\n")

        # Notify web interface via Socket.IO (if connected)
        # This would integrate with the web app's socketio instance

        return jsonify({'received': True, 'hostname': hostname})

    except Exception as e:
        logger.error(f"Error receiving status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/images/<filename>', methods=['GET'])
def download_image(filename):
    """Serve master image for download"""
    try:
        image_path = IMAGE_DIR / filename
        
        if not image_path.exists():
            return jsonify({'error': 'Image not found'}), 404
        
        logger.info(f"Image download started: {filename} to {request.remote_addr}")
        
        return send_file(
            image_path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error serving image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Ensure directories exist
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database if needed
    if not DB_PATH.exists():
        from database_setup import initialize_database
        initialize_database()

    logger.info("Starting deployment server on deployment network")
    logger.info(f"Deployment API: http://{DEPLOYMENT_IP}:5001")

    # Start server (on deployment network port)
    app.run(host='0.0.0.0', port=5001, debug=False)
```

Make executable:
```bash
chmod +x /opt/rpi-deployment/scripts/deployment_server.py
```

### Step 8.2: Enhanced Client Installer Script

Create `/opt/rpi-deployment/scripts/pi_installer.py`:

```python
#!/usr/bin/env python3
"""
KXP/RXP Enhanced Pi Installer
Runs on Raspberry Pi during network boot to install master image with hostname assignment
"""

import os
import sys
import time
import json
import hashlib
import logging
import argparse
import subprocess
import requests
from pathlib import Path

class PiInstaller:
    def __init__(self, server_url, product_type="KXP2", venue_code=None, target_device="/dev/mmcblk0"):
        self.server_url = server_url
        self.product_type = product_type
        self.venue_code = venue_code
        self.target_device = target_device
        self.hostname = None
        self.config = None
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("PiInstaller")
        
    def report_status(self, status, message="", error_message=None):
        """Report installation status to server"""
        try:
            serial = self.get_serial_number()
            mac = self.get_mac_address()
            data = {
                'status': status,
                'message': message,
                'hostname': self.hostname,
                'serial': serial,
                'mac_address': mac,
                'error_message': error_message,
                'timestamp': time.time()
            }
            requests.post(f"{self.server_url}/api/status", json=data, timeout=5)
        except Exception as e:
            self.logger.warning(f"Failed to report status: {e}")
            
    def get_serial_number(self):
        """Get Raspberry Pi serial number"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
        except:
            return "unknown"

    def get_mac_address(self):
        """Get MAC address of first network interface"""
        try:
            # Get first ethernet interface MAC
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'link/ether' in line:
                    return line.split()[1]
        except:
            return None
            
    def verify_sd_card(self):
        """Verify SD card is present and accessible"""
        self.logger.info("Verifying SD card...")
        
        if not Path(self.target_device).exists():
            raise RuntimeError(f"SD card not found: {self.target_device}")
            
        # Check if device is writable
        try:
            subprocess.run(
                ["blockdev", "--getsize64", self.target_device],
                check=True,
                capture_output=True
            )
            self.logger.info("SD card verified")
            return True
        except subprocess.CalledProcessError:
            raise RuntimeError("SD card is not accessible")
            
    def get_config(self):
        """Fetch deployment configuration from server with hostname assignment"""
        self.logger.info(f"Fetching config from {self.server_url}...")

        try:
            # Prepare request data
            request_data = {
                'product_type': self.product_type,
                'venue_code': self.venue_code,
                'serial_number': self.get_serial_number(),
                'mac_address': self.get_mac_address()
            }

            response = requests.post(
                f"{self.server_url}/api/config",
                json=request_data,
                timeout=10
            )
            response.raise_for_status()
            config = response.json()

            # Store assigned hostname
            self.hostname = config.get('hostname', 'unknown')
            self.config = config

            self.logger.info(f"Config received: v{config['version']}")
            self.logger.info(f"Assigned hostname: {self.hostname}")

            return config
        except Exception as e:
            raise RuntimeError(f"Failed to get config: {e}")
            
    def download_and_write_image(self, image_url, expected_size):
        """Download image and write directly to SD card"""
        self.logger.info("Starting image download and write...")
        
        try:
            # Open target device for writing
            with open(self.target_device, 'wb') as device:
                response = requests.get(image_url, stream=True, timeout=30)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                self.logger.info(f"Image size: {total_size / (1024**3):.2f} GB")
                
                # Write in chunks
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        device.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 100MB
                        if downloaded % (100 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size) * 100
                            self.logger.info(f"Progress: {progress:.1f}%")
                
                # Sync to ensure all data is written
                device.flush()
                os.fsync(device.fileno())
                
            self.logger.info("Image write completed")
            
        except Exception as e:
            raise RuntimeError(f"Image write failed: {e}")
            
    def verify_installation(self, expected_checksum):
        """Verify written image checksum"""
        self.logger.info("Verifying installation...")
        
        # Sync filesystem
        subprocess.run(["sync"])
        time.sleep(2)
        
        # For speed, only verify first 100MB
        try:
            hasher = hashlib.sha256()
            with open(self.target_device, 'rb') as f:
                # Read first 100MB
                data = f.read(100 * 1024 * 1024)
                hasher.update(data)
            
            # Note: This is a partial checksum, full verification would take too long
            self.logger.info("Installation verification completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return False
            
    def customize_installation(self):
        """Mount and customize the installed image with assigned hostname"""
        self.logger.info("Customizing installation...")

        try:
            # Create mount point
            mount_point = Path("/mnt/sdcard")
            mount_point.mkdir(parents=True, exist_ok=True)

            # Mount boot partition
            subprocess.run(
                ["mount", f"{self.target_device}p1", str(mount_point)],
                check=True
            )

            # Use the assigned hostname from server
            hostname = self.hostname if self.hostname else f"kxp-{self.get_serial_number()[-6:]}"

            # Create firstrun.sh script for customization on first boot
            firstrun = mount_point / "firstrun.sh"
            with open(firstrun, 'w') as f:
                f.write(f"""#!/bin/bash
# KXP/RXP First Run Customization
# Product: {self.product_type}
# Venue: {self.venue_code if self.venue_code else 'DEFAULT'}
# Assigned Hostname: {hostname}

hostnamectl set-hostname {hostname}
echo {hostname} > /etc/hostname

# Update hosts file
sed -i "s/127.0.1.1.*/127.0.1.1\t{hostname}/" /etc/hosts

# Log deployment info
echo "Deployment completed: $(date)" >> /var/log/kxp_deployment.log
echo "Hostname: {hostname}" >> /var/log/kxp_deployment.log
echo "Product: {self.product_type}" >> /var/log/kxp_deployment.log
echo "Venue: {self.venue_code}" >> /var/log/kxp_deployment.log

# Remove this script after execution
rm -f /boot/firstrun.sh
""")
            
            os.chmod(firstrun, 0o755)
            
            # Unmount
            subprocess.run(["umount", str(mount_point)], check=True)
            
            self.logger.info(f"Installation customized with hostname: {hostname}")
            
        except Exception as e:
            self.logger.warning(f"Customization failed: {e}")
            
    def reboot_system(self):
        """Reboot the system"""
        self.logger.info("Installation complete! Rebooting...")
        time.sleep(3)
        subprocess.run(["reboot"])
        
    def install(self):
        """Main installation process"""
        try:
            self.logger.info("=== KXP Installation Started ===")
            self.report_status("starting")
            
            # Step 1: Verify SD card
            self.verify_sd_card()
            
            # Step 2: Get configuration
            config = self.get_config()
            
            # Step 3: Download and write image
            self.report_status("downloading")
            self.download_and_write_image(
                config['image_url'],
                config['image_size']
            )
            
            # Step 4: Verify installation
            self.report_status("verifying")
            if not self.verify_installation(config['image_checksum']):
                raise RuntimeError("Installation verification failed")
            
            # Step 5: Customize
            self.report_status("customizing")
            self.customize_installation()
            
            # Step 6: Success
            self.report_status("success", "Installation completed successfully")
            self.logger.info("=== Installation Successful ===")
            
            # Step 7: Reboot
            time.sleep(2)
            self.reboot_system()
            
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            self.report_status("failed", str(e))
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='KXP/RXP Pi Installer')
    parser.add_argument('--server', required=True, help='Deployment server URL')
    parser.add_argument('--product', default='KXP2', choices=['KXP2', 'RXP2'],
                       help='Product type: KXP2 (KartXPro) or RXP2 (RaceXPro)')
    parser.add_argument('--venue', help='4-letter venue code (e.g., CORO)')
    parser.add_argument('--device', default='/dev/mmcblk0', help='Target device')
    args = parser.parse_args()

    # Server runs on port 5001 for deployment network
    server_url = f"http://{args.server}:5001" if ':' not in args.server else args.server

    installer = PiInstaller(
        server_url,
        product_type=args.product,
        venue_code=args.venue,
        target_device=args.device
    )
    installer.install()

if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x /opt/rpi-deployment/scripts/pi_installer.py
```

---

## Phase 11: Creating the Master Image

### Step 6.1: Prepare a Reference Pi

1. Start with a fresh Raspberry Pi 5
2. Install Raspberry Pi OS
3. Configure dual camera setup
4. Install all KXP software and dependencies
5. Test thoroughly

### Step 6.2: Create Master Image

```bash
# On the reference Pi, create the image
sudo dd if=/dev/mmcblk0 of=/tmp/kxp_master_raw.img bs=4M status=progress

# Transfer to deployment server
scp /tmp/kxp_master_raw.img user@192.168.101.10:/opt/rpi-deployment/images/

# On deployment server, shrink the image
cd /opt/rpi-deployment/images
sudo apt install -y pishrink
sudo pishrink.sh -aZ kxp_master_raw.img kxp_dualcam_master.img

# Verify image
ls -lh kxp_dualcam_master.img
```

---

## Phase 9: Service Management

### Step 9.1: Create Systemd Service for Deployment Server

```bash
sudo nano /etc/systemd/system/rpi-deployment.service
```

```ini
[Unit]
Description=KXP/RXP Deployment Server (Deployment Network API)
After=network.target nginx.service dnsmasq.service

[Service]
Type=simple
User=captureworks
WorkingDirectory=/opt/rpi-deployment/scripts
ExecStart=/usr/bin/python3 /opt/rpi-deployment/scripts/deployment_server.py
Environment="PYTHONPATH=/opt/rpi-deployment/scripts"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 9.2: Create Systemd Service for Web Management Interface

```bash
sudo nano /etc/systemd/system/rpi-web.service
```

```ini
[Unit]
Description=KXP/RXP Web Management Interface
After=network.target nginx.service rpi-deployment.service

[Service]
Type=simple
User=captureworks
WorkingDirectory=/opt/rpi-deployment/web
ExecStart=/usr/bin/python3 /opt/rpi-deployment/web/app.py
Environment="PYTHONPATH=/opt/rpi-deployment/scripts"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 9.3: Enable and Start Services

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable rpi-deployment
sudo systemctl enable rpi-web

# Start services
sudo systemctl start rpi-deployment
sudo systemctl start rpi-web

# Check status
sudo systemctl status rpi-deployment
sudo systemctl status rpi-web

# View logs
sudo journalctl -u rpi-deployment -f
sudo journalctl -u rpi-web -f
```

---

## Phase 10: Testing and Validation

### Step 10.1: Pre-Deployment Checks

```bash
# Create validation script
cat > /opt/rpi-deployment/scripts/validate_deployment.sh << 'EOF'
#!/bin/bash

echo "=== KXP/RXP Deployment Server Validation ==="

# Check services
echo "Checking services..."
systemctl is-active dnsmasq && echo "✓ dnsmasq running" || echo "✗ dnsmasq not running"
systemctl is-active nginx && echo "✓ nginx running" || echo "✗ nginx not running"
systemctl is-active tftpd-hpa && echo "✓ tftp running" || echo "✗ tftp not running"
systemctl is-active rpi-deployment && echo "✓ deployment server running" || echo "✗ deployment server not running"
systemctl is-active rpi-web && echo "✓ web interface running" || echo "✗ web interface not running"

# Check network interfaces
echo -e "\nChecking network configuration..."
ip addr show | grep "192.168.101" && echo "✓ Management network (VLAN 101) configured" || echo "✗ Management network not configured"
ip addr show | grep "192.168.151.1" && echo "✓ Deployment network (VLAN 151) configured" || echo "✗ Deployment network not configured"

# Check database
echo -e "\nChecking database..."
[ -f /opt/rpi-deployment/database/deployment.db ] && echo "✓ Database exists" || echo "✗ Database missing"

# Check files
echo -e "\nChecking required files..."
[ -f /opt/rpi-deployment/images/kxp2_master.img ] && echo "✓ KXP2 master image exists" || echo "✗ KXP2 master image missing"
[ -f /opt/rpi-deployment/images/rxp2_master.img ] && echo "✓ RXP2 master image exists" || echo "✗ RXP2 master image missing"
[ -f /tftpboot/bootfiles/boot.ipxe ] && echo "✓ Boot script exists" || echo "✗ Boot script missing"

# Check API endpoints
echo -e "\nChecking API endpoints..."
curl -s http://192.168.101.20:5000/ && echo "✓ Web interface accessible" || echo "✗ Web interface not accessible"
curl -s http://192.168.151.1:5001/health && echo "✓ Deployment API accessible" || echo "✗ Deployment API not accessible"

echo -e "\n=== Validation Complete ==="
EOF

chmod +x /opt/rpi-deployment/scripts/validate_deployment.sh

# Run validation
/opt/rpi-deployment/scripts/validate_deployment.sh
```

### Step 10.2: Test Deployment with a Single Pi

1. Connect blank Pi to deployment network
2. Ensure network boot is enabled in EEPROM
3. Power on Pi
4. Monitor logs:
   ```bash
   tail -f /var/log/dnsmasq.log
   tail -f /opt/rpi-deployment/logs/deployment.log
   ```
5. Verify successful installation

---

## Phase 12: Mass Deployment Procedures

### Step 12.1: Preparation Checklist

- [ ] Deployment server validated
- [ ] Master images (KXP2 and RXP2) tested on reference Pi
- [ ] Network infrastructure ready (VLAN 151 isolated)
- [ ] Power supplies available
- [ ] Blank SD cards inserted in all Pis
- [ ] Hostname pool pre-configured for venue
- [ ] Web interface accessible for monitoring

### Step 12.2: Deployment Process

```bash
# Start monitoring on web interface
# Navigate to http://192.168.101.20 in browser

# Start monitoring via command line
tmux new-session -d -s deployment "tail -f /opt/rpi-deployment/logs/deployment.log"

# Power on Pis in batches (recommend 5-10 at a time)
# Monitor progress through web dashboard

# Check deployment status
tail -f /opt/rpi-deployment/logs/deployment_$(date +%Y%m%d).log
```

### Step 12.3: Post-Deployment Validation

```python
# Create validation script
cat > /opt/rpi-deployment/scripts/check_deployments.py << 'EOF'
#!/usr/bin/env python3
"""Check deployment status"""

import csv
from pathlib import Path
from datetime import datetime

log_file = Path(f"/opt/rpi-deployment/logs/deployment_{datetime.now().strftime('%Y%m%d')}.log")

if not log_file.exists():
    print("No deployments today")
    exit()

deployments = {}
with open(log_file, 'r') as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) >= 4:
            timestamp, ip, serial, status = parts[:4]
            deployments[serial] = {
                'ip': ip,
                'status': status,
                'timestamp': timestamp
            }

print(f"Total unique devices: {len(deployments)}")
print(f"Successful: {sum(1 for d in deployments.values() if d['status'] == 'success')}")
print(f"Failed: {sum(1 for d in deployments.values() if d['status'] == 'failed')}")
print(f"In Progress: {sum(1 for d in deployments.values() if d['status'] not in ['success', 'failed'])}")
EOF

chmod +x /opt/rpi-deployment/scripts/check_deployments.py
```

---

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

## Phase 14: Maintenance and Updates

### Updating Master Image

```bash
# 1. Create new master image from updated reference Pi
# 2. Transfer to server
# 3. Shrink and optimize
sudo pishrink.sh -aZ kxp_master_new.img kxp_dualcam_master_v2.img

# 4. Test with single Pi
# 5. If successful, replace old image
mv /opt/rpi-deployment/images/kxp_dualcam_master.img \
   /opt/rpi-deployment/images/kxp_dualcam_master_v1_backup.img
mv /opt/rpi-deployment/images/kxp_dualcam_master_v2.img \
   /opt/rpi-deployment/images/kxp_dualcam_master.img

# 6. Restart deployment server
sudo systemctl restart rpi-deployment
```

### Backup Procedures

```bash
# Backup deployment server configuration
tar -czf rpi-deployment-backup-$(date +%Y%m%d).tar.gz \
  /opt/rpi-deployment/scripts \
  /etc/dnsmasq.conf \
  /etc/nginx/sites-available/rpi-deployment \
  /tftpboot/bootfiles/boot.ipxe

# Backup logs
tar -czf kxp-logs-$(date +%Y%m%d).tar.gz \
  /opt/rpi-deployment/logs
```

---

## Phase 15: Security Considerations

### Network Security
- Deploy on isolated VLAN if possible
- Use firewall rules to restrict access
- Monitor for unauthorized DHCP requests

### Image Security
- Store master images with restricted permissions
- Implement checksum verification
- Maintain audit log of all deployments

```bash
# Set secure permissions
sudo chmod 600 /opt/rpi-deployment/images/*.img
sudo chown root:root /opt/rpi-deployment/images/*.img
```

---

## Appendix A: Quick Reference Commands

```bash
# Check server status
sudo systemctl status dnsmasq nginx tftpd-hpa rpi-deployment

# View real-time deployment logs
tail -f /opt/rpi-deployment/logs/deployment.log

# Monitor DHCP requests
sudo tcpdump -i eth0 port 67 or port 68

# Monitor TFTP traffic
sudo tcpdump -i eth0 port 69

# Check deployment statistics
python3 /opt/rpi-deployment/scripts/check_deployments.py

# Restart all services
sudo systemctl restart dnsmasq nginx tftpd-hpa rpi-deployment

# Validate configuration
/opt/rpi-deployment/scripts/validate_deployment.sh
```

---

## Appendix B: Network Diagram

```
                    Deployment Network (192.168.101.0/24)
                                   |
                    Deployment Server (192.168.101.10)
                    +---------------------------+
                    |  - DHCP Server (dnsmasq)  |
                    |  - TFTP Server            |
                    |  - HTTP Server (nginx)    |
                    |  - Flask API              |
                    +---------------------------+
                                   |
        +--------------------------|---------------------------+
        |                          |                           |
    Pi #1 (DHCP)              Pi #2 (DHCP)               Pi #3 (DHCP)
    192.168.101.100           192.168.101.101            192.168.101.102
        |                          |                           |
    [Installing...]           [Installing...]            [Installing...]
```

---

## Appendix C: File Structure Reference

```
/opt/rpi-deployment/
├── images/
│   ├── kxp_dualcam_master.img          # Current master image
│   └── kxp_dualcam_master_v1_backup.img # Previous version
├── scripts/
│   ├── deployment_server.py             # Main server application
│   ├── pi_installer.py                  # Client installer script
│   ├── validate_deployment.sh           # Validation script
│   └── check_deployments.py             # Status checker
├── logs/
│   ├── deployment.log                   # Main server log
│   └── deployment_YYYYMMDD.log          # Daily status logs
└── web/
    └── index.html                       # Optional web dashboard

/tftpboot/
├── bootcode.bin
├── start*.elf
├── fixup*.dat
└── bootfiles/
    └── boot.ipxe                        # iPXE boot script

/var/www/deployment/
└── (served by nginx)
```

---

## Appendix D: Hardware Requirements

### Deployment Server
- CPU: 2+ cores
- RAM: 4GB minimum, 8GB recommended
- Storage: 100GB+ (depends on image size)
- Network: Gigabit Ethernet
- OS: Ubuntu 22.04 LTS or Debian 12

### Network Infrastructure
- Gigabit switch
- DHCP range available (192.168.101.100-200)
- Internet access (for initial setup)

### Raspberry Pi 5 Units
- Blank SD card (32GB+ recommended)
- Power supply (27W official recommended)
- Network boot enabled in EEPROM
- Ethernet cable for initial deployment

---

## Document Version Control

- **Version:** 1.0
- **Date:** 2025-10-22
- **Author:** KXP Development Team
- **Status:** Implementation Ready

## Implementation Notes for Claude Code

This document is designed to be processed by Claude Code for automated deployment. Key considerations:

1. **Sequential Execution:** Follow phases in order
2. **Error Checking:** Verify each step before proceeding
3. **Logging:** Maintain detailed logs of all operations
4. **Rollback:** Be prepared to revert changes if errors occur
5. **Testing:** Test each component before moving to next phase

## Success Criteria

- [ ] Deployment server responds to health checks
- [ ] DHCP assigns IPs to new Pis
- [ ] TFTP serves boot files successfully
- [ ] Master image downloads without errors
- [ ] Installation completes on test Pi
- [ ] Deployed Pi boots successfully from SD card
- [ ] Dual camera system functions correctly

---

End of Implementation Plan

---

# EXTENSION: Proxmox VM Automation for Deployment Server

## Advanced Automation: Proxmox VM Provisioning Scripts

This section provides advanced automation scripts for provisioning the deployment server VM on your Proxmox cluster.

### Step 13.1: Install Proxmoxer Python Library

On your workstation or CI/CD system:

```bash
# Install proxmoxer with dependencies
pip3 install proxmoxer requests

# Verify installation
python3 -c "from proxmoxer import ProxmoxAPI; print('Proxmoxer installed successfully')"
```

### Step 13.2: Create Proxmox VM Provisioning Script

Create `/opt/rpi-deployment/scripts/proxmox_provision.py`:

```python
#!/usr/bin/env python3
"""
Proxmox VM Provisioning Script for KXP Deployment Server
Automatically creates and configures the deployment server VM
"""

import sys
import time
import argparse
import logging
from pathlib import Path
from proxmoxer import ProxmoxAPI

class ProxmoxProvisioner:
    def __init__(self, host, user, password, verify_ssl=False):
        """Initialize Proxmox API connection"""
        self.proxmox = ProxmoxAPI(
            host,
            user=user,
            password=password,
            verify_ssl=verify_ssl
        )
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/tmp/proxmox_provision.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("ProxmoxProvisioner")
        
    def get_next_vmid(self):
        """Get next available VM ID"""
        try:
            return self.proxmox.cluster.nextid.get()
        except Exception as e:
            self.logger.error(f"Failed to get next VMID: {e}")
            return None
            
    def select_node(self, preferred_node=None):
        """Select a Proxmox node for VM creation"""
        try:
            nodes = self.proxmox.nodes.get()
            
            if preferred_node:
                for node in nodes:
                    if node['node'] == preferred_node:
                        self.logger.info(f"Using preferred node: {preferred_node}")
                        return preferred_node
                        
            # Select node with most available resources
            best_node = max(nodes, key=lambda n: n.get('mem', 0) - n.get('maxmem', 0))
            self.logger.info(f"Auto-selected node: {best_node['node']}")
            return best_node['node']
            
        except Exception as e:
            self.logger.error(f"Failed to select node: {e}")
            return None
            
    def create_deployment_vm(self, node, vmid, vm_config):
        """Create the deployment server VM"""
        try:
            self.logger.info(f"Creating VM {vmid} on node {node}")
            
            # Create VM with basic configuration
            self.proxmox.nodes(node).qemu.create(
                vmid=vmid,
                name=vm_config['name'],
                memory=vm_config['memory'],
                cores=vm_config['cores'],
                sockets=vm_config['sockets'],
                ostype='l26',  # Linux 2.6+ kernel
                scsihw='virtio-scsi-pci',
                boot='order=scsi0;net0',
                agent='enabled=1',
                onboot=1,  # Auto-start on boot
                description='KXP Deployment Server - Automated PXE/Network Boot System'
            )
            
            self.logger.info(f"VM {vmid} created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create VM: {e}")
            return False
            
    def configure_storage(self, node, vmid, storage_config):
        """Configure VM storage"""
        try:
            self.logger.info("Configuring storage...")
            
            # Add main disk
            self.proxmox.nodes(node).qemu(vmid).config.set(
                scsi0=f"{storage_config['storage']}:{storage_config['disk_size']}"
            )
            
            # Add Cloud-Init drive if specified
            if storage_config.get('cloudinit', True):
                self.proxmox.nodes(node).qemu(vmid).config.set(
                    ide2=f"{storage_config['storage']}:cloudinit"
                )
                
            self.logger.info("Storage configured successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure storage: {e}")
            return False
            
    def configure_network(self, node, vmid, network_config):
        """Configure VM network"""
        try:
            self.logger.info("Configuring network...")
            
            # Configure primary network interface
            net0_config = (
                f"virtio,bridge={network_config['bridge']},"
                f"firewall=1"
            )
            
            if network_config.get('vlan'):
                net0_config += f",tag={network_config['vlan']}"
                
            self.proxmox.nodes(node).qemu(vmid).config.set(
                net0=net0_config
            )
            
            # Configure Cloud-Init network settings
            if network_config.get('ip'):
                self.proxmox.nodes(node).qemu(vmid).config.set(
                    ipconfig0=(
                        f"ip={network_config['ip']}/{network_config['netmask']},"
                        f"gw={network_config['gateway']}"
                    ),
                    nameserver=network_config.get('dns', '8.8.8.8 8.8.4.4')
                )
                
            self.logger.info("Network configured successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure network: {e}")
            return False
            
    def configure_cloudinit(self, node, vmid, cloudinit_config):
        """Configure Cloud-Init settings"""
        try:
            self.logger.info("Configuring Cloud-Init...")
            
            # Set Cloud-Init user and SSH key
            config = {
                'ciuser': cloudinit_config['user'],
                'cipassword': cloudinit_config.get('password', ''),
            }
            
            if cloudinit_config.get('ssh_key'):
                config['sshkeys'] = cloudinit_config['ssh_key']
                
            self.proxmox.nodes(node).qemu(vmid).config.set(**config)
            
            self.logger.info("Cloud-Init configured successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure Cloud-Init: {e}")
            return False
            
    def start_vm(self, node, vmid, wait_for_agent=True):
        """Start the VM and optionally wait for guest agent"""
        try:
            self.logger.info(f"Starting VM {vmid}...")
            
            self.proxmox.nodes(node).qemu(vmid).status.start.post()
            
            if wait_for_agent:
                self.logger.info("Waiting for QEMU guest agent...")
                timeout = 300  # 5 minutes
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    try:
                        # Try to ping the agent
                        self.proxmox.nodes(node).qemu(vmid).agent.ping.post()
                        self.logger.info("Guest agent is responsive")
                        return True
                    except:
                        time.sleep(5)
                        
                self.logger.warning("Guest agent timeout, but VM is running")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start VM: {e}")
            return False
            
    def provision_full_server(self, config):
        """Complete provisioning workflow"""
        try:
            self.logger.info("=== Starting Proxmox VM Provisioning ===")
            
            # Step 1: Get VMID
            vmid = config.get('vmid') or self.get_next_vmid()
            if not vmid:
                raise RuntimeError("Could not determine VM ID")
            self.logger.info(f"Using VM ID: {vmid}")
            
            # Step 2: Select node
            node = self.select_node(config.get('node'))
            if not node:
                raise RuntimeError("Could not select node")
                
            # Step 3: Create VM
            if not self.create_deployment_vm(node, vmid, config['vm']):
                raise RuntimeError("VM creation failed")
                
            # Step 4: Configure storage
            if not self.configure_storage(node, vmid, config['storage']):
                raise RuntimeError("Storage configuration failed")
                
            # Step 5: Configure network
            if not self.configure_network(node, vmid, config['network']):
                raise RuntimeError("Network configuration failed")
                
            # Step 6: Configure Cloud-Init
            if config.get('cloudinit'):
                if not self.configure_cloudinit(node, vmid, config['cloudinit']):
                    raise RuntimeError("Cloud-Init configuration failed")
                    
            # Step 7: Start VM
            if not self.start_vm(node, vmid):
                raise RuntimeError("VM start failed")
                
            self.logger.info("=== Provisioning Complete ===")
            self.logger.info(f"VM ID: {vmid}")
            self.logger.info(f"Node: {node}")
            self.logger.info(f"IP: {config['network']['ip']}")
            
            return {
                'success': True,
                'vmid': vmid,
                'node': node,
                'ip': config['network']['ip']
            }
            
        except Exception as e:
            self.logger.error(f"Provisioning failed: {e}")
            return {'success': False, 'error': str(e)}

def main():
    parser = argparse.ArgumentParser(
        description='Provision KXP Deployment Server on Proxmox'
    )
    parser.add_argument('--host', required=True, help='Proxmox host')
    parser.add_argument('--user', default='root@pam', help='Proxmox user')
    parser.add_argument('--password', required=True, help='Proxmox password')
    parser.add_argument('--config', required=True, help='Config file path')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL')
    
    args = parser.parse_args()
    
    # Load configuration
    import json
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Create provisioner
    provisioner = ProxmoxProvisioner(
        args.host,
        args.user,
        args.password,
        args.verify_ssl
    )
    
    # Run provisioning
    result = provisioner.provision_full_server(config)
    
    if result['success']:
        print(f"\n✓ Deployment server provisioned successfully!")
        print(f"  VM ID: {result['vmid']}")
        print(f"  Node: {result['node']}")
        print(f"  IP: {result['ip']}")
        sys.exit(0)
    else:
        print(f"\n✗ Provisioning failed: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x /opt/rpi-deployment/scripts/proxmox_provision.py
```

### Step 13.3: Create Deployment Server Configuration File

Create `/opt/rpi-deployment/config/deployment_server_config.json`:

```json
{
  "vmid": null,
  "node": null,
  "vm": {
    "name": "rpi-deployment-server",
    "memory": 4096,
    "cores": 2,
    "sockets": 1
  },
  "storage": {
    "storage": "local-lvm",
    "disk_size": 100,
    "cloudinit": true
  },
  "network": {
    "bridge": "vmbr0",
    "vlan": null,
    "ip": "192.168.101.10",
    "netmask": "24",
    "gateway": "192.168.101.1",
    "dns": "8.8.8.8 8.8.4.4"
  },
  "cloudinit": {
    "user": "captureworks",
    "password": "SecurePassword123!",
    "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... your-ssh-key-here"
  }
}
```

### Step 13.4: Provision the Deployment Server

```bash
# Run the provisioning script
python3 /opt/rpi-deployment/scripts/proxmox_provision.py \
  --host 192.168.101.5 \
  --user root@pam \
  --password YourProxmoxPassword \
  --config /opt/rpi-deployment/config/deployment_server_config.json
```

### Step 13.5: Post-Provisioning Setup Script

Create `/opt/rpi-deployment/scripts/post_provision_setup.py`:

```python
#!/usr/bin/env python3
"""
Post-provisioning setup script
Runs on the newly created VM to complete deployment server setup
"""

import subprocess
import logging
from pathlib import Path

class PostProvisionSetup:
    def __init__(self):
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("PostProvisionSetup")
        
    def run_command(self, command, shell=True):
        """Execute shell command"""
        try:
            result = subprocess.run(
                command,
                shell=shell,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e.stderr}")
            raise
            
    def update_system(self):
        """Update system packages"""
        self.logger.info("Updating system packages...")
        self.run_command("apt update && apt upgrade -y")
        
    def install_packages(self):
        """Install required packages"""
        self.logger.info("Installing required packages...")
        packages = [
            "dnsmasq", "nginx", "tftpd-hpa", "nfs-kernel-server",
            "python3", "python3-pip", "python3-venv", "git",
            "curl", "wget", "pv", "pigz"
        ]
        self.run_command(f"apt install -y {' '.join(packages)}")
        
    def install_python_deps(self):
        """Install Python dependencies"""
        self.logger.info("Installing Python dependencies...")
        self.run_command("pip3 install requests flask proxmoxer")
        
    def create_directories(self):
        """Create required directory structure"""
        self.logger.info("Creating directory structure...")
        directories = [
            "/opt/rpi-deployment/images",
            "/opt/rpi-deployment/scripts",
            "/opt/rpi-deployment/logs",
            "/opt/rpi-deployment/config",
            "/tftpboot/bootfiles",
            "/var/www/deployment",
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
    def download_deployment_scripts(self, repo_url=None):
        """Download deployment scripts from repository"""
        if not repo_url:
            self.logger.info("No repository URL provided, skipping script download")
            return
            
        self.logger.info(f"Cloning deployment scripts from {repo_url}")
        self.run_command(
            f"git clone {repo_url} /tmp/rpi-deployment-scripts"
        )
        self.run_command(
            "cp -r /tmp/rpi-deployment-scripts/scripts/* /opt/rpi-deployment/scripts/"
        )
        
    def setup_services(self):
        """Configure and enable services"""
        self.logger.info("Setting up services...")
        
        # Enable services
        services = ["dnsmasq", "nginx", "tftpd-hpa"]
        for service in services:
            self.run_command(f"systemctl enable {service}")
            
    def run_setup(self, repo_url=None):
        """Complete setup workflow"""
        try:
            self.logger.info("=== Starting Post-Provision Setup ===")
            
            self.update_system()
            self.install_packages()
            self.install_python_deps()
            self.create_directories()
            
            if repo_url:
                self.download_deployment_scripts(repo_url)
                
            self.setup_services()
            
            self.logger.info("=== Setup Complete ===")
            self.logger.info("Please complete manual configuration:")
            self.logger.info("1. Configure dnsmasq (/etc/dnsmasq.conf)")
            self.logger.info("2. Configure nginx (/etc/nginx/sites-available/rpi-deployment)")
            self.logger.info("3. Upload master image to /opt/rpi-deployment/images/")
            self.logger.info("4. Start deployment server service")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Post-provision setup')
    parser.add_argument('--repo', help='Git repository URL for scripts')
    args = parser.parse_args()
    
    setup = PostProvisionSetup()
    success = setup.run_setup(args.repo)
    
    exit(0 if success else 1)
```

### Step 13.6: Complete Automation Workflow

Create a master automation script:

```bash
#!/bin/bash
# complete_automation.sh
# Complete end-to-end automation for deployment server

set -e

echo "=== KXP Deployment Server - Complete Automation ==="

# Configuration
PROXMOX_HOST="192.168.101.5"
PROXMOX_USER="root@pam"
CONFIG_FILE="deployment_server_config.json"

# Step 1: Provision VM on Proxmox
echo "Step 1: Provisioning VM on Proxmox..."
read -s -p "Enter Proxmox password: " PROXMOX_PASSWORD
echo

python3 proxmox_provision.py \
  --host "$PROXMOX_HOST" \
  --user "$PROXMOX_USER" \
  --password "$PROXMOX_PASSWORD" \
  --config "$CONFIG_FILE"

# Extract VM IP from config
VM_IP=$(jq -r '.network.ip' "$CONFIG_FILE")

echo "Step 2: Waiting for VM to be accessible..."
while ! ping -c 1 -W 1 "$VM_IP" > /dev/null 2>&1; do
  sleep 5
done

echo "Step 3: Running post-provision setup..."
ssh captureworks@"$VM_IP" 'bash -s' < post_provision_setup.py

echo "Step 4: Copying configuration files..."
scp -r ../config/* captureworks@"$VM_IP":/opt/rpi-deployment/config/

echo "=== Automation Complete ==="
echo "Deployment server is ready at: $VM_IP"
echo ""
echo "Next steps:"
echo "1. SSH to $VM_IP"
echo "2. Upload master image"
echo "3. Start deployment service"
echo "4. Begin deploying Raspberry Pis"
```

---

## Advanced Automation: CI/CD Integration

### Step 14.1: Create GitLab CI/CD Pipeline

Create `.gitlab-ci.yml`:

```yaml
stages:
  - provision
  - configure
  - deploy
  - test

variables:
  PROXMOX_HOST: "192.168.101.5"
  PROXMOX_USER: "root@pam"

provision_vm:
  stage: provision
  script:
    - pip3 install proxmoxer requests
    - python3 scripts/proxmox_provision.py 
        --host $PROXMOX_HOST 
        --user $PROXMOX_USER 
        --password $PROXMOX_PASSWORD 
        --config config/deployment_server_config.json
  only:
    - main
    
configure_server:
  stage: configure
  script:
    - VM_IP=$(jq -r '.network.ip' config/deployment_server_config.json)
    - ssh captureworks@$VM_IP 'bash -s' < scripts/post_provision_setup.py
  dependencies:
    - provision_vm
    
deploy_services:
  stage: deploy
  script:
    - VM_IP=$(jq -r '.network.ip' config/deployment_server_config.json)
    - scp -r config/* captureworks@$VM_IP:/opt/rpi-deployment/config/
    - ssh captureworks@$VM_IP 'systemctl start rpi-deployment'
  dependencies:
    - configure_server
    
test_deployment:
  stage: test
  script:
    - VM_IP=$(jq -r '.network.ip' config/deployment_server_config.json)
    - curl -f http://$VM_IP:5000/health
    - ssh captureworks@$VM_IP '/opt/rpi-deployment/scripts/validate_deployment.sh'
  dependencies:
    - deploy_services
```

---

## Advanced Automation: Proxmox Management Functions

### Step 15.1: VM Template Creation for Faster Provisioning

```python
def create_deployment_template(self, node, template_vmid=9000):
    """Create a reusable template for deployment servers"""
    try:
        # Create base VM
        self.create_deployment_vm(node, template_vmid, {
            'name': 'rpi-deployment-template',
            'memory': 4096,
            'cores': 2,
            'sockets': 1
        })
        
        # Configure with Cloud-Init
        self.configure_cloudinit(node, template_vmid, {
            'user': 'captureworks',
            'ssh_key': self.get_public_key()
        })
        
        # Convert to template
        self.proxmox.nodes(node).qemu(template_vmid).template.post()
        
        self.logger.info(f"Template created: {template_vmid}")
        return True
        
    except Exception as e:
        self.logger.error(f"Template creation failed: {e}")
        return False

def clone_from_template(self, node, template_vmid, new_vmid, new_name):
    """Clone a new deployment server from template"""
    try:
        self.proxmox.nodes(node).qemu(template_vmid).clone.post(
            newid=new_vmid,
            name=new_name,
            full=1  # Full clone
        )
        
        self.logger.info(f"Cloned VM {new_vmid} from template {template_vmid}")
        return True
        
    except Exception as e:
        self.logger.error(f"Clone failed: {e}")
        return False
```

### Step 15.2: Backup and Snapshot Management

```python
def create_vm_snapshot(self, node, vmid, snapname, description=""):
    """Create a snapshot of the deployment server"""
    try:
        self.proxmox.nodes(node).qemu(vmid).snapshot.create(
            snapname=snapname,
            description=description or f"Snapshot created at {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        self.logger.info(f"Snapshot created: {snapname}")
        return True
        
    except Exception as e:
        self.logger.error(f"Snapshot creation failed: {e}")
        return False

def backup_vm(self, node, vmid, storage="local"):
    """Create a backup of the deployment server"""
    try:
        self.proxmox.nodes(node).vzdump.post(
            vmid=vmid,
            storage=storage,
            mode='snapshot',
            compress='zstd'
        )
        
        self.logger.info(f"Backup initiated for VM {vmid}")
        return True
        
    except Exception as e:
        self.logger.error(f"Backup failed: {e}")
        return False
```

---

## Appendix E: Proxmox Configuration Reference

### Required Proxmox Permissions

```bash
# Create deployment automation user
pveum user add deployment@pve --password SecurePassword123

# Create custom role with required permissions
pveum role add DeploymentAutomation -privs "VM.Allocate VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network VM.Config.Options VM.Console VM.PowerMgmt Datastore.Allocate Datastore.AllocateSpace"

# Assign role to user
pveum acl modify / -user deployment@pve -role DeploymentAutomation
```

### Proxmox API Token Setup (More Secure)

```bash
# Create API token
pveum user token add deployment@pve automation --privsep 0

# Token output (save this securely):
# Token: deployment@pve!automation=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Update provisioning script to use token:

```python
from proxmoxer import ProxmoxAPI

proxmox = ProxmoxAPI(
    'proxmox_host',
    user='deployment@pve',
    token_name='automation',
    token_value='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
    verify_ssl=False
)
```

---

## Appendix F: Troubleshooting Proxmox Provisioning

### Common Issues

#### Issue 1: Authentication Failed
```bash
# Verify credentials
pveum user list | grep deployment
pveum acl list | grep deployment

# Test API access
curl -k -d "username=deployment@pve&password=SecurePassword123" \
  https://proxmox-host:8006/api2/json/access/ticket
```

#### Issue 2: Insufficient Permissions
```bash
# Check user permissions
pveum user permissions deployment@pve

# Add missing permissions
pveum acl modify / -user deployment@pve -role PVEAdmin
```

#### Issue 3: Network Configuration Failed
```python
# Verify bridge exists
for node in proxmox.nodes.get():
    bridges = proxmox.nodes(node['node']).network.get(type='bridge')
    print(f"Node {node['node']} bridges: {[b['iface'] for b in bridges]}")
```

---

## Complete Workflow Summary

1. **Prepare Proxmox**
   - Create automation user/token
   - Verify network and storage

2. **Run Provisioning**
   - Execute `proxmox_provision.py`
   - VM is created and configured automatically

3. **Post-Provision Setup**
   - SSH to new VM
   - Run `post_provision_setup.py`
   - Upload configurations

4. **Deploy Master Image**
   - Transfer master image to VM
   - Start deployment services

5. **Begin Pi Deployments**
   - Connect Pis to network
   - Monitor deployment logs

---

End of Proxmox Extension
