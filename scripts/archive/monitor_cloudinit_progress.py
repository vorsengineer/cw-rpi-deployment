#!/usr/bin/env python3
"""
Monitor Cloud-Init progress after disk resize
Checks VM status every 30 seconds until Cloud-Init completes
"""

import time
import sys
from datetime import datetime
from proxmoxer import ProxmoxAPI
import paramiko

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"
SSH_USER = "root"
SSH_PASSWORD = "Ati4870_x5"

VMID = 104
NODE = "cw-dc01"
VM_IP = "192.168.101.20"
VM_USER = "captureworks"
VM_PASSWORD = "Jankycorpltd01"

def check_vm_status():
    """Check VM and Cloud-Init status"""
    try:
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
        uptime = vm_status.get('uptime', 0)

        # Try guest agent
        agent_status = "Not responding"
        try:
            proxmox.nodes(NODE).qemu(VMID).agent.ping.post()
            agent_status = "Active"
        except:
            pass

        return {
            'status': vm_status['status'],
            'uptime_seconds': uptime,
            'uptime_minutes': uptime // 60,
            'agent': agent_status
        }
    except:
        return None

def check_ssh_via_proxmox():
    """Check if SSH is accessible via Proxmox"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=PROXMOX_HOST,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=10
        )

        # Test SSH
        cmd = f"timeout 3 sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no {VM_USER}@{VM_IP} 'echo OK'"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode().strip()

        ssh.close()
        return "OK" in output
    except:
        return False

def monitor_progress():
    """Monitor Cloud-Init progress"""
    print("=" * 60)
    print("Cloud-Init Progress Monitor")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"VM: {VMID} at {VM_IP}")
    print("Checking every 30 seconds...")
    print("=" * 60)

    start_time = time.time()
    max_wait = 600  # 10 minutes max
    check_count = 0

    while time.time() - start_time < max_wait:
        check_count += 1
        elapsed = int(time.time() - start_time)

        print(f"\n[Check #{check_count}] Time: +{elapsed}s ({elapsed//60}m {elapsed%60}s)")

        # Check VM status
        vm_info = check_vm_status()
        if vm_info:
            print(f"  VM Status: {vm_info['status']}")
            print(f"  Uptime: {vm_info['uptime_minutes']}m {vm_info['uptime_seconds']%60}s")
            print(f"  Guest Agent: {vm_info['agent']}")

            # If guest agent is active, Cloud-Init is likely done
            if vm_info['agent'] == "Active":
                print("  [GOOD] Guest agent active - Cloud-Init likely complete!")

        # Check SSH
        ssh_ok = check_ssh_via_proxmox()
        if ssh_ok:
            print("  SSH: ✓ ACCESSIBLE!")
            print("\n" + "=" * 60)
            print("SUCCESS! VM IS READY")
            print("=" * 60)
            print(f"\nCloud-Init completed successfully after {elapsed//60} minutes")
            print(f"SSH is now accessible at {VM_IP}")
            print(f"\nYou can now run the validation script:")
            print(f"  python scripts\\validate_vm_via_proxmox.py")
            return True
        else:
            print("  SSH: Not yet accessible")

        # Progress indicators
        if elapsed < 120:
            print("  Stage: Initial boot and expansion")
        elif elapsed < 240:
            print("  Stage: Package installation")
        elif elapsed < 360:
            print("  Stage: Final configuration")
        else:
            print("  Stage: Should be nearly complete")

        # Wait before next check
        if not ssh_ok and elapsed < max_wait - 30:
            print(f"\nWaiting 30 seconds before next check...")
            time.sleep(30)
        else:
            break

    # Timeout
    if time.time() - start_time >= max_wait:
        print("\n" + "=" * 60)
        print("TIMEOUT REACHED")
        print("=" * 60)
        print("\nCloud-Init is taking longer than expected.")
        print("Please check the VM console manually.")
        return False

    return False

if __name__ == "__main__":
    print("Starting Cloud-Init progress monitoring...")
    print("The VM disk has been resized to 100GB.")
    print("Cloud-Init should complete successfully now.\n")

    success = monitor_progress()
    sys.exit(0 if success else 1)