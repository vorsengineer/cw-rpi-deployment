#!/usr/bin/env python3
"""
Network diagnostics to understand connectivity issues
"""

import subprocess
import socket
import sys

def check_local_network():
    """Check local network configuration"""
    print("=" * 60)
    print("Local Network Configuration")
    print("=" * 60)

    # Get network interfaces
    print("\n[Windows Network Interfaces]")
    try:
        result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True)
        lines = result.stdout.split('\n')

        current_adapter = None
        for line in lines:
            if 'Ethernet adapter' in line or 'Wireless' in line:
                current_adapter = line.strip()
                print(f"\n{current_adapter}")
            elif current_adapter and 'IPv4 Address' in line:
                print(f"  {line.strip()}")
            elif current_adapter and 'Subnet Mask' in line:
                print(f"  {line.strip()}")
            elif current_adapter and 'Default Gateway' in line:
                print(f"  {line.strip()}")
            elif current_adapter and 'VLAN' in line:
                print(f"  {line.strip()}")
    except Exception as e:
        print(f"[ERROR] Could not get network configuration: {e}")

def test_proxmox_network():
    """Test connectivity to Proxmox host"""
    print("\n" + "=" * 60)
    print("Testing Proxmox Host Connectivity")
    print("=" * 60)

    proxmox_ip = "192.168.11.194"
    print(f"\nTesting connectivity to Proxmox host ({proxmox_ip})...")

    result = subprocess.run(['ping', '-n', '2', proxmox_ip], capture_output=True, text=True)
    if 'Reply from' in result.stdout:
        print(f"[OK] Proxmox host is reachable at {proxmox_ip}")
        return True
    else:
        print(f"[ERROR] Cannot reach Proxmox host at {proxmox_ip}")
        return False

def check_vlan_access():
    """Check which VLANs/subnets are accessible"""
    print("\n" + "=" * 60)
    print("Checking Subnet Accessibility")
    print("=" * 60)

    subnets_to_test = [
        ("192.168.11.1", "Main network gateway"),
        ("192.168.11.194", "Proxmox host"),
        ("192.168.101.1", "VLAN 101 gateway"),
        ("192.168.101.20", "VM Management IP"),
        ("192.168.151.1", "VM Deployment IP")
    ]

    accessible = []
    not_accessible = []

    for ip, description in subnets_to_test:
        print(f"\nTesting {ip} ({description})...")
        result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip],
                               capture_output=True, text=True)
        if 'Reply from' in result.stdout or 'bytes=' in result.stdout:
            print(f"  [OK] {ip} is reachable")
            accessible.append((ip, description))
        elif 'Destination host unreachable' in result.stdout:
            print(f"  [UNREACHABLE] {ip} - Host unreachable")
            not_accessible.append((ip, description))
        else:
            print(f"  [TIMEOUT] {ip} - No response")
            not_accessible.append((ip, description))

    return accessible, not_accessible

def suggest_solutions(accessible, not_accessible):
    """Suggest solutions based on network analysis"""
    print("\n" + "=" * 60)
    print("Analysis and Recommendations")
    print("=" * 60)

    # Check if we can reach Proxmox but not the VM
    proxmox_reachable = any(ip == "192.168.11.194" for ip, _ in accessible)
    vm_not_reachable = any(ip == "192.168.101.20" for ip, _ in not_accessible)

    if proxmox_reachable and vm_not_reachable:
        print("\n[ISSUE] Can reach Proxmox but not the VM")
        print("\nPossible causes:")
        print("1. This Windows machine doesn't have access to VLAN 101 (192.168.101.x)")
        print("2. The VM's network configuration might not be complete")
        print("3. Cloud-Init might have failed to configure networking")

        print("\n[RECOMMENDED ACTIONS]")
        print("1. Connect to Proxmox Web Console to check VM directly:")
        print(f"   https://192.168.11.194:8006/")
        print("   - Login and select VM 104")
        print("   - Open Console to see if VM booted properly")
        print("   - Check for any error messages")

        print("\n2. Check VM network via Proxmox Console:")
        print("   In the VM console, run:")
        print("   - ip addr show")
        print("   - systemctl status cloud-init")
        print("   - cloud-init status")

        print("\n3. Alternative validation approach:")
        print("   - Use a jump host that has access to VLAN 101")
        print("   - Or temporarily add a route to VLAN 101 on this machine")
        print("   - Or validate directly from Proxmox host via SSH")

        print("\n4. Validate from Proxmox host itself:")
        print("   SSH to Proxmox: ssh root@192.168.11.194")
        print("   Then from Proxmox: ssh captureworks@192.168.101.20")

    elif not proxmox_reachable:
        print("\n[ISSUE] Cannot reach Proxmox host")
        print("Please check your network connection and VPN if applicable")

    else:
        print("\n[INFO] Network analysis complete")
        if accessible:
            print(f"Accessible networks: {len(accessible)}")
        if not_accessible:
            print(f"Inaccessible networks: {len(not_accessible)}")

def main():
    print("=" * 60)
    print("Network Connectivity Diagnostics")
    print("=" * 60)

    # Check local configuration
    check_local_network()

    # Test network access
    proxmox_ok = test_proxmox_network()

    # Check VLAN access
    accessible, not_accessible = check_vlan_access()

    # Provide recommendations
    suggest_solutions(accessible, not_accessible)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    if not_accessible and any(ip == "192.168.101.20" for ip, _ in not_accessible):
        print("\n[RESULT] Cannot reach VM from this workstation")
        print("\nThe VM might be properly configured, but this Windows machine")
        print("doesn't have network access to VLAN 101 (192.168.101.x).")
        print("\nYou need to validate the VM using one of these methods:")
        print("1. Proxmox Web Console (recommended)")
        print("2. SSH to Proxmox first, then to the VM")
        print("3. Use a machine that has access to VLAN 101")

        # Create alternative validation script
        create_proxmox_validation_script()
        return False
    else:
        print("\n[RESULT] Network diagnostics complete")
        return True

def create_proxmox_validation_script():
    """Create a script to validate from Proxmox host"""
    print("\n" + "=" * 60)
    print("Creating Alternative Validation Method")
    print("=" * 60)

    validation_commands = """#!/bin/bash
# Run this script on the Proxmox host to validate the VM

echo "===================================================="
echo "VM Validation from Proxmox Host"
echo "===================================================="

VM_IP="192.168.101.20"
VM_USER="captureworks"
VM_PASS="Jankycorpltd01"

echo -e "\\n[1] Testing network connectivity to VM..."
ping -c 3 $VM_IP

echo -e "\\n[2] Testing SSH access..."
sshpass -p "$VM_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \\
    $VM_USER@$VM_IP "hostname; ip addr show; cloud-init status"

echo -e "\\n[3] Checking VM configuration..."
sshpass -p "$VM_PASS" ssh -o StrictHostKeyChecking=no \\
    $VM_USER@$VM_IP "
echo '=== Hostname ==='
hostname
echo '=== Network Interfaces ==='
ip addr show eth0 | grep inet
ip addr show eth1 | grep inet
echo '=== Routing ==='
ip route show default
echo '=== DNS ==='
cat /etc/resolv.conf | grep nameserver
echo '=== Cloud-Init Status ==='
cloud-init status --long
echo '=== Guest Agent ==='
systemctl status qemu-guest-agent --no-pager
"

echo -e "\\n===================================================="
echo "Validation Complete"
echo "===================================================="
"""

    with open('validate_vm_from_proxmox.sh', 'w') as f:
        f.write(validation_commands)

    print("\nCreated: validate_vm_from_proxmox.sh")
    print("\nTo use this script:")
    print("1. Copy it to Proxmox: scp validate_vm_from_proxmox.sh root@192.168.11.194:/tmp/")
    print("2. SSH to Proxmox: ssh root@192.168.11.194")
    print("3. Run: bash /tmp/validate_vm_from_proxmox.sh")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)