# VM Provisioning for KXP/RXP Deployment Server

This directory contains the consolidated, production-ready scripts for provisioning the deployment server VM on Proxmox.

## Overview

The provisioning process creates a Ubuntu 24.04 LTS VM using Cloud-Init for automated configuration. This approach is fully automated and takes approximately 5-10 minutes from start to finish.

**Current Status**: ✅ Phase 1 COMPLETE - VM successfully provisioned and running
- **VM ID**: 104
- **VM Name**: cw-rpi-deployment01
- **Management IP**: 192.168.101.146 (DHCP from UniFi)
- **Deployment IP**: 192.168.151.1 (Static)
- **SSH Access**: Working with both key and password authentication

## Key Features

- **Automated provisioning** using Cloud-Init (no manual installation)
- **Dual network configuration** (Management VLAN 101 & Deployment VLAN 151)
- **Proper disk sizing** (100GB automatically configured)
- **VGA display** (avoids serial console issues)
- **Pre-installed packages** for deployment server functionality

## Scripts

### 1. `provision_deployment_vm.py`
Main provisioning script that:
- Downloads Ubuntu cloud image to Proxmox
- Creates VM with proper specifications
- Imports and resizes disk to 100GB
- Configures Cloud-Init with networking and credentials
- Starts the VM for automatic configuration

### 2. `validate_vm.py`
Validation script that:
- Checks VM status via Proxmox API
- Verifies network connectivity
- Tests SSH access
- Validates Cloud-Init completion
- Checks critical services

### 3. `cleanup_vm.py`
Cleanup script that:
- Safely stops running VMs
- Removes VM configuration
- Optionally purges disk storage
- Cleans up resources

## Configuration

### Default Settings (config.json)
```json
{
  "vm": {
    "vmid": 104,
    "name": "cw-rpi-deployment01",
    "cores": 4,
    "memory": 8192,
    "disk_size": "100G"
  },
  "network": {
    "management": {
      "dhcp": true,  // DHCP from UniFi
      "vlan": 101
    },
    "deployment": {
      "ip": "192.168.151.1/24",
      "vlan": 151
    },
    "dns": ["8.8.8.8"]  // Single DNS server
  },
  "cloud_init": {
    "username": "captureworks",
    "password": "Jankycorpltd01",
    "hostname": "cw-rpi-deployment01"
  }
}
```

## Usage

### Complete VM Provisioning

```bash
# Using default configuration
python vm_provisioning\provision_deployment_vm.py

# Using custom configuration file
python vm_provisioning\provision_deployment_vm.py --config custom_config.json

# Specify custom VM ID and name
python vm_provisioning\provision_deployment_vm.py --vmid 105 --name cw-rpi-deployment02
```

### Validate VM

```bash
# Validate default VM (104)
python vm_provisioning\validate_vm.py

# Validate specific VM
python vm_provisioning\validate_vm.py --vmid 105 --ip 192.168.101.21
```

### Cleanup/Delete VM

```bash
# Delete VM (preserve disks)
python vm_provisioning\cleanup_vm.py 104

# Delete VM and purge disks
python vm_provisioning\cleanup_vm.py 104 --purge-disks

# Skip confirmation prompt
python vm_provisioning\cleanup_vm.py 104 --force
```

## Important Lessons Learned

### 1. Cloud Image Disk Size
**Problem**: Cloud images import at ~3.5GB size
**Solution**: Always resize disk to target size (100GB) after import

### 2. Display Configuration
**Problem**: Setting VGA display can cause issues
**Solution**: Don't set display - use Proxmox default

### 3. Network Configuration
**Problem**: Static IP on VLAN 101 conflicts with UniFi DHCP
**Solution**: Use DHCP for management network (VLAN 101)

### 4. DNS Configuration
**Problem**: Comma-separated DNS servers cause Cloud-Init errors
**Solution**: Use single DNS server (8.8.8.8)

### 5. SSH Authentication
**Problem**: Default cloud images disable password authentication
**Solution**: Enable via Cloud-Init custom user-data

### 6. Cloud-Init State Persistence
**Problem**: Cloud-Init won't run on recreated VMs (marks completion in disk)
**Solution**: Always use `--purge-disks` when deleting VMs

### 7. SSH Connection Rate Limiting
**Problem**: Multiple rapid SSH connections get rate-limited by Proxmox
**Solution**: Implement connection pooling/reuse in scripts

### 8. QEMU Guest Agent
**Problem**: Not installed by default
**Solution**: Auto-install via Cloud-Init runcmd

## Workflow

### Phase 1: Initial Provisioning

1. **Provision VM**
   ```bash
   python vm_provisioning\provision_deployment_vm.py
   ```
   - Downloads Ubuntu cloud image
   - Creates and configures VM
   - Starts Cloud-Init process

2. **Wait for Cloud-Init** (3-5 minutes)
   - VM automatically configures networking
   - Installs packages
   - Sets up SSH access

3. **Validate VM**
   ```bash
   python vm_provisioning\validate_vm.py
   ```
   - Confirms VM is accessible
   - Verifies all configurations

### Phase 2: Post-Provisioning (Next Steps)

Once validated, SSH to the VM to continue setup:

```bash
# Using SSH key (recommended)
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146

# Using password
ssh captureworks@192.168.101.146
# Password: Jankycorpltd01

# Via Proxmox jump host (if no direct access)
ssh root@192.168.11.194
ssh captureworks@192.168.101.146
```

Then proceed with:
- Installing deployment server software
- Configuring DHCP/TFTP services
- Setting up web interface
- Preparing for RPi deployments

## Troubleshooting

### SSH Not Accessible

1. **Check Cloud-Init status** via Proxmox console:
   ```bash
   cloud-init status
   ```

2. **Verify network configuration**:
   ```bash
   ip addr show
   systemctl status systemd-networkd
   ```

3. **Check SSH service**:
   ```bash
   systemctl status ssh
   sudo systemctl restart ssh
   ```

### Cloud-Init Errors

1. **Access VM console** via Proxmox web UI
2. **Login** with captureworks/Jankycorpltd01
3. **Check logs**:
   ```bash
   sudo cat /var/log/cloud-init.log
   sudo cat /var/log/cloud-init-output.log
   ```

### VM Won't Start

1. **Check Proxmox resources**:
   - Sufficient disk space
   - Available memory
   - No conflicting VMID

2. **Review VM configuration**:
   - Correct storage pool
   - Valid network bridges
   - Proper VLAN tags

## Network Architecture

```
┌─────────────────┐     ┌──────────────────┐
│ Management      │     │ Deployment       │
│ VLAN 101        │     │ VLAN 151         │
│ 192.168.101.0/24│     │ 192.168.151.0/24 │
└────────┬────────┘     └──────┬───────────┘
         │                     │
         │ eth0                │ eth1
    ┌────┴──────────────────────┴────┐
    │    Deployment Server VM        │
    │    192.168.101.20 (mgmt)       │
    │    192.168.151.1  (deploy)     │
    │    User: captureworks          │
    └─────────────────────────────────┘
```

## Files Generated

- `vm_104_config.json` - VM configuration details
- `vm_provisioning_YYYYMMDD_HHMMSS.log` - Provisioning logs
- `validation_results_YYYYMMDD_HHMMSS.json` - Validation results

## Requirements

### Python Packages
- `proxmoxer` - Proxmox API client
- `paramiko` - SSH automation
- `requests` - HTTP library

Install with:
```bash
pip install proxmoxer paramiko requests
```

### Proxmox Requirements
- Proxmox VE 8.x
- Sufficient resources (8GB RAM, 100GB disk, 4 cores)
- Network bridges configured for VLANs 101 and 151
- ISO storage with write permissions

## Security Notes

- Credentials are stored in config files - protect appropriately
- Consider using environment variables for passwords in production
- VM has sudo access - secure after initial setup
- Firewall rules should be configured after provisioning

## Support

For issues or questions about the provisioning process, check:
1. The provisioning logs
2. Proxmox system logs
3. Cloud-Init logs on the VM
4. This documentation

## Version History

- **v2.1** (2025-10-23): Production version with all fixes applied
  - DHCP on management network (VLAN 101)
  - Fixed DNS configuration (single server)
  - SSH key and password authentication
  - QEMU guest agent auto-installation
  - Connection pooling for SSH
- **v2.0** (2025-10-23): Complete rewrite with Cloud-Init automation
- **v1.0**: Manual installation approach (deprecated)

---

*Developed as part of the KXP/RXP RPi5 Network Deployment System*