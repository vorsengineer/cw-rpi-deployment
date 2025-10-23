#!/usr/bin/env python3
"""
Check available resources on a specific Proxmox node
Lists available ISOs, storage pools, and network bridges for the specified node
"""

from proxmoxer import ProxmoxAPI
import sys

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

# Specify the node we want to use
TARGET_NODE = "cw-dc01"  # Use cw-dc01 for deployment server

def main():
    try:
        print("=" * 60)
        print("Proxmox Resource Check - Node Specific")
        print("=" * 60)

        # Connect to Proxmox with timeout
        print("\nConnecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )
        print("[OK] Connected to Proxmox API")

        # Get all nodes
        nodes = proxmox.nodes.get()
        if not nodes:
            print("[FAIL] No nodes available!")
            sys.exit(1)

        # Find our target node
        node_found = False
        for node_info in nodes:
            if node_info['node'] == TARGET_NODE:
                node_found = True
                print(f"\n[OK] Found target node: {TARGET_NODE}")
                print(f"     Status: {node_info.get('status', 'unknown')}")
                if node_info.get('status') != 'online':
                    print(f"     [WARNING] Node {TARGET_NODE} is not online!")
                break

        if not node_found:
            print(f"\n[ERROR] Target node '{TARGET_NODE}' not found!")
            print("Available nodes:")
            for node_info in nodes:
                print(f"  - {node_info['node']} (status: {node_info.get('status', 'unknown')})")
            sys.exit(1)

        node = TARGET_NODE
        print(f"\nChecking resources on node: {node}")
        print("-" * 60)

        # Check storage pools
        print("\n[1] Available Storage Pools on {0}:".format(node))
        print("-" * 30)
        storages = proxmox.nodes(node).storage.get()

        available_storage = []
        for storage in storages:
            if storage['enabled'] == 1:
                print(f"   Storage: {storage['storage']}")
                print(f"     Type: {storage['type']}")
                print(f"     Content: {storage.get('content', 'N/A')}")

                # Check available space if it's a disk storage
                if 'rootdir' in storage.get('content', '') or 'images' in storage.get('content', ''):
                    try:
                        status = proxmox.nodes(node).storage(storage['storage']).status.get()
                        total_gb = status.get('total', 0) / (1024**3)
                        used_gb = status.get('used', 0) / (1024**3)
                        avail_gb = status.get('avail', 0) / (1024**3)

                        print(f"     Total: {total_gb:.1f} GB")
                        print(f"     Used: {used_gb:.1f} GB")
                        print(f"     Available: {avail_gb:.1f} GB")

                        if 'images' in storage.get('content', ''):
                            available_storage.append({
                                'name': storage['storage'],
                                'type': storage['type'],
                                'avail_gb': avail_gb
                            })
                    except:
                        pass
                print()

        # Recommend storage for VM
        print("\n[2] Recommended Storage for VM:")
        print("-" * 30)
        if available_storage:
            # Sort by available space
            available_storage.sort(key=lambda x: x['avail_gb'], reverse=True)
            recommended = available_storage[0]
            print(f"   Recommended: {recommended['name']}")
            print(f"   Type: {recommended['type']}")
            print(f"   Available Space: {recommended['avail_gb']:.1f} GB")

            if recommended['avail_gb'] < 100:
                print(f"   [WARNING] Only {recommended['avail_gb']:.1f} GB available, need at least 100 GB")
        else:
            print("   [WARNING] No suitable storage found for VM disks!")

        # Check ISO storage and available ISOs
        print("\n\n[3] Available ISO Images on {0}:".format(node))
        print("-" * 30)

        iso_storages = []
        for storage in storages:
            if 'iso' in storage.get('content', ''):
                iso_storages.append(storage['storage'])

        if not iso_storages:
            print("   [WARNING] No ISO storage configured!")
        else:
            ubuntu_iso_found = False
            ubuntu_iso_filename = None
            all_isos = []

            for iso_storage in iso_storages:
                print(f"\n   Storage: {iso_storage}")
                print("   " + "-" * 20)

                try:
                    contents = proxmox.nodes(node).storage(iso_storage).content.get()

                    isos_in_storage = []
                    for item in contents:
                        if item.get('content') == 'iso':
                            volid = item['volid']
                            size_gb = item.get('size', 0) / (1024**3)

                            # Extract just the filename
                            if ':' in volid:
                                filename = volid.split('/', 1)[1] if '/' in volid else volid.split(':', 1)[1]
                            else:
                                filename = volid

                            isos_in_storage.append({
                                'filename': filename,
                                'volid': volid,
                                'size_gb': size_gb
                            })

                            # Check for Ubuntu 24.04
                            if 'ubuntu' in filename.lower() and ('24.04' in filename or '24-04' in filename or 'noble' in filename.lower()):
                                ubuntu_iso_found = True
                                ubuntu_iso_filename = filename
                                print(f"   >>> [FOUND] {filename} ({size_gb:.1f} GB)")
                            else:
                                print(f"       {filename} ({size_gb:.1f} GB)")

                    all_isos.extend(isos_in_storage)

                    if not isos_in_storage:
                        print("       (No ISOs in this storage)")

                except Exception as e:
                    print(f"       Error reading storage: {e}")

            if ubuntu_iso_found:
                print(f"\n   [OK] Ubuntu 24.04 ISO found: {ubuntu_iso_filename}")
            else:
                print("\n   [WARNING] Ubuntu 24.04 ISO not found!")
                print("   You need to upload: ubuntu-24.04-live-server-amd64.iso")
                print("   Download from: https://ubuntu.com/download/server")

        # Check network bridges
        print("\n\n[4] Network Bridges on {0}:".format(node))
        print("-" * 30)

        try:
            network = proxmox.nodes(node).network.get()
            bridges = []

            for iface in network:
                if iface['type'] == 'bridge':
                    bridges.append(iface['iface'])
                    print(f"   Bridge: {iface['iface']}")
                    if 'cidr' in iface:
                        print(f"     IP: {iface['cidr']}")
                    if 'bridge_ports' in iface:
                        print(f"     Ports: {iface['bridge_ports']}")
                    print()

            if not bridges:
                print("   [WARNING] No network bridges found!")
            else:
                print(f"   [INFO] Will use '{bridges[0]}' for VM networking")

        except Exception as e:
            print(f"   Error checking networks: {e}")

        # Check existing VMs on this node
        print("\n[5] Existing VMs on {0}:".format(node))
        print("-" * 30)

        try:
            vms = proxmox.nodes(node).qemu.get()

            if vms:
                kxp_exists = False
                for vm in vms:
                    print(f"   VMID: {vm['vmid']} - Name: {vm.get('name', 'unnamed')}")
                    print(f"     Status: {vm['status']}")
                    print(f"     CPUs: {vm.get('cpus', 'N/A')}, RAM: {vm.get('maxmem', 0)/(1024**3):.1f} GB")

                    if 'kxp' in vm.get('name', '').lower():
                        kxp_exists = True
                        print("     [WARNING] This appears to be a KXP deployment server!")
                    print()

                if kxp_exists:
                    print("   [WARNING] A KXP deployment server may already exist!")
                    print("   Check if you need to remove the old one first.")
            else:
                print("   No existing VMs on this node")

        except Exception as e:
            print(f"   Error checking VMs: {e}")

        # Summary
        print("\n" + "=" * 60)
        print(f"SUMMARY FOR NODE: {node}")
        print("=" * 60)

        print("\nFor VM Creation:")
        if available_storage:
            print(f"  [OK] Storage: {available_storage[0]['name']} ({available_storage[0]['avail_gb']:.1f} GB available)")
        else:
            print("  [FAIL] No suitable storage pool found")

        if ubuntu_iso_found:
            print(f"  [OK] Ubuntu 24.04 ISO is available: {ubuntu_iso_filename}")
        else:
            print("  [MISSING] Ubuntu 24.04 ISO needs to be uploaded")

        if bridges:
            print(f"  [OK] Network bridge: {bridges[0]}")
        else:
            print("  [FAIL] No network bridge found")

        print(f"\nNode: {node}")
        print(f"Status: Ready for VM creation" if (available_storage and bridges) else "Not ready - check requirements")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Failed to check resources: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()