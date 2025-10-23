# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains implementation plans and automation scripts for a **Raspberry Pi 5 Network Deployment System v2.0**. The system enables mass deployment of KartXPro (KXP2) and RaceXPro (RXP2) dual-camera recorder systems to blank Raspberry Pi 5 devices over the network using PXE/network boot technology with advanced hostname management.

**GitHub Repository**: https://github.com/vorsengineer/cw-rpi-deployment

**Target Environment:**
- Management Network: 192.168.101.x subnet (VLAN 101)
- Deployment Network: 192.168.151.0/24 subnet (VLAN 151)
- Deployment Server Management IP: 192.168.101.146
- Deployment Server Deployment IP: 192.168.151.1
- Device Type: Raspberry Pi 5 with dual camera setup
- Platform: Ubuntu 24.04 LTS on Proxmox VM
- Products: KXP2 (KartXPro) and RXP2 (RaceXPro)

**Current Status**:
- **Phase 1**: ✅ COMPLETE (VM provisioned at 192.168.101.146)
- **Phase 2**: ✅ COMPLETE (Server configured, Git initialized)
- **Phase 3**: ✅ COMPLETE (DHCP and TFTP configured, 34/34 tests passed)
- **Phase 4**: ✅ COMPLETE (Boot files ready, simplified design - no iPXE needed)
- **Phase 5**: ⏳ CURRENT (HTTP Server Configuration)
- See `@CURRENT_PHASE.md` for quick reference

**Documentation Structure**:
- `@CURRENT_PHASE.md` - Quick reference to current phase
- `@IMPLEMENTATION_TRACKER.md` - Overall progress tracking
- `@TRANSITION_TO_SERVER.md` - Guide for Phase 2 server transition
- `@PHASE_TRANSITION_CHECKLIST.md` - Checklist for phase transitions
- `docs/README.md` - Navigation index to all documentation
- `docs/phases/Phase_X_*.md` - Individual phase guides (15 phases)

## Architecture

### Core Components

1. **Deployment Server VM** (Dual Network Architecture)
   - Management Interface: 192.168.101.146 (VLAN 101) - Web UI and administration
   - Deployment Interface: 192.168.151.1 (VLAN 151) - Isolated deployment network
   - DHCP Server (dnsmasq) - assigns IPs (192.168.151.100-250) on deployment network
   - TFTP Server (dnsmasq built-in) - serves boot files from /tftpboot
   - HTTP Server (nginx) - distributes master images
   - Flask Web Interface (port 5000) - management dashboard
   - Flask Deployment API (port 5001) - deployment operations
   - SQLite Database - hostname pool and deployment tracking

2. **Network Boot Process**
   - Pi 5 boots from network using native UEFI network boot on VLAN 151
   - Receives IP from deployment server DHCP (192.168.151.100-250)
   - DHCP provides Option 43 ("Raspberry Pi Boot") for Pi 5 bootloader recognition
   - Downloads boot files (config.txt, kernel, dtb) via TFTP
   - Requests hostname assignment from server (product/venue based)
   - Downloads appropriate master image (KXP2 or RXP2) via HTTP
   - Image is written to local SD card with assigned hostname
   - Pi reboots from SD card for standalone operation

3. **Master Images**
   - KXP2: Pre-configured KartXPro dual camera recorder
   - RXP2: Pre-configured RaceXPro dual camera recorder
   - Hostname formats:
     - KXP2: `KXP2-[VENUE]-[NUMBER]` (e.g., KXP2-CORO-001)
     - RXP2: `RXP2-[VENUE]-[SERIAL]` (e.g., RXP2-CORO-ABC12345)
   - All dependencies installed and production-ready

## Key Python Scripts

### Deployment Server (`/opt/rpi-deployment/scripts/deployment_server.py`)
Flask application running on port 5001 (deployment network) that provides:
- `POST /api/config` - Serves deployment configuration with hostname assignment
- `POST /api/status` - Receives installation status reports from Pis
- `GET /images/<filename>` - Serves master image downloads
- `GET /health` - Health check endpoint

Features:
- Integrates with hostname management system
- Tracks deployments in SQLite database
- Product-specific image selection (KXP2/RXP2)
- Venue-based hostname assignment

### Web Management Interface (`/opt/rpi-deployment/web/app.py`)
Flask application running on port 5000 (management network) that provides:
- Real-time deployment monitoring dashboard
- Venue and kart number management
- Image upload and version control
- Deployment statistics and reporting
- WebSocket support for live updates

### Client Installer (`/opt/rpi-deployment/scripts/pi_installer.py`)
Runs on Raspberry Pi during network boot to:
- Verify SD card is present and writable
- Request hostname assignment from server (product/venue based)
- Download appropriate master image (KXP2 or RXP2)
- Write image directly to SD card
- Configure assigned hostname (KXP2-VENUE-### or RXP2-VENUE-SERIAL)
- Report detailed status back to server
- Reboot into newly installed system

### Hostname Manager (`/opt/rpi-deployment/scripts/hostname_manager.py`)
Manages hostname pool and assignments:
- Create venues with 4-letter codes
- Bulk import kart numbers for KXP2 deployments
- Automatic assignment based on product type
- Track assignment status in database

### Proxmox Provisioner (`/opt/rpi-deployment/scripts/proxmox_provision.py`)
Automates deployment server VM creation on Proxmox:
- Creates VM with specified resources
- Configures storage, network, and Cloud-Init
- Supports both password and API token authentication
- Can create templates for faster provisioning
- Includes snapshot and backup capabilities

## Directory Structure

```
/opt/rpi-deployment/          # Main deployment directory on server
├── images/                    # Master images (.img files)
│   ├── kxp2_master.img       # KartXPro master image
│   └── rxp2_master.img       # RaceXPro master image
├── scripts/                   # Python deployment scripts
│   ├── deployment_server.py  # Deployment API (port 5001)
│   ├── pi_installer.py       # Client installer
│   ├── hostname_manager.py   # Hostname management
│   └── database_setup.py     # Database initialization
├── web/                       # Web management interface
│   ├── app.py                # Flask web app (port 5000)
│   ├── templates/            # HTML templates
│   └── static/               # CSS, JS, uploads
├── database/                  # SQLite database
│   └── deployment.db         # Hostname pool and history
├── logs/                      # Deployment and status logs
├── config/                    # Configuration files
├── docs/                      # Project documentation
└── ssh_keys/                  # SSH keys for server access

/tftpboot/                     # TFTP root for network boot files
├── config.txt                 # Raspberry Pi 5 boot configuration
├── cmdline.txt                # Kernel command line parameters
├── kernel8.img                # ARM64 Linux kernel (9.5MB)
├── bcm2712-rpi-5-b.dtb       # Device tree for Raspberry Pi 5
└── README_PHASE4.txt          # Boot files documentation

/var/www/deployment/           # Nginx web root
```

## Custom Agents

The project has specialized agents for different technical domains. **Use these agents proactively** when their expertise is needed:

### Phase 3+ Agent Recommendations

**For DHCP/TFTP Configuration (Phase 3):**
- **@linux-ubuntu-specialist** - Primary agent for dnsmasq configuration, systemd services, network optimization
- **@research-documentation-specialist** - Look up dnsmasq, TFTP, and Raspberry Pi boot documentation

**For HTTP Server & Python Development (Phases 5-8):**
- **@nginx-config-specialist** - Nginx reverse proxy, dual-network setup, static file serving
- **@python-tdd-architect** - Flask applications, deployment scripts, test-driven development
- **@flask-ux-designer** - Web UI design, Flask templates, responsive interfaces, dashboard creation
- **@code-auditor** - Review Python code before deployment

**For Documentation & Phase Transitions:**
- **@doc-admin-agent** - Update IMPLEMENTATION_TRACKER.md, manage phase transitions, log issues

### Available Agents

| Agent | Use When | Key Capabilities |
|-------|----------|------------------|
| **linux-ubuntu-specialist** | System optimization, bash scripting, systemd services, kernel tuning, network configuration | Deep Linux/Ubuntu expertise, performance optimization, service management, troubleshooting |
| **nginx-config-specialist** | Web server setup, reverse proxy, SSL/TLS, virtual hosts, load balancing | Nginx configuration, security hardening, performance tuning |
| **python-tdd-architect** | Writing Python code, refactoring, creating tests, clean architecture | Test-driven development, preventing code duplication, Flask applications |
| **flask-ux-designer** | Creating web interfaces, dashboards, forms, responsive designs for Flask apps | UX/UI design, Flask templates, HTML/CSS/JS, modern web interfaces, accessibility |
| **code-auditor** | Reviewing code before deployment, validating implementations | Code validation, catching issues early, ensuring quality |
| **research-documentation-specialist** | Looking up package docs, finding technical details, clarifying requirements | Documentation research, best practices, technology validation |
| **doc-admin-agent** | Phase transitions, updating trackers, logging issues | IMPLEMENTATION_TRACKER.md updates, phase management, issue tracking |

**Usage Example:**
```
User: "Configure dnsmasq for DHCP and TFTP on the deployment network"
Assistant: "I'm going to use the @linux-ubuntu-specialist agent for this Linux system configuration task"
```

**Agent Invocation:**
- Agents are automatically available when Claude Code detects their need
- You can explicitly request an agent with: `@agent-name` in your prompt
- Agents run autonomously and return comprehensive solutions

## Common Commands

### Check Server Status
```bash
# Check all services
sudo systemctl status dnsmasq nginx rpi-deployment rpi-web

# View real-time deployment logs
tail -f /opt/rpi-deployment/logs/deployment.log

# Validate deployment server configuration
/opt/rpi-deployment/scripts/validate_deployment.sh

# Check deployment statistics
python3 /opt/rpi-deployment/scripts/check_deployments.py

# View web interface logs
sudo journalctl -u rpi-web -f
```

### Service Management
```bash
# Restart all services
sudo systemctl restart dnsmasq nginx rpi-deployment rpi-web

# Enable services on boot
sudo systemctl enable dnsmasq nginx rpi-deployment rpi-web
```

### Network Diagnostics
```bash
# Monitor DHCP requests on deployment network
sudo tcpdump -i eth1 port 67 or port 68

# Monitor TFTP traffic on deployment network
sudo tcpdump -i eth1 port 69

# Check if web interface is accessible
curl http://192.168.101.146:5000/

# Check if deployment API is accessible
curl http://192.168.151.1:5001/health

# Check both network interfaces
ip addr show eth0  # Management network (VLAN 101)
ip addr show eth1  # Deployment network (VLAN 151)
```

### Hostname Management
```bash
# Initialize database
python3 /opt/rpi-deployment/scripts/database_setup.py

# Access database directly
sqlite3 /opt/rpi-deployment/database/deployment.db

# View hostname pool
sqlite3 /opt/rpi-deployment/database/deployment.db "SELECT * FROM hostname_pool;"

# View deployment history
sqlite3 /opt/rpi-deployment/database/deployment.db "SELECT * FROM deployment_history ORDER BY started_at DESC LIMIT 10;"
```

### Master Image Management
```bash
# Create master image from reference Pi
sudo dd if=/dev/mmcblk0 of=/tmp/kxp_master_raw.img bs=4M status=progress

# Shrink image for faster deployment (requires pishrink)
sudo pishrink.sh -aZ kxp_master_raw.img kxp_dualcam_master.img

# Calculate checksum
sha256sum /opt/rpi-deployment/images/kxp_dualcam_master.img

# Set secure permissions
sudo chmod 600 /opt/rpi-deployment/images/*.img
sudo chown root:root /opt/rpi-deployment/images/*.img
```

## Development Workflow

### Deployment Server Setup Status

**Phases 1-4: COMPLETE** ✅
- VM provisioned at 192.168.101.146 (VMID 104, Ubuntu 24.04 LTS)
- Dual network configured (eth0: 192.168.101.146, eth1: 192.168.151.1)
- All base packages installed (dnsmasq, nginx, Python, Flask)
- Git repository: https://github.com/vorsengineer/cw-rpi-deployment
- Custom agents configured for specialized tasks
- **Phase 3**: DHCP/TFTP configured with dnsmasq (34/34 tests passed)
- **Phase 4**: Boot files ready (config.txt, kernel8.img, dtb) - no iPXE needed

**Current Phase: Phase 5** - HTTP Server Configuration
- See `docs/phases/Phase_5_HTTP_Server.md` for current work
- Use @nginx-config-specialist for dual-network nginx configuration

**Remaining Phases:**
- Phase 6: Hostname Management System
- Phase 7: Web Management Interface
- Phase 8-15: Python scripts, services, testing, deployment

### Updating Master Image

1. Create new image from updated reference Pi
2. Transfer to server and shrink with pishrink
3. Test with single Pi
4. Backup old image and replace:
   ```bash
   mv /opt/rpi-deployment/images/kxp_dualcam_master.img \
      /opt/rpi-deployment/images/kxp_dualcam_master_v1_backup.img
   mv /opt/rpi-deployment/images/kxp_dualcam_master_v2.img \
      /opt/rpi-deployment/images/kxp_dualcam_master.img
   ```
5. Restart deployment server: `sudo systemctl restart rpi-deployment`

### Mass Deployment

1. **Configure Venue and Hostname Pool**:
   ```bash
   # Access web interface
   http://192.168.101.146

   # Or via command line
   python3 -c "
   from hostname_manager import HostnameManager
   mgr = HostnameManager()
   mgr.create_venue('CORO', 'Corona Karting', 'California', 'contact@corona.com')
   mgr.bulk_import_kart_numbers('CORO', ['001', '002', '003', '004', '005'])
   "
   ```

2. **Run Pre-Deployment Validation**:
   ```bash
   /opt/rpi-deployment/scripts/validate_deployment.sh
   ```

3. **Start Monitoring**:
   - Web Dashboard: http://192.168.101.146
   - Command line: `tmux new-session -d -s deployment "tail -f /opt/rpi-deployment/logs/deployment.log"`

4. **Connect Pis to VLAN 151** and power on in batches (5-10 at a time)

5. **Monitor Progress**:
   ```bash
   # Real-time logs
   tail -f /opt/rpi-deployment/logs/deployment_$(date +%Y%m%d).log

   # Check deployment status
   python3 /opt/rpi-deployment/scripts/check_deployments.py

   # View assigned hostnames
   sqlite3 /opt/rpi-deployment/database/deployment.db "SELECT hostname, mac_address, assigned_date FROM hostname_pool WHERE status='assigned';"
   ```

## Important Technical Details

### Network Boot Configuration
- Raspberry Pi 5 uses native UEFI ARM64 boot (option:client-arch,11)
- **CRITICAL**: DHCP Option 43 must contain "Raspberry Pi Boot" string for Pi 5 bootloader
- Boot sequence: DHCP (with Option 43) → TFTP (config.txt, kernel8.img, dtb) → Kernel → HTTP Installer
- Boot files served via TFTP from `/tftpboot/` (using dnsmasq built-in TFTP)
- No iPXE required - Pi 5 has network boot support in EEPROM firmware
- Installer script URL passed via kernel command line in cmdline.txt

### Image Writing Process
- Installer writes directly to `/dev/mmcblk0` (SD card)
- Uses streaming download to minimize RAM usage
- Progress logged every 100MB
- Partial checksum verification (first 100MB) for speed
- Full sync with `fsync()` before verification

### Hostname Customization
- KXP2 devices: `KXP2-[VENUE]-[NUMBER]` (e.g., KXP2-CORO-001)
- RXP2 devices: `RXP2-[VENUE]-[SERIAL]` (e.g., RXP2-CORO-ABC12345)
- Hostname assignment managed by server based on product type and venue
- Customization done via `firstrun.sh` script on boot partition
- Serial number read from `/proc/cpuinfo`

### Status Reporting
- Pis report status: `starting`, `downloading`, `verifying`, `customizing`, `success`, `failed`
- All status reports logged with timestamp, IP, hostname, serial number
- Status tracked in SQLite database for history
- Daily log files: `/opt/rpi-deployment/logs/deployment_YYYYMMDD.log`

### Dual Network Architecture
- **Management Network (VLAN 101)**: Web interface, SSH access, monitoring
- **Deployment Network (VLAN 151)**: Isolated network for Pi imaging
- No routing between networks for security
- UniFi DHCP must be disabled on VLAN 151 to avoid conflicts

## Proxmox Integration

### Authentication Methods
1. **Password**: Use `--user root@pam --password PASSWORD`
2. **API Token** (more secure): Create token with `pveum user token add deployment@pve automation`

### Required Proxmox Permissions
Create custom role with: `VM.Allocate`, `VM.Config.*`, `VM.Console`, `VM.PowerMgmt`, `Datastore.Allocate*`

### VM Template Workflow
1. Create base VM with all configurations
2. Convert to template: `proxmox.nodes(node).qemu(vmid).template.post()`
3. Clone from template for faster provisioning

## Troubleshooting

### Pi Not Receiving DHCP
- Check dnsmasq logs: `tail -f /var/log/dnsmasq.log`
- Verify dnsmasq is listening on eth1: `sudo netstat -tulpn | grep dnsmasq`
- Ensure Pi is connected to VLAN 151
- **CRITICAL**: Verify UniFi DHCP is disabled on VLAN 151
- Check for DHCP conflicts: `sudo tcpdump -i eth1 -n port 67 or port 68`

### TFTP Boot Files Not Loading
- Check dnsmasq logs: `tail -f /var/log/dnsmasq.log | grep TFTP`
- Test manually: `tftp 192.168.151.1` then `get config.txt` and `get kernel8.img`
- Verify permissions: `ls -la /tftpboot/` (should be 644 for files, root:nogroup ownership)
- Ensure TFTP is bound to deployment network (192.168.151.1)
- Verify tftp-secure is disabled if having permission issues

### Image Download Fails
- Check nginx logs: `tail -f /var/log/nginx/deployment-error.log`
- Test download: `wget http://192.168.151.1/images/kxp2_master.img`
- Check disk space: `df -h /opt/rpi-deployment/images/`
- Verify nginx is serving on deployment network

### Hostname Assignment Issues
- Check database: `sqlite3 /opt/rpi-deployment/database/deployment.db`
- Verify venue exists and has available hostnames
- Check hostname pool: `SELECT * FROM hostname_pool WHERE venue_code='XXXX' AND status='available';`
- View assignment logs in deployment history table

### Installation Verification Fails
- Verify image integrity: `sha256sum /opt/rpi-deployment/images/kxp_dualcam_master.img`
- Check SD card health: `sudo badblocks -v /dev/mmcblk0`

## Security Considerations

- Deploy on isolated VLAN when possible
- Master images stored with 600 permissions, root ownership
- All deployments logged with timestamps and serial numbers
- Implement checksum verification for image integrity
- Use API tokens instead of passwords for Proxmox automation
- Monitor for unauthorized DHCP requests

## File Naming Conventions

- Master images: `kxp_dualcam_master.img` (current), `kxp_dualcam_master_v1_backup.img` (previous)
- Log files: `deployment.log` (main), `deployment_YYYYMMDD.log` (daily status)
- Config files: `deployment_server_config.json` (Proxmox VM config)
- Scripts: Use `.py` extension, make executable with `chmod +x`

## Code Implementation Notes

When working with the Python scripts:

1. **Error Handling**: All scripts use try/except with detailed logging. Always report status to server before exiting on failure.

2. **Logging**: Use Python logging module with both file and console handlers. Log level: INFO for normal operations, ERROR for failures.

3. **Status Reporting**: Client installer reports status at each phase: starting, downloading, verifying, customizing, success/failed.

4. **Checksum Calculation**: Use SHA256 with 8192-byte chunks. For speed, client does partial verification (first 100MB only).

5. **Flask API**: Server runs on 0.0.0.0:5000, proxied through nginx. Use JSON for all API responses.

6. **Systemd Service**: Services run as 'captureworks' user, auto-restart on failure with 10-second delay.

## Key v2.0 Features

### Dual Network Architecture
- **Management**: 192.168.101.146 (VLAN 101) - Web UI, SSH, monitoring
- **Deployment**: 192.168.151.1 (VLAN 151) - Isolated Pi imaging network
- Complete network isolation for security
- UniFi DHCP must be disabled on VLAN 151

### Enhanced Hostname Management
- Product-specific naming (KXP2 vs RXP2)
- Venue-based organization with 4-letter codes
- Pre-loadable kart number pools
- Automatic assignment and tracking
- SQLite database for persistence

### Web Management Interface
- Real-time deployment dashboard
- Venue and kart management
- Image upload capability
- Deployment statistics
- WebSocket for live updates

### Improved Security
- Network isolation between VLANs
- No internet access on deployment network
- User-based service execution (captureworks)
- Comprehensive logging and tracking

### Critical Configuration Requirements
1. **UniFi VLAN 151**: DHCP must be DISABLED
2. **Dual NICs**: VM must have interfaces on both VLANs
3. **Database**: Must be initialized before first deployment
4. **Hostname Pool**: Must be configured before deploying KXP2 devices
## Documentation Structure and Maintenance

### Key Documentation Files
- **@IMPLEMENTATION_TRACKER.md** - Overall progress tracking across all phases
- **@CURRENT_PHASE.md** - Quick reference for the current active phase (UPDATE THIS!)
- **docs/README.md** - Navigation index to all documentation
- **docs/RPI_NETWORK_DEPLOYMENT_IMPLEMENTATION_PLAN.md** - Full implementation plan (all phases)
- **docs/phases/** - Individual phase documentation files (small, focused files)

### CRITICAL: Phase Transition Workflow

**📋 Use the checklist**: See `@PHASE_TRANSITION_CHECKLIST.md` for complete step-by-step guide

**When completing a phase and moving to the next phase, you MUST:**

1. **Update IMPLEMENTATION_TRACKER.md**:
   - Mark completed phase with ✅ COMPLETE and date
   - Update phase status table
   - Add completion notes to Daily Notes section
   - Update Issues & Resolutions Log if needed

2. **Update CURRENT_PHASE.md** (IMPORTANT!):
   - Change the phase number and title at the top
   - Update the "Status" line
   - Update the VM IP if it changed
   - Update "Full Phase Documentation" link to new phase
   - Update all task checkboxes for the new phase
   - Update "Previous Phase" and "Next Phase" links
   - Update "Last Updated" date

3. **Update docs/README.md**:
   - Mark completed phase with ✅
   - Mark new current phase with ⏳
   - Update "Current Status" section

### Example Phase Transition:
```bash
# When completing Phase 2 and starting Phase 3:
# 1. Edit IMPLEMENTATION_TRACKER.md - mark Phase 2 complete
# 2. Edit CURRENT_PHASE.md - change from Phase 2 to Phase 3
# 3. Edit docs/README.md - update status icons
```

### Quick Access Commands
- **Current Phase**: `cat CURRENT_PHASE.md` or `@CURRENT_PHASE.md`
- **Implementation Tracker**: `@IMPLEMENTATION_TRACKER.md`
- **Phase Documentation**: Read from `docs/phases/Phase_X_*.md`

### SSH Access
- SSH to cw-rpi-deployment01: `ssh -i ssh_keys/deployment_key captureworks@192.168.101.146`
- Password (if needed): Jankycorpltd01

### Other Reminders
- Make sure to keep the @IMPLEMENTATION_TRACKER.md up to date between each phase step!
- Always update @CURRENT_PHASE.md when transitioning phases
- Use context7 MCP for checking latest documentation for packages/libraries
- @PHASE_TRANSITION_CHECKLIST.md