#!/usr/bin/env python3
"""
Configure network interfaces for the VM
"""

from proxmoxer import ProxmoxAPI
import sys

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

VMID = 103
NODE = "cw-dc01"

def main():
    try:
        print("=" * 60)
        print("Configuring VM Network Interfaces")
        print("=" * 60)

        # Connect to Proxmox
        print("\nConnecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )
        print("[OK] Connected")

        print(f"\nConfiguring network interfaces for VM {VMID}...")

        # Configure eth0 - Management interface (VLAN 101)
        print("\n[1/2] Configuring eth0 (Management Network - VLAN 101)...")
        try:
            proxmox.nodes(NODE).qemu(VMID).config.set(
                net0="virtio,bridge=vmbr0,firewall=1,tag=101"
            )
            print("   [OK] eth0 configured: VLAN 101 (Management - 192.168.101.x)")
        except Exception as e:
            print(f"   [FAIL] Could not configure eth0: {e}")

        # Configure eth1 - Deployment interface (VLAN 151)
        print("\n[2/2] Configuring eth1 (Deployment Network - VLAN 151)...")
        try:
            proxmox.nodes(NODE).qemu(VMID).config.set(
                net1="virtio,bridge=vmbr0,firewall=1,tag=151"
            )
            print("   [OK] eth1 configured: VLAN 151 (Deployment - 192.168.151.x)")
        except Exception as e:
            print(f"   [FAIL] Could not configure eth1: {e}")

        # Verify configuration
        print("\nVerifying configuration...")
        vm_config = proxmox.nodes(NODE).qemu(VMID).config.get()

        print("\n" + "=" * 60)
        print("VM CONFIGURATION COMPLETE")
        print("=" * 60)

        print(f"\nVM {VMID}: {vm_config.get('name', 'Unknown')}")
        print(f"Node: {NODE}")
        print("\nHardware Configuration:")
        print(f"   Cores: {vm_config.get('cores', 'Unknown')}")
        print(f"   Memory: {vm_config.get('memory', 'Unknown')} MB")

        if 'scsi0' in vm_config:
            print(f"   Disk: {vm_config['scsi0'].split(',')[0].split(':')[1]}")

        if 'ide2' in vm_config:
            print(f"   ISO: Attached (ubuntu-24.04.1-desktop-amd64.iso)")
        else:
            print(f"   ISO: Not attached")

        print("\nNetwork Configuration:")
        if 'net0' in vm_config:
            print(f"   eth0: {vm_config['net0']} (Management)")
        if 'net1' in vm_config:
            print(f"   eth1: {vm_config['net1']} (Deployment)")

        print("\n" + "=" * 60)
        print("READY TO START INSTALLATION")
        print("=" * 60)

        print("\nNext Steps:")
        print("1. Open Proxmox web interface: https://192.168.11.194:8006")
        print(f"2. Select VM {VMID} ({vm_config.get('name', 'VM')}) on node {NODE}")
        print("3. Click 'Start' button to boot the VM")
        print("4. Click 'Console' button (noVNC or xterm.js)")
        print("5. Install Ubuntu 24.04 LTS with these settings:")
        print("\n   Installation Configuration:")
        print("   • Language: English")
        print("   • Keyboard: Your layout")
        print("   • Installation type: Ubuntu Server (minimal)")
        print("   • Network (eth0): ")
        print("       - Manual configuration")
        print("       - IP: 192.168.101.20/24")
        print("       - Gateway: 192.168.101.1")
        print("       - DNS: 8.8.8.8, 8.8.4.4")
        print("   • Network (eth1): Leave unconfigured during installation")
        print("   • Hostname: kxp-deployment")
        print("   • Username: captureworks")
        print("   • Password: Jankycorpltd01")
        print("   • Enable OpenSSH server: YES")
        print("   • Disk: Use entire disk with LVM")
        print("\n[INFO] The VM is configured and ready for Ubuntu installation!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()