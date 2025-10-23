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
