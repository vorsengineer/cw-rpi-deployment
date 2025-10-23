#!/usr/bin/env python3
"""
Create and configure Cloud-Init VM with Ubuntu Server Cloud Image
This script creates a VM, imports the cloud image, configures Cloud-Init, and starts it
"""

from proxmoxer import ProxmoxAPI
import paramiko
import sys
import time
import json
import os
import subprocess

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

# SSH for advanced operations
SSH_USER = "root"
SSH_PASSWORD = "Ati4870_x5"

# VM Configuration
VMID = 104  # New VM ID
NODE = "cw-dc01"
VM_NAME = "cw-rpi-deployment01"

# Cloud Image
CLOUD_IMAGE_NAME = "ubuntu-24.04-server-cloudimg-amd64.img"
CLOUD_IMAGE_PATH = f"/var/lib/vz/template/iso/{CLOUD_IMAGE_NAME}"

# VM Hardware Settings
VM_CONFIG = {
    'name': VM_NAME,
    'cores': 4,
    'memory': 8192,  # MB
    'disk_size': 100,  # GB
    'storage': 'vm_data',
}

# Cloud-Init Configuration
CLOUD_INIT_CONFIG = {
    'username': 'captureworks',
    'password': 'Jankycorpltd01',
    'hostname': 'kxp-deployment',
    'domain': 'local',
    'network': {
        'eth0': {
            'ip': '192.168.101.20/24',
            'gateway': '192.168.101.1'
        },
        'eth1': {
            'ip': '192.168.151.1/24',
            'gateway': None
        }
    },
    'dns': '8.8.8.8,8.8.4.4'
}

def generate_ssh_keys():
    """Generate SSH key pair for passwordless access"""
    print("\n[SSH Keys] Generating SSH key pair...")

    ssh_dir = "C:\\Temp\\Claude_Desktop\\RPi5_Network_Deployment\\ssh_keys"
    os.makedirs(ssh_dir, exist_ok=True)

    private_key_path = os.path.join(ssh_dir, "deployment_key")
    public_key_path = os.path.join(ssh_dir, "deployment_key.pub")

    if os.path.exists(private_key_path):
        print("   [INFO] SSH keys already exist")
        with open(public_key_path, 'r') as f:
            public_key = f.read().strip()
        return public_key, private_key_path

    try:
        # Generate keys using ssh-keygen
        result = subprocess.run(
            ['ssh-keygen', '-t', 'rsa', '-b', '4096', '-f', private_key_path,
             '-N', '', '-C', 'kxp-deployment@proxmox'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and os.path.exists(public_key_path):
            with open(public_key_path, 'r') as f:
                public_key = f.read().strip()
            print(f"   [OK] SSH keys generated")
            print(f"       Private key: {private_key_path}")
            return public_key, private_key_path
        else:
            print(f"   [WARNING] Could not generate SSH keys: {result.stderr}")
            return None, None

    except Exception as e:
        print(f"   [WARNING] SSH key generation failed: {e}")
        return None, None

def create_vm_with_cloudinit():
    """Create and configure VM with Cloud-Init"""

    try:
        print("=" * 60)
        print("Cloud-Init VM Creation and Configuration")
        print("=" * 60)

        # Connect to Proxmox
        print("\n[1/10] Connecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )
        print("   [OK] Connected to Proxmox API")

        # Create base VM
        print(f"\n[2/10] Creating VM {VMID} ({VM_NAME})...")

        vm_params = {
            'vmid': VMID,
            'name': VM_CONFIG['name'],
            'memory': VM_CONFIG['memory'],
            'cores': VM_CONFIG['cores'],
            'sockets': 1,
            'cpu': 'host',
            'ostype': 'l26',
            'scsihw': 'virtio-scsi-single',
            'agent': 'enabled=1,fstrim_cloned_disks=1',
            'boot': 'order=scsi0',
            'onboot': 1,
            'description': 'KXP/RXP Deployment Server - Cloud-Init Automated (v2.0)'
        }

        try:
            proxmox.nodes(NODE).qemu.create(**vm_params)
            print(f"   [OK] VM {VMID} created")
        except Exception as e:
            if '500' in str(e) and 'already exists' in str(e):
                print(f"   [INFO] VM {VMID} already exists, continuing...")
            else:
                raise e

        time.sleep(2)

        # Configure network interfaces
        print("\n[3/10] Configuring network interfaces...")

        # eth0 - Management interface (VLAN 101)
        proxmox.nodes(NODE).qemu(VMID).config.set(
            net0="virtio,bridge=vmbr0,firewall=1,tag=101"
        )
        print("   [OK] eth0: VLAN 101 (Management Network)")

        # eth1 - Deployment interface (VLAN 151)
        proxmox.nodes(NODE).qemu(VMID).config.set(
            net1="virtio,bridge=vmbr0,firewall=1,tag=151"
        )
        print("   [OK] eth1: VLAN 151 (Deployment Network)")

        # Set serial console (required for cloud images)
        proxmox.nodes(NODE).qemu(VMID).config.set(
            serial0="socket",
            vga="serial0"
        )
        print("   [OK] Serial console configured")

        # Import cloud image as disk via SSH
        print("\n[4/10] Importing cloud image as VM disk (via SSH)...")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=PROXMOX_HOST,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=30
        )

        # Import the cloud image to VM disk
        import_cmd = f"qm importdisk {VMID} {CLOUD_IMAGE_PATH} {VM_CONFIG['storage']}"
        print(f"   Executing: {import_cmd}")

        stdin, stdout, stderr = ssh.exec_command(import_cmd, timeout=120)

        # Monitor import progress
        for line in stdout:
            line = line.strip()
            if line and ('imported' in line.lower() or 'successfully' in line.lower()):
                print(f"   {line}")

        import_output = stdout.read().decode()
        import_error = stderr.read().decode()

        if 'Successfully imported' in import_output or 'imported' in import_output.lower():
            print("   [OK] Cloud image imported as disk")
        else:
            print(f"   [WARNING] Import status unclear: {import_output}")
            if import_error:
                print(f"   Error output: {import_error}")

        ssh.close()

        # Attach the imported disk as scsi0
        print("\n[5/10] Attaching imported disk...")

        # The imported disk is usually named vm-<vmid>-disk-0
        disk_name = f"vm-{VMID}-disk-0"

        # Resize disk to configured size
        proxmox.nodes(NODE).qemu(VMID).config.set(
            scsi0=f"{VM_CONFIG['storage']}:{disk_name},size={VM_CONFIG['disk_size']}G"
        )
        print(f"   [OK] Disk attached and resized to {VM_CONFIG['disk_size']}G")

        # Add Cloud-Init drive
        print("\n[6/10] Adding Cloud-Init drive...")
        proxmox.nodes(NODE).qemu(VMID).config.set(
            ide2=f"{VM_CONFIG['storage']}:cloudinit"
        )
        print("   [OK] Cloud-Init drive added")

        # Configure Cloud-Init settings
        print("\n[7/10] Configuring Cloud-Init settings...")

        config = CLOUD_INIT_CONFIG

        # User and password
        proxmox.nodes(NODE).qemu(VMID).config.set(
            ciuser=config['username'],
            cipassword=config['password']
        )
        print(f"   [OK] User: {config['username']}")

        # Network configuration
        # eth0 - Management
        ipconfig0 = f"ip={config['network']['eth0']['ip']},gw={config['network']['eth0']['gateway']}"
        proxmox.nodes(NODE).qemu(VMID).config.set(ipconfig0=ipconfig0)
        print(f"   [OK] eth0: {config['network']['eth0']['ip']}")

        # eth1 - Deployment (no gateway)
        ipconfig1 = f"ip={config['network']['eth1']['ip']}"
        proxmox.nodes(NODE).qemu(VMID).config.set(ipconfig1=ipconfig1)
        print(f"   [OK] eth1: {config['network']['eth1']['ip']}")

        # DNS
        proxmox.nodes(NODE).qemu(VMID).config.set(
            nameserver=config['dns']
        )
        print(f"   [OK] DNS servers: {config['dns']}")

        # Generate and add SSH keys
        print("\n[8/10] Configuring SSH keys...")
        public_key, private_key_path = generate_ssh_keys()

        if public_key:
            # URL encode the SSH key for Proxmox API
            encoded_key = public_key.replace(' ', '%20').replace('\n', '%0A')
            proxmox.nodes(NODE).qemu(VMID).config.set(
                sshkeys=encoded_key
            )
            print("   [OK] SSH public key added to Cloud-Init")

        # Enable automatic package upgrades
        proxmox.nodes(NODE).qemu(VMID).config.set(
            ciupgrade=1
        )
        print("   [OK] Package upgrades enabled")

        # Start the VM
        print("\n[9/10] Starting VM...")
        proxmox.nodes(NODE).qemu(VMID).status.start.post()
        print(f"   [OK] VM {VMID} started")

        # Save configuration
        print("\n[10/10] Saving VM details...")

        vm_details = {
            'vmid': VMID,
            'name': VM_CONFIG['name'],
            'node': NODE,
            'created': time.strftime('%Y-%m-%d %H:%M:%S'),
            'proxmox_host': PROXMOX_HOST,
            'management_ip': '192.168.101.20',
            'deployment_ip': '192.168.151.1',
            'username': CLOUD_INIT_CONFIG['username'],
            'password': CLOUD_INIT_CONFIG['password'],
            'ssh_private_key': private_key_path if private_key_path else None,
            'cloud_init': True
        }

        with open('vm_cloudinit_details.json', 'w') as f:
            json.dump(vm_details, f, indent=2)

        print("   [OK] VM details saved to vm_cloudinit_details.json")

        # Success summary
        print("\n" + "=" * 60)
        print("SUCCESS! CLOUD-INIT VM CREATED AND STARTED")
        print("=" * 60)

        print(f"\nVM Details:")
        print(f"  VMID: {VMID}")
        print(f"  Name: {VM_CONFIG['name']}")
        print(f"  Node: {NODE}")
        print(f"  Status: Running (Cloud-Init configuring)")

        print(f"\nNetwork Configuration:")
        print(f"  Management IP: 192.168.101.20 (VLAN 101)")
        print(f"  Deployment IP: 192.168.151.1 (VLAN 151)")

        print(f"\nAccess Credentials:")
        print(f"  Username: {CLOUD_INIT_CONFIG['username']}")
        print(f"  Password: {CLOUD_INIT_CONFIG['password']}")

        if private_key_path:
            print(f"  SSH Key: {private_key_path}")

        print("\n[NEXT STEPS]")
        print("1. Wait 3-5 minutes for Cloud-Init to complete")
        print("2. Monitor progress in Proxmox console (optional)")
        print("3. Test SSH access:")
        print(f"   ssh {CLOUD_INIT_CONFIG['username']}@192.168.101.20")

        if private_key_path:
            print(f"   OR with key: ssh -i ssh_keys\\deployment_key {CLOUD_INIT_CONFIG['username']}@192.168.101.20")

        print("\n[INFO] The VM is now self-configuring with Cloud-Init!")
        print("[INFO] All settings will be applied automatically.")

        return True

    except Exception as e:
        print(f"\n[ERROR] VM creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_vm_with_cloudinit()
    sys.exit(0 if success else 1)