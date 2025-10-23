#!/usr/bin/env python3
"""
Complete VM Provisioning for KXP/RXP Deployment Server
This script incorporates all lessons learned and creates a fully functional VM

Author: Claude Code
Version: 2.0
Date: 2025-10-23
"""

import sys
import os
import time
import json
import argparse
import urllib.parse
from datetime import datetime
from proxmoxer import ProxmoxAPI
import paramiko
import subprocess

# Default Configuration
DEFAULT_CONFIG = {
    'proxmox': {
        'host': '192.168.11.194',
        'user': 'root@pam',
        'password': 'Ati4870_x5',
        'node': 'cw-dc01',
        'verify_ssl': False
    },
    'vm': {
        'vmid': 104,
        'name': 'cw-rpi-deployment01',
        'cores': 4,
        'memory': 8192,  # MB
        'disk_size': '100G',
        'storage': 'vm_data',
        'description': 'KXP/RXP Deployment Server - Ubuntu 24.04 LTS (Cloud-Init)'
    },
    'cloud_init': {
        'username': 'captureworks',
        'password': 'Jankycorpltd01',
        'hostname': 'cw-rpi-deployment01',
        'domain': 'captureworks.eu',
        'upgrade': True,
        'packages': ['qemu-guest-agent', 'openssh-server', 'python3', 'git', 'curl', 'wget']
    },
    'network': {
        'management': {
            'interface': 'eth0',
            'vlan': 101,
            'dhcp': True  # DHCP from UniFi VLAN 101
        },
        'deployment': {
            'interface': 'eth1',
            'vlan': 151,
            'ip': '192.168.151.1/24',
            'gateway': None
        },
        'dns': ['8.8.8.8', '8.8.4.4']
    },
    'cloud_image': {
        'url': 'https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img',
        'filename': 'ubuntu-24.04-server-cloudimg-amd64.img',
        'storage_path': '/var/lib/vz/template/iso/'
    }
}


class VMProvisioner:
    def __init__(self, config=None):
        """Initialize provisioner with configuration"""
        self.config = config or DEFAULT_CONFIG
        self.proxmox = None
        self.ssh = None
        self.ssh_connected = False
        self.log_file = f"vm_provisioning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    def log(self, message, level="INFO"):
        """Log messages to console and file"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        with open(self.log_file, 'a') as f:
            f.write(log_message + '\n')

    def connect_proxmox(self):
        """Connect to Proxmox API"""
        self.log("Connecting to Proxmox API...")
        try:
            self.proxmox = ProxmoxAPI(
                self.config['proxmox']['host'],
                user=self.config['proxmox']['user'],
                password=self.config['proxmox']['password'],
                verify_ssl=self.config['proxmox']['verify_ssl'],
                timeout=30
            )

            # Test connection
            version = self.proxmox.version.get()
            self.log(f"Connected to Proxmox VE {version['version']}")
            return True
        except Exception as e:
            self.log(f"Failed to connect to Proxmox: {e}", "ERROR")
            return False

    def connect_ssh(self):
        """Connect to Proxmox via SSH with retry logic"""
        # If already connected, test the connection
        if self.ssh_connected and self.ssh:
            try:
                # Test if connection is still alive
                stdin, stdout, stderr = self.ssh.exec_command('echo "test"', timeout=5)
                stdout.read()
                return True
            except:
                self.log("SSH connection lost, reconnecting...", "WARNING")
                self.ssh_connected = False
                try:
                    self.ssh.close()
                except:
                    pass

        # Try to connect with retries
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            self.log(f"SSH connection attempt {attempt}/{max_attempts}...")
            try:
                self.ssh = paramiko.SSHClient()
                self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh.connect(
                    hostname=self.config['proxmox']['host'],
                    username=self.config['proxmox']['user'].split('@')[0],
                    password=self.config['proxmox']['password'],
                    timeout=10,  # Shorter timeout for retries
                    look_for_keys=False,
                    allow_agent=False
                )
                self.ssh_connected = True
                self.log("SSH connection established")
                return True
            except Exception as e:
                self.log(f"Attempt {attempt} failed: {e}", "WARNING")
                if attempt < max_attempts:
                    self.log(f"Waiting 3 seconds before retry...", "INFO")
                    time.sleep(3)  # Wait before retry to avoid rate limiting
                else:
                    self.log(f"Failed to connect via SSH after {max_attempts} attempts", "ERROR")

        return False

    def download_cloud_image(self):
        """Download Ubuntu cloud image to Proxmox storage"""
        self.log("=== STEP 1: Cloud Image Download ===")

        if not self.connect_ssh():
            self.log("SSH connection failed, assuming cloud image exists", "WARNING")
            self.log("Continuing with provisioning...", "INFO")
            return True  # Continue anyway since image likely exists

        try:
            image_path = os.path.join(
                self.config['cloud_image']['storage_path'],
                self.config['cloud_image']['filename']
            )

            # Check if image already exists
            stdin, stdout, stderr = self.ssh.exec_command(f"ls -la {image_path} 2>/dev/null")
            if self.config['cloud_image']['filename'] in stdout.read().decode():
                self.log("Cloud image already exists, skipping download")
                return True

            # Download the image
            self.log(f"Downloading Ubuntu 24.04 cloud image...")
            self.log(f"URL: {self.config['cloud_image']['url']}")

            download_cmd = f"""
            cd {self.config['cloud_image']['storage_path']} && \
            wget -O {self.config['cloud_image']['filename']} {self.config['cloud_image']['url']}
            """

            stdin, stdout, stderr = self.ssh.exec_command(download_cmd, timeout=600)

            # Wait for download to complete
            for line in stdout:
                if '100%' in line or 'saved' in line.lower():
                    self.log(line.strip())

            # Verify download
            stdin, stdout, stderr = self.ssh.exec_command(f"ls -lh {image_path}")
            result = stdout.read().decode()

            if self.config['cloud_image']['filename'] in result:
                self.log(f"Cloud image downloaded successfully")
                return True
            else:
                self.log("Cloud image download failed", "ERROR")
                return False

        except Exception as e:
            self.log(f"Error downloading cloud image: {e}", "ERROR")
            return False
        finally:
            # Keep SSH connection alive for reuse
            pass

    def create_vm(self):
        """Create the VM with proper configuration"""
        self.log("=== STEP 2: VM Creation ===")

        node = self.config['proxmox']['node']
        vmid = self.config['vm']['vmid']

        try:
            # Check if VM already exists
            try:
                existing = self.proxmox.nodes(node).qemu(vmid).status.current.get()
                self.log(f"VM {vmid} already exists, deleting...")

                # Stop if running
                if existing['status'] == 'running':
                    self.proxmox.nodes(node).qemu(vmid).status.stop.post()
                    time.sleep(3)

                # Delete VM
                self.proxmox.nodes(node).qemu(vmid).delete()
                time.sleep(2)
            except:
                pass  # VM doesn't exist, continue

            # Create new VM
            self.log(f"Creating VM {vmid} ({self.config['vm']['name']})...")

            vm_params = {
                'vmid': vmid,
                'name': self.config['vm']['name'],
                'memory': self.config['vm']['memory'],
                'cores': self.config['vm']['cores'],
                'sockets': 1,
                'cpu': 'host',
                'ostype': 'l26',
                'scsihw': 'virtio-scsi-single',
                'boot': 'order=scsi0',
                'agent': 'enabled=1,fstrim_cloned_disks=1',
                'onboot': 1,
                'description': self.config['vm']['description'],
                # IMPORTANT: Do NOT set serial console - use default display
                'tablet': 1
            }

            self.proxmox.nodes(node).qemu.create(**vm_params)
            self.log(f"VM {vmid} created successfully")
            time.sleep(2)

            # Configure network interfaces
            self.log("Configuring network interfaces...")

            # Management interface (VLAN 101)
            self.proxmox.nodes(node).qemu(vmid).config.set(
                net0=f"virtio,bridge=vmbr0,firewall=1,tag={self.config['network']['management']['vlan']}"
            )
            self.log(f"  eth0: VLAN {self.config['network']['management']['vlan']} (Management)")

            # Deployment interface (VLAN 151)
            self.proxmox.nodes(node).qemu(vmid).config.set(
                net1=f"virtio,bridge=vmbr0,firewall=1,tag={self.config['network']['deployment']['vlan']}"
            )
            self.log(f"  eth1: VLAN {self.config['network']['deployment']['vlan']} (Deployment)")

            return True

        except Exception as e:
            self.log(f"Error creating VM: {e}", "ERROR")
            return False

    def import_and_configure_disk(self):
        """Import cloud image and configure disk properly"""
        self.log("=== STEP 3: Disk Configuration ===")

        node = self.config['proxmox']['node']
        vmid = self.config['vm']['vmid']
        storage = self.config['vm']['storage']

        # SSH is required for disk import
        if not self.connect_ssh():
            self.log("SSH connection required for disk import", "ERROR")
            self.log("Please check network connectivity to Proxmox host", "ERROR")
            return False

        try:
            # Import cloud image as disk
            self.log("Importing cloud image as VM disk...")

            image_path = os.path.join(
                self.config['cloud_image']['storage_path'],
                self.config['cloud_image']['filename']
            )

            import_cmd = f"qm importdisk {vmid} {image_path} {storage}"
            stdin, stdout, stderr = self.ssh.exec_command(import_cmd, timeout=120)

            output = stdout.read().decode()
            error = stderr.read().decode()

            if 'successfully imported' in output.lower() or 'imported' in output.lower():
                self.log("Cloud image imported successfully")
            else:
                self.log(f"Import status unclear: {output}", "WARNING")
                if error:
                    self.log(f"Error output: {error}", "WARNING")

            # Attach the imported disk as scsi0
            self.log("Attaching imported disk...")
            disk_name = f"vm-{vmid}-disk-0"
            self.proxmox.nodes(node).qemu(vmid).config.set(
                scsi0=f"{storage}:{disk_name}"
            )

            # CRITICAL: Resize disk to 100GB (cloud images are typically ~3GB)
            self.log(f"Resizing disk to {self.config['vm']['disk_size']}...")
            self.proxmox.nodes(node).qemu(vmid).resize.put(
                disk='scsi0',
                size=self.config['vm']['disk_size']
            )
            self.log(f"Disk resized to {self.config['vm']['disk_size']}")

            return True

        except Exception as e:
            self.log(f"Error configuring disk: {e}", "ERROR")
            return False
        finally:
            # Keep SSH connection alive for reuse
            pass

    def configure_cloud_init(self):
        """Configure Cloud-Init settings"""
        self.log("=== STEP 4: Cloud-Init Configuration ===")

        node = self.config['proxmox']['node']
        vmid = self.config['vm']['vmid']

        try:
            # Add Cloud-Init drive
            self.log("Adding Cloud-Init drive...")
            self.proxmox.nodes(node).qemu(vmid).config.set(
                ide2=f"{self.config['vm']['storage']}:cloudinit"
            )

            # Configure Cloud-Init settings
            self.log("Configuring Cloud-Init parameters...")

            # Upload Cloud-Init user data for SSH password authentication
            if self.connect_ssh():
                self.log("Uploading Cloud-Init user data...")
                # Create snippets directory if it doesn't exist
                stdin, stdout, stderr = self.ssh.exec_command("mkdir -p /var/lib/vz/snippets")
                stdout.read()

                # Create user-data file with SSH password authentication enabled
                user_data = """#cloud-config
ssh_pwauth: true
users:
  - name: captureworks
    groups: sudo
    shell: /bin/bash
    lock_passwd: false
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDQlmXfUnS6BIA5Ww5bjmNHR2usc2taN/mtQ/521QZOPwJF/vJfXv0tmW6lMri61nSKRErIntURquEUs6twTPjydJe0N9hN7E9jk0O4hbsSviVso/Cgng2JRIuxIbjrUeF51aKyCEWmTLyxXo1BPv3fuOBPmHIRRmg1paQGd3KidvQf1Kh1QtxRJyoDo4aV73PIWTZVr5a1ohX56X/ELznczIYz6yGiTvGOGZPLxt7bsNDBo/vspuSU23v+HC3yB4i4nLdwfNYuqLQ7JYD4AKnxw5yMgB7FuoGKWEF0JiZJOCWyH5BbdWUA1Y7YMUkI7oZe78+zqpkBUvE3cXobnLnzpjByaKyPW2w8uMA1VJpRJHO2LwU2alQeoDxqAjGyfqhdkQ7U7DFHn+15RMr05Y+MbHU0rrSHwXkZC0mdGz0q2chdwr/I/bYJmNAOL0efAwQ0/meA3746HFBMYvSY929lNiOpVnwURhcuMcrVggeN/IJFiaDtXQcICBxr7GEAH1CBPR17zGiWmMUzEuTx7nobrhtLSqjvJKXY+/XQuw4v2UBkXlQdoN7KNJ+IFDXRu1smx2hKvq9svejEJVX2cuPMWOxNz4AYd9dhfwVY0FzxTDjGYgw16re2ty5gsGpilURGhzBjR8PSI/1ZcOWQCvxNe1fVKoaWKa2yhgkS0S7VcQ== kxp-deployment@proxmox

runcmd:
  - sed -i 's/^PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
  - sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
  - systemctl restart ssh
  - apt-get update
  - apt-get install -y qemu-guest-agent
  - systemctl start qemu-guest-agent

hostname: cw-rpi-deployment01
manage_etc_hosts: true
"""

                # Write user-data to Proxmox
                user_data_escaped = user_data.replace("'", "'\\''")
                stdin, stdout, stderr = self.ssh.exec_command(f"echo '{user_data_escaped}' > /var/lib/vz/snippets/user-data-{vmid}.yaml")
                stdout.read()
                time.sleep(1)

            # Read SSH public key from file
            ssh_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ssh_keys', 'deployment_key.pub')
            ssh_public_key = ""
            if os.path.exists(ssh_key_path):
                with open(ssh_key_path, 'r') as f:
                    ssh_public_key = f.read().strip()
                self.log("  Found SSH public key")

            # User, password, and SSH key
            self.proxmox.nodes(node).qemu(vmid).config.set(
                ciuser=self.config['cloud_init']['username'],
                cipassword=self.config['cloud_init']['password'],
                sshkeys=urllib.parse.quote(ssh_public_key, safe='') if ssh_public_key else "",
                cicustom=f"user=local:snippets/user-data-{vmid}.yaml"
            )
            self.log(f"  User: {self.config['cloud_init']['username']}")
            self.log("  SSH password authentication: Enabled")
            if ssh_public_key:
                self.log("  SSH key authentication: Enabled")

            # Network configuration
            # Management network (eth0) - DHCP from UniFi VLAN 101
            ipconfig0 = "ip=dhcp"
            self.proxmox.nodes(node).qemu(vmid).config.set(ipconfig0=ipconfig0)
            self.log(f"  eth0: DHCP (VLAN {self.config['network']['management']['vlan']})")

            # Deployment network (eth1) - no gateway
            ipconfig1 = f"ip={self.config['network']['deployment']['ip']}"
            self.proxmox.nodes(node).qemu(vmid).config.set(ipconfig1=ipconfig1)
            self.log(f"  eth1: {self.config['network']['deployment']['ip']}")

            # DNS servers - use only first one if multiple provided
            if self.config['network']['dns']:
                dns_server = self.config['network']['dns'][0]
                self.proxmox.nodes(node).qemu(vmid).config.set(
                    nameserver=dns_server
                )
                self.log(f"  DNS: {dns_server}")

            # Hostname is set via ciuser, not as separate parameter
            # The hostname will be configured via Cloud-Init user-data
            self.log(f"  Hostname will be: {self.config['cloud_init']['hostname']}")

            # Enable package upgrades
            if self.config['cloud_init']['upgrade']:
                self.proxmox.nodes(node).qemu(vmid).config.set(ciupgrade=1)
                self.log("  Package upgrades: Enabled")

            # Regenerate Cloud-Init ISO
            if self.connect_ssh():  # Will reuse existing connection
                self.log("Regenerating Cloud-Init ISO...")
                stdin, stdout, stderr = self.ssh.exec_command(f"qm cloudinit update {vmid}")
                time.sleep(2)
                # Keep connection alive - don't close

            return True

        except Exception as e:
            self.log(f"Error configuring Cloud-Init: {e}", "ERROR")
            return False

    def start_vm(self):
        """Start the VM"""
        self.log("=== STEP 5: Starting VM ===")

        node = self.config['proxmox']['node']
        vmid = self.config['vm']['vmid']

        try:
            self.proxmox.nodes(node).qemu(vmid).status.start.post()
            self.log(f"VM {vmid} started successfully")

            # Get VM status
            time.sleep(3)
            status = self.proxmox.nodes(node).qemu(vmid).status.current.get()
            self.log(f"VM Status: {status['status']}")

            return True

        except Exception as e:
            self.log(f"Error starting VM: {e}", "ERROR")
            return False

    def cleanup(self):
        """Clean up resources"""
        if self.ssh_connected and self.ssh:
            try:
                self.log("Closing SSH connection...")
                self.ssh.close()
                self.ssh_connected = False
            except:
                pass

    def save_configuration(self):
        """Save VM configuration for future reference"""
        config_file = f"vm_{self.config['vm']['vmid']}_config.json"

        vm_info = {
            'created': datetime.now().isoformat(),
            'vmid': self.config['vm']['vmid'],
            'name': self.config['vm']['name'],
            'node': self.config['proxmox']['node'],
            'proxmox_host': self.config['proxmox']['host'],
            'management_network': f"DHCP on VLAN {self.config['network']['management']['vlan']}",
            'deployment_ip': self.config['network']['deployment']['ip'].split('/')[0],
            'username': self.config['cloud_init']['username'],
            'password': self.config['cloud_init']['password'],
            'hostname': self.config['cloud_init']['hostname'],
            'disk_size': self.config['vm']['disk_size'],
            'memory': self.config['vm']['memory'],
            'cores': self.config['vm']['cores']
        }

        with open(config_file, 'w') as f:
            json.dump(vm_info, f, indent=2)

        self.log(f"Configuration saved to {config_file}")
        return config_file

    def provision(self):
        """Run the complete provisioning process"""
        print("=" * 70)
        print("KXP/RXP Deployment Server VM Provisioning")
        print("=" * 70)

        start_time = time.time()

        try:
            # Connect to Proxmox
            if not self.connect_proxmox():
                return False

            # Step 1: Download cloud image
            if not self.download_cloud_image():
                return False

            # Step 2: Create VM
            if not self.create_vm():
                return False

            # Step 3: Import and configure disk
            if not self.import_and_configure_disk():
                self.cleanup()
                return False

            # Step 4: Configure Cloud-Init
            if not self.configure_cloud_init():
                self.cleanup()
                return False

            # Step 5: Start VM
            if not self.start_vm():
                self.cleanup()
                return False
        except Exception as e:
            self.log(f"Provisioning failed with error: {e}", "ERROR")
            self.cleanup()
            return False

        # Save configuration
        config_file = self.save_configuration()

        # Clean up SSH connection
        self.cleanup()

        # Calculate elapsed time
        elapsed = int(time.time() - start_time)

        # Success message
        print("\n" + "=" * 70)
        print("PROVISIONING COMPLETE!")
        print("=" * 70)

        print(f"\nVM Details:")
        print(f"  VMID: {self.config['vm']['vmid']}")
        print(f"  Name: {self.config['vm']['name']}")
        print(f"  Node: {self.config['proxmox']['node']}")

        print(f"\nNetwork Configuration:")
        print(f"  Management: DHCP (VLAN {self.config['network']['management']['vlan']})")
        print(f"  Deployment: {self.config['network']['deployment']['ip'].split('/')[0]} (VLAN {self.config['network']['deployment']['vlan']})")

        print(f"\nAccess Credentials:")
        print(f"  Username: {self.config['cloud_init']['username']}")
        print(f"  Password: {self.config['cloud_init']['password']}")

        print(f"\nCloud-Init Status:")
        print(f"  Cloud-Init will now configure the VM automatically")
        print(f"  This process takes 3-5 minutes to complete")
        print(f"  The VM will install packages, configure networking, and set up SSH")

        print(f"\nNext Steps:")
        print(f"  1. Wait 5 minutes for Cloud-Init to complete")
        print(f"  2. Check DHCP lease on UniFi for VM's IP address")
        print(f"  3. Run validation: python vm_provisioning\\validate_vm.py --ip <DHCP_IP>")
        print(f"  4. Access VM: ssh {self.config['cloud_init']['username']}@<DHCP_IP>")

        print(f"\nProvisioning completed in {elapsed} seconds")
        print(f"Logs saved to: {self.log_file}")
        print(f"Configuration saved to: {config_file}")

        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Provision KXP/RXP Deployment Server VM on Proxmox'
    )
    parser.add_argument(
        '--config',
        help='Path to custom configuration file (JSON)',
        default=None
    )
    parser.add_argument(
        '--vmid',
        help='VM ID to use (default: 104)',
        type=int,
        default=104
    )
    parser.add_argument(
        '--name',
        help='VM name (default: cw-rpi-deployment01)',
        default='cw-rpi-deployment01'
    )

    args = parser.parse_args()

    # Load configuration
    config = DEFAULT_CONFIG.copy()

    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            custom_config = json.load(f)
            # Merge custom config
            for key in custom_config:
                if key in config:
                    config[key].update(custom_config[key])

    # Override with command line arguments
    if args.vmid:
        config['vm']['vmid'] = args.vmid
    if args.name:
        config['vm']['name'] = args.name

    # Create provisioner and run
    provisioner = VMProvisioner(config)
    success = provisioner.provision()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()