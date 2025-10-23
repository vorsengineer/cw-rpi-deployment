#!/usr/bin/env python3
"""
Check the created VM and fix ISO attachment
"""

from proxmoxer import ProxmoxAPI
import sys

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

VMID = 103  # The VM that was just created
NODE = "cw-dc01"

def main():
    try:
        print("=" * 60)
        print("VM Status Check and ISO Fix")
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

        # Check VM status
        print(f"\nChecking VM {VMID} on node {NODE}...")
        try:
            vm_config = proxmox.nodes(NODE).qemu(VMID).config.get()

            print(f"\n[OK] VM {VMID} exists!")
            print(f"   Name: {vm_config.get('name', 'Unknown')}")
            print(f"   Status: Created")
            print(f"   Cores: {vm_config.get('cores', 'Unknown')}")
            print(f"   Memory: {vm_config.get('memory', 'Unknown')} MB")

            # Check storage
            if 'scsi0' in vm_config:
                print(f"   Disk: {vm_config['scsi0']}")

            # Check networks
            if 'net0' in vm_config:
                print(f"   Network 0: {vm_config['net0']}")
            if 'net1' in vm_config:
                print(f"   Network 1: {vm_config['net1']}")

            # Check if ISO is attached
            if 'ide2' in vm_config:
                print(f"   ISO: {vm_config['ide2']}")
            else:
                print(f"   ISO: Not attached")

                # Try to attach ISO
                print("\nAttempting to attach Ubuntu ISO...")
                iso_path = "local:iso/ubuntu-24.04.1-desktop-amd64.iso"

                try:
                    proxmox.nodes(NODE).qemu(VMID).config.set(ide2=f"{iso_path},media=cdrom")
                    print(f"   [OK] ISO attached: {iso_path}")
                except Exception as e:
                    print(f"   [FAIL] Could not attach ISO: {e}")
                    print(f"\n   To attach manually in Proxmox web UI:")
                    print(f"   1. Select VM {VMID}")
                    print(f"   2. Go to Hardware")
                    print(f"   3. Add -> CD/DVD Drive")
                    print(f"   4. Select: ubuntu-24.04.1-desktop-amd64.iso")

            print("\n" + "=" * 60)
            print("VM SUMMARY")
            print("=" * 60)
            print(f"\nVM ID: {VMID}")
            print(f"Node: {NODE}")
            print(f"Name: {vm_config.get('name', 'Unknown')}")
            print("\nNext Steps:")
            print("1. Open Proxmox web interface: https://192.168.11.194:8006")
            print(f"2. Select VM {VMID} on node {NODE}")
            print("3. Click 'Start' to boot the VM")
            print("4. Click 'Console' to access installation")
            print("\nInstallation Settings:")
            print("   Username: captureworks")
            print("   Password: Jankycorpltd01")
            print("   Hostname: kxp-deployment")
            print("   Network:")
            print("     - eth0: Configure for VLAN 101 (192.168.101.20)")
            print("     - eth1: Leave unconfigured (will be 192.168.151.1 later)")

        except Exception as e:
            if '500' in str(e) and 'does not exist' in str(e):
                print(f"[ERROR] VM {VMID} does not exist on node {NODE}")

                # Check other nodes
                print("\nChecking other nodes...")
                nodes = proxmox.nodes.get()
                for node_info in nodes:
                    node_name = node_info['node']
                    try:
                        vms = proxmox.nodes(node_name).qemu.get()
                        for vm in vms:
                            if vm['vmid'] == str(VMID):
                                print(f"   Found VM {VMID} on node {node_name}!")
                                break
                    except:
                        pass
            else:
                print(f"[ERROR] Failed to get VM info: {e}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()