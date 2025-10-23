#!/usr/bin/env python3
"""
Complete the Cloud-Init VM setup - fix SSH keys and start the VM
"""

from proxmoxer import ProxmoxAPI
import sys
import time
import json
import os
import urllib.parse

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

VMID = 104
NODE = "cw-dc01"

# Cloud-Init Configuration
CLOUD_INIT_CONFIG = {
    'username': 'captureworks',
    'password': 'Jankycorpltd01',
    'hostname': 'kxp-deployment'
}

def complete_setup():
    try:
        print("=" * 60)
        print("Completing Cloud-Init VM Setup")
        print("=" * 60)

        # Connect to Proxmox
        print("\n[1/4] Connecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )
        print("   [OK] Connected")

        # Check VM status
        print(f"\n[2/4] Checking VM {VMID} status...")
        try:
            vm_config = proxmox.nodes(NODE).qemu(VMID).config.get()
            status = proxmox.nodes(NODE).qemu(VMID).status.current.get()

            print(f"   VM Name: {vm_config.get('name', 'Unknown')}")
            print(f"   Status: {status['status']}")

            # Check if Cloud-Init is configured
            if 'ide2' in vm_config and 'cloudinit' in vm_config['ide2']:
                print("   Cloud-Init: Configured")
            if 'ciuser' in vm_config:
                print(f"   User: {vm_config['ciuser']}")
            if 'ipconfig0' in vm_config:
                print(f"   Network eth0: {vm_config['ipconfig0']}")
            if 'ipconfig1' in vm_config:
                print(f"   Network eth1: {vm_config['ipconfig1']}")

        except Exception as e:
            print(f"   [ERROR] Could not get VM status: {e}")
            return False

        # Try to add SSH key properly (optional - can work without it)
        print("\n[3/4] Configuring SSH access...")

        ssh_key_path = "C:\\Temp\\Claude_Desktop\\RPi5_Network_Deployment\\ssh_keys\\deployment_key.pub"

        if os.path.exists(ssh_key_path):
            try:
                with open(ssh_key_path, 'r') as f:
                    ssh_key = f.read().strip()

                # The key should not be URL encoded manually - Proxmox API handles it
                # Just pass the raw key
                proxmox.nodes(NODE).qemu(VMID).config.set(
                    sshkeys=ssh_key
                )
                print("   [OK] SSH public key configured")
            except Exception as e:
                print(f"   [WARNING] Could not set SSH key: {e}")
                print("   [INFO] You can still access with password")
        else:
            print("   [INFO] No SSH key found, using password authentication")

        # Start the VM if not already running
        print(f"\n[4/4] Starting VM {VMID}...")

        current_status = proxmox.nodes(NODE).qemu(VMID).status.current.get()

        if current_status['status'] == 'running':
            print("   [INFO] VM is already running")
        else:
            try:
                proxmox.nodes(NODE).qemu(VMID).status.start.post()
                print(f"   [OK] VM {VMID} started")
            except Exception as e:
                print(f"   [ERROR] Could not start VM: {e}")
                return False

        # Save final configuration
        vm_details = {
            'vmid': VMID,
            'name': vm_config.get('name', 'cw-rpi-deployment01'),
            'node': NODE,
            'status': 'running',
            'proxmox_host': PROXMOX_HOST,
            'management_ip': '192.168.101.20',
            'deployment_ip': '192.168.151.1',
            'username': CLOUD_INIT_CONFIG['username'],
            'password': CLOUD_INIT_CONFIG['password'],
            'cloud_init': True,
            'created': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        with open('vm_final_details.json', 'w') as f:
            json.dump(vm_details, f, indent=2)

        # Success!
        print("\n" + "=" * 60)
        print("SUCCESS! VM IS RUNNING WITH CLOUD-INIT")
        print("=" * 60)

        print("\n[VM DETAILS]")
        print(f"  VMID: {VMID}")
        print(f"  Name: {vm_config.get('name', 'cw-rpi-deployment01')}")
        print(f"  Node: {NODE}")
        print(f"  Status: Running")

        print("\n[NETWORK CONFIGURATION]")
        print(f"  Management: 192.168.101.20 (VLAN 101)")
        print(f"  Deployment: 192.168.151.1 (VLAN 151)")
        print(f"  Gateway: 192.168.101.1")
        print(f"  DNS: 8.8.8.8, 8.8.4.4")

        print("\n[ACCESS CREDENTIALS]")
        print(f"  Username: {CLOUD_INIT_CONFIG['username']}")
        print(f"  Password: {CLOUD_INIT_CONFIG['password']}")

        print("\n[WHAT HAPPENS NEXT]")
        print("1. Cloud-Init is now automatically configuring the VM")
        print("2. This process takes 3-5 minutes")
        print("3. The VM will:")
        print("   - Configure network interfaces")
        print("   - Set hostname and users")
        print("   - Update all packages")
        print("   - Install qemu-guest-agent")
        print("   - Configure SSH access")

        print("\n[TESTING ACCESS]")
        print("Wait about 5 minutes, then test SSH:")
        print(f"  ssh {CLOUD_INIT_CONFIG['username']}@192.168.101.20")

        if os.path.exists("C:\\Temp\\Claude_Desktop\\RPi5_Network_Deployment\\ssh_keys\\deployment_key"):
            print("\nOr with SSH key:")
            print(f"  ssh -i ssh_keys\\deployment_key {CLOUD_INIT_CONFIG['username']}@192.168.101.20")

        print("\n[MONITORING]")
        print("You can monitor the boot process via:")
        print(f"  1. Proxmox Web UI: https://{PROXMOX_HOST}:8006")
        print(f"  2. Select VM {VMID}")
        print("  3. Click 'Console' to watch Cloud-Init progress")

        print("\n[IMPORTANT]")
        print("Cloud-Init only runs on first boot!")
        print("All settings are being applied automatically.")
        print("No manual installation or configuration needed!")

        return True

    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = complete_setup()
    sys.exit(0 if success else 1)