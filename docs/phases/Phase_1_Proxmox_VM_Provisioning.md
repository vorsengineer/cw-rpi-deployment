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

