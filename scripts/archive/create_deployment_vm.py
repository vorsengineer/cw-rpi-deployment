#!/usr/bin/env python3
"""
Create KXP Deployment Server VM on Proxmox
This script creates a VM with Ubuntu 24.04 LTS configured for dual network deployment
"""

from proxmoxer import ProxmoxAPI
import sys
import time
import json

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

# VM Configuration
VM_CONFIG = {
    'name': 'cw-rpi-deployment01',
    'vmid': None,  # Auto-assign
    'node': 'cw-dc01',  # Use specific node with ISO available
    'cores': 4,
    'memory': 8192,  # MB
    'disk_size': 100,  # GB
    'os_type': 'l26',  # Linux 2.6+
    'iso': 'ubuntu-24.04.1-desktop-amd64.iso',  # Found on cw-dc01
    'storage': 'vm_data',  # Use vm_data with 912GB available
}

def main():
    try:
        print("=" * 60)
        print("KXP Deployment Server VM Creation Script")
        print("=" * 60)

        # Connect to Proxmox with timeout
        print("\n[1/8] Connecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30  # 30 second timeout
        )
        print("   [OK] Connected to Proxmox API")

        # Use specified node
        print("\n[2/8] Using specified node...")
        node = VM_CONFIG['node']  # cw-dc01

        # Verify node exists and is online
        nodes = proxmox.nodes.get()
        node_found = False
        for n in nodes:
            if n['node'] == node:
                node_found = True
                if n.get('status') != 'online':
                    print(f"   [WARNING] Node {node} is not online!")
                break

        if not node_found:
            print(f"   [FAIL] Node {node} not found!")
            sys.exit(1)

        print(f"   [OK] Using node: {node}")

        # Get available ISO images
        print("\n[3/8] Checking for Ubuntu ISO...")
        try:
            storages = proxmox.nodes(node).storage('local').content.get()
            iso_found = False
            available_isos = []

            for item in storages:
                if item['content'] == 'iso':
                    available_isos.append(item['volid'])
                    if 'ubuntu' in item['volid'].lower() and '24.04' in item['volid']:
                        # Extract just the filename without the 'iso/' prefix
                        full_path = item['volid'].split(':')[1]
                        if full_path.startswith('iso/'):
                            VM_CONFIG['iso'] = full_path[4:]  # Remove 'iso/' prefix
                        else:
                            VM_CONFIG['iso'] = full_path
                        iso_found = True
                        print(f"   [OK] Found Ubuntu 24.04 ISO: {VM_CONFIG['iso']}")
                        break

            if not iso_found:
                print("   [WARNING] Ubuntu 24.04 ISO not found!")
                print("   Available ISOs:")
                for iso in available_isos:
                    print(f"     - {iso}")
                print("\n   Please upload ubuntu-24.04-live-server-amd64.iso to Proxmox")
                print("   You can download it from: https://ubuntu.com/download/server")

                response = input("\n   Do you want to continue without ISO (y/n)? ")
                if response.lower() != 'y':
                    sys.exit(1)
                VM_CONFIG['iso'] = None
        except Exception as e:
            print(f"   [WARNING] Could not check ISOs: {e}")
            VM_CONFIG['iso'] = None

        # Get next available VMID
        print("\n[4/8] Getting next available VMID...")
        vmid = proxmox.cluster.nextid.get()
        print(f"   [OK] Using VMID: {vmid}")

        # Create VM
        print("\n[5/8] Creating VM...")
        print(f"   Name: {VM_CONFIG['name']}")
        print(f"   VMID: {vmid}")
        print(f"   Cores: {VM_CONFIG['cores']}")
        print(f"   Memory: {VM_CONFIG['memory']}MB")
        print(f"   Disk: {VM_CONFIG['disk_size']}GB")

        vm_params = {
            'vmid': vmid,
            'name': VM_CONFIG['name'],
            'memory': VM_CONFIG['memory'],
            'cores': VM_CONFIG['cores'],
            'sockets': 1,
            'cpu': 'host',  # Use host CPU type for best performance
            'ostype': VM_CONFIG['os_type'],
            'scsihw': 'virtio-scsi-single',  # Optimized for NVMe/SSD
            'boot': 'order=scsi0;ide2;net0',
            'agent': 'enabled=1,fstrim_cloned_disks=1',  # Enable guest agent with TRIM
            'numa': 0,
            'onboot': 1,
            'description': 'KXP/RXP Deployment Server - Network Boot System for RPi5 (v2.0)',
        }

        proxmox.nodes(node).qemu.create(**vm_params)
        print("   [OK] VM created successfully")

        # Wait a moment for VM to be fully created
        time.sleep(2)

        # Configure storage (NVMe/SSD optimized)
        print("\n[6/8] Configuring storage...")
        storage_config = f"{VM_CONFIG['storage']}:{VM_CONFIG['disk_size']},discard=on,iothread=1,ssd=1"
        proxmox.nodes(node).qemu(vmid).config.set(scsi0=storage_config)
        print(f"   [OK] Storage configured: {VM_CONFIG['disk_size']}GB with NVMe/SSD optimizations")

        # Add CD-ROM for Ubuntu ISO (if available)
        if VM_CONFIG['iso']:
            print("\n[7/8] Adding Ubuntu ISO...")
            iso_path = f"local:iso/{VM_CONFIG['iso']}"
            proxmox.nodes(node).qemu(vmid).config.set(ide2=f"{iso_path},media=cdrom")
            print(f"   [OK] ISO attached: {VM_CONFIG['iso']}")
        else:
            print("\n[7/8] Skipping ISO attachment (not available)")

        # Configure dual network interfaces
        print("\n[8/8] Configuring network interfaces...")

        # eth0 - Management interface (VLAN 101)
        proxmox.nodes(node).qemu(vmid).config.set(
            net0="virtio,bridge=vmbr0,firewall=1,tag=101"
        )
        print("   [OK] eth0 configured: VLAN 101 (Management Network)")

        # eth1 - Deployment interface (VLAN 151)
        proxmox.nodes(node).qemu(vmid).config.set(
            net1="virtio,bridge=vmbr0,firewall=1,tag=151"
        )
        print("   [OK] eth1 configured: VLAN 151 (Deployment Network)")

        # Summary
        print("\n" + "=" * 60)
        print("[SUCCESS] VM CREATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nVM Details:")
        print(f"  VMID: {vmid}")
        print(f"  Name: {VM_CONFIG['name']}")
        print(f"  Node: {node}")
        print(f"  Cores: {VM_CONFIG['cores']}")
        print(f"  Memory: {VM_CONFIG['memory']}MB")
        print(f"  Disk: {VM_CONFIG['disk_size']}GB (NVMe optimized)")
        print(f"  Networks:")
        print(f"    - eth0: VLAN 101 (Management - 192.168.101.x)")
        print(f"    - eth1: VLAN 151 (Deployment - 192.168.151.x)")

        if VM_CONFIG['iso']:
            print(f"  ISO: {VM_CONFIG['iso']}")
            print("\nNext Steps:")
            print("  1. Open Proxmox web interface: https://192.168.11.194:8006")
            print(f"  2. Select VM {vmid} ({VM_CONFIG['name']})")
            print("  3. Click 'Start' to boot the VM")
            print("  4. Click 'Console' to access the VM console")
            print("  5. Install Ubuntu 24.04 LTS with these settings:")
            print("     - Username: captureworks")
            print("     - Password: Jankycorpltd01")
            print("     - Hostname: kxp-deployment")
            print("     - Configure eth0 for DHCP or static IP in 192.168.101.x")
            print("     - Leave eth1 unconfigured during installation")
            print("     - Enable OpenSSH server")
        else:
            print("\n[WARNING] No Ubuntu ISO attached!")
            print("Next Steps:")
            print("  1. Upload ubuntu-24.04-live-server-amd64.iso to Proxmox")
            print("  2. Attach the ISO to the VM in Proxmox web interface")
            print("  3. Then follow the installation steps above")

        # Save VM details for future reference
        vm_details = {
            'vmid': vmid,
            'name': VM_CONFIG['name'],
            'node': node,
            'created': time.strftime('%Y-%m-%d %H:%M:%S'),
            'proxmox_host': PROXMOX_HOST,
            'networks': {
                'management': 'VLAN 101 (192.168.101.x)',
                'deployment': 'VLAN 151 (192.168.151.x)'
            }
        }

        with open('vm_details.json', 'w') as f:
            json.dump(vm_details, f, indent=2)
        print(f"\n[INFO] VM details saved to vm_details.json")

        return vmid, node

    except Exception as e:
        print(f"\n[ERROR] VM creation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    vmid, node = main()