#!/usr/bin/env python3
"""
Check VM 104 status via Proxmox API
"""

from proxmoxer import ProxmoxAPI
import sys
import time

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"
VMID = 104
NODE = "cw-dc01"

def check_vm_status():
    try:
        print("=" * 60)
        print("Checking VM Status via Proxmox")
        print("=" * 60)

        # Connect to Proxmox
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )

        # Get VM status
        vm_status = proxmox.nodes(NODE).qemu(VMID).status.current.get()
        vm_config = proxmox.nodes(NODE).qemu(VMID).config.get()

        print(f"\n[VM Information]")
        print(f"  VMID: {VMID}")
        print(f"  Name: {vm_config.get('name', 'Unknown')}")
        print(f"  Status: {vm_status['status']}")
        print(f"  Uptime: {vm_status.get('uptime', 0)} seconds")

        # Check QEMU guest agent
        try:
            guest_info = proxmox.nodes(NODE).qemu(VMID).agent.info.get()
            print(f"  Guest Agent: Responding")
            print(f"  Guest Agent Version: {guest_info.get('version', 'Unknown')}")

            # Try to get network interfaces via guest agent
            try:
                network_interfaces = proxmox.nodes(NODE).qemu(VMID).agent('network-get-interfaces').get()
                print(f"\n[Network Interfaces via Guest Agent]")
                for iface in network_interfaces.get('result', []):
                    if iface['name'] in ['eth0', 'eth1']:
                        print(f"  {iface['name']}:")
                        for addr in iface.get('ip-addresses', []):
                            if addr.get('ip-address-type') == 'ipv4':
                                print(f"    IPv4: {addr.get('ip-address')}/{addr.get('prefix')}")
            except:
                print("  [INFO] Cannot get network info via guest agent yet")

        except Exception as e:
            print(f"  Guest Agent: Not responding (Cloud-Init may still be running)")

        # Check Cloud-Init configuration
        print(f"\n[Cloud-Init Configuration]")
        if 'ciuser' in vm_config:
            print(f"  User: {vm_config['ciuser']}")
        if 'ipconfig0' in vm_config:
            print(f"  eth0: {vm_config['ipconfig0']}")
        if 'ipconfig1' in vm_config:
            print(f"  eth1: {vm_config['ipconfig1']}")

        # Get console output (last lines)
        print(f"\n[Recent Console Activity]")
        print("  Checking for Cloud-Init messages...")

        # Calculate runtime
        uptime_seconds = vm_status.get('uptime', 0)
        if uptime_seconds > 0:
            minutes = uptime_seconds // 60
            seconds = uptime_seconds % 60
            print(f"\n[Runtime]")
            print(f"  VM has been running for {minutes} minutes and {seconds} seconds")

            if minutes < 3:
                print("  [INFO] Cloud-Init typically takes 3-5 minutes to complete")
                print("  [INFO] Please wait a bit longer before testing SSH")
            elif minutes >= 3 and minutes < 5:
                print("  [INFO] Cloud-Init should be nearly complete")
            else:
                print("  [INFO] Cloud-Init should be complete by now")

        return vm_status['status'] == 'running'

    except Exception as e:
        print(f"\n[ERROR] Failed to check VM status: {e}")
        return False

if __name__ == "__main__":
    is_running = check_vm_status()

    if is_running:
        print("\n" + "=" * 60)
        print("VM is RUNNING")
        print("=" * 60)
        print("\nIf SSH is not accessible yet, Cloud-Init may still be configuring.")
        print("You can monitor progress via Proxmox console at:")
        print(f"  https://{PROXMOX_HOST}:8006/")
        print(f"  VM {VMID} -> Console")
    else:
        print("\n" + "=" * 60)
        print("VM is NOT RUNNING")
        print("=" * 60)
        print("\nPlease check Proxmox for any issues.")

    sys.exit(0 if is_running else 1)