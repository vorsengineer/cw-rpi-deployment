#!/usr/bin/env python3
"""
Check available resources on Proxmox host
Lists available ISOs, storage pools, and network bridges
"""

from proxmoxer import ProxmoxAPI
import sys

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

def main():
    try:
        print("=" * 60)
        print("Proxmox Resource Check")
        print("=" * 60)

        # Connect to Proxmox with increased timeout
        print("\nConnecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30  # Increase timeout to 30 seconds
        )
        print("[OK] Connected to Proxmox API")

        # Get nodes
        nodes = proxmox.nodes.get()
        if not nodes:
            print("[FAIL] No nodes available!")
            sys.exit(1)

        node = nodes[0]['node']
        print(f"\nNode: {node}")
        print("-" * 60)

        # Check storage pools
        print("\n[1] Available Storage Pools:")
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
        print("\n\n[3] Available ISO Images:")
        print("-" * 30)

        iso_storages = []
        for storage in storages:
            if 'iso' in storage.get('content', ''):
                iso_storages.append(storage['storage'])

        if not iso_storages:
            print("   [WARNING] No ISO storage configured!")
        else:
            ubuntu_iso_found = False
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
                            if 'ubuntu' in filename.lower() and '24.04' in filename:
                                ubuntu_iso_found = True
                                print(f"   >>> [FOUND] {filename} ({size_gb:.1f} GB)")
                            else:
                                print(f"       {filename} ({size_gb:.1f} GB)")

                    all_isos.extend(isos_in_storage)

                    if not isos_in_storage:
                        print("       (No ISOs in this storage)")

                except Exception as e:
                    print(f"       Error reading storage: {e}")

            if ubuntu_iso_found:
                print("\n   [OK] Ubuntu 24.04 ISO found!")
            else:
                print("\n   [WARNING] Ubuntu 24.04 ISO not found!")
                print("   You need to upload: ubuntu-24.04-live-server-amd64.iso")
                print("   Download from: https://ubuntu.com/download/server")

                # Show how to upload
                print("\n   To upload ISO to Proxmox:")
                print(f"   1. Open https://{PROXMOX_HOST}:8006 in browser")
                print(f"   2. Select node '{node}' -> local -> ISO Images")
                print("   3. Click 'Upload' and select the ISO file")

        # Check network bridges
        print("\n\n[4] Network Bridges:")
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

        # Check existing VMs
        print("\n[5] Existing VMs:")
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
                print("   No existing VMs")

        except Exception as e:
            print(f"   Error checking VMs: {e}")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        print("\nFor VM Creation:")
        if available_storage:
            print(f"  [OK] Storage: {available_storage[0]['name']} ({available_storage[0]['avail_gb']:.1f} GB available)")
        else:
            print("  [FAIL] No suitable storage pool found")

        if ubuntu_iso_found:
            print("  [OK] Ubuntu 24.04 ISO is available")
        else:
            print("  [MISSING] Ubuntu 24.04 ISO needs to be uploaded")

        if bridges:
            print(f"  [OK] Network bridge: {bridges[0]}")
        else:
            print("  [FAIL] No network bridge found")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Failed to check resources: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()