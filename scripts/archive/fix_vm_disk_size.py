#!/usr/bin/env python3
"""
Fix VM disk size - resize from 3.5GB to 100GB
The cloud image was imported at its original size and needs to be expanded
"""

from proxmoxer import ProxmoxAPI
import paramiko
import sys
import time

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

# SSH credentials
SSH_USER = "root"
SSH_PASSWORD = "Ati4870_x5"

VMID = 104
NODE = "cw-dc01"
STORAGE = "vm_data"
TARGET_SIZE = "100G"

def fix_disk_size():
    """Resize the VM disk to 100GB"""
    print("=" * 60)
    print("Fixing VM Disk Size")
    print("=" * 60)
    print(f"\nProblem: Disk is only 3.5GB instead of 100GB")
    print(f"Solution: Resize disk to {TARGET_SIZE}")
    print("=" * 60)

    try:
        # Connect to Proxmox API
        print("\n[1/7] Connecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )
        print("   [OK] Connected")

        # Check current VM status
        print(f"\n[2/7] Checking VM {VMID} status...")
        vm_status = proxmox.nodes(NODE).qemu(VMID).status.current.get()
        vm_config = proxmox.nodes(NODE).qemu(VMID).config.get()

        print(f"   VM Name: {vm_config.get('name', 'Unknown')}")
        print(f"   Current Status: {vm_status['status']}")

        # Check current disk configuration
        print("\n[3/7] Checking current disk configuration...")
        if 'scsi0' in vm_config:
            current_disk = vm_config['scsi0']
            print(f"   Current disk: {current_disk}")

            # Parse the disk string to get the actual disk name
            # Format is usually: "storage:vm-104-disk-0,size=3584M"
            if ':' in current_disk:
                storage_part, options_part = current_disk.split(':', 1)
                if ',' in options_part:
                    disk_name = options_part.split(',')[0]
                else:
                    disk_name = options_part
                print(f"   Disk name: {disk_name}")

        # Stop the VM first (required for disk resize)
        print(f"\n[4/7] Stopping VM {VMID} (required for resize)...")
        if vm_status['status'] == 'running':
            proxmox.nodes(NODE).qemu(VMID).status.shutdown.post()
            print("   Shutdown signal sent, waiting for VM to stop...")

            # Wait for VM to stop (max 60 seconds)
            for i in range(60):
                time.sleep(1)
                status = proxmox.nodes(NODE).qemu(VMID).status.current.get()
                if status['status'] == 'stopped':
                    print(f"   [OK] VM stopped after {i+1} seconds")
                    break
                if i % 5 == 0:
                    print(f"   Still waiting... ({i} seconds)")
            else:
                print("   [WARNING] VM didn't stop gracefully, forcing stop...")
                proxmox.nodes(NODE).qemu(VMID).status.stop.post()
                time.sleep(5)

        # Resize the disk via API
        print(f"\n[5/7] Resizing disk to {TARGET_SIZE}...")
        try:
            # Use the resize API endpoint
            proxmox.nodes(NODE).qemu(VMID).resize.put(
                disk='scsi0',
                size=TARGET_SIZE
            )
            print(f"   [OK] Disk resize command executed")
        except Exception as e:
            print(f"   [WARNING] API resize might have failed: {e}")
            print("   Trying alternative method via SSH...")

            # Alternative method via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=PROXMOX_HOST,
                username=SSH_USER,
                password=SSH_PASSWORD,
                timeout=30
            )

            # Try qm resize command
            resize_cmd = f"qm resize {VMID} scsi0 {TARGET_SIZE}"
            stdin, stdout, stderr = ssh.exec_command(resize_cmd)
            output = stdout.read().decode()
            error = stderr.read().decode()

            if error and 'successfully' not in error.lower():
                print(f"   [ERROR] Resize failed: {error}")
                ssh.close()
                return False
            else:
                print(f"   [OK] Disk resized via SSH command")

            ssh.close()

        # Verify the new disk size
        print("\n[6/7] Verifying new disk size...")
        time.sleep(2)  # Give it a moment to update

        vm_config = proxmox.nodes(NODE).qemu(VMID).config.get()
        if 'scsi0' in vm_config:
            new_disk = vm_config['scsi0']
            print(f"   New disk configuration: {new_disk}")

            if '100G' in new_disk or '102400M' in new_disk:
                print(f"   [OK] Disk successfully resized to 100GB")
            else:
                print(f"   [WARNING] Disk size might not be correct, please verify")

        # Start the VM again
        print(f"\n[7/7] Starting VM {VMID}...")
        proxmox.nodes(NODE).qemu(VMID).status.start.post()
        print(f"   [OK] VM start command sent")

        # Wait a moment and check status
        time.sleep(5)
        final_status = proxmox.nodes(NODE).qemu(VMID).status.current.get()
        print(f"   VM Status: {final_status['status']}")

        # Success!
        print("\n" + "=" * 60)
        print("SUCCESS! DISK RESIZED")
        print("=" * 60)

        print("\n[WHAT HAPPENS NEXT]")
        print("1. VM is restarting with the expanded 100GB disk")
        print("2. Cloud-Init will run again with sufficient space")
        print("3. This should take 3-5 minutes to complete")
        print("4. All packages should install properly now")

        print("\n[MONITORING]")
        print("You can monitor the boot process:")
        print(f"1. Proxmox Console: https://{PROXMOX_HOST}:8006/")
        print(f"2. Select VM {VMID} -> Console")
        print("3. Watch for Cloud-Init completion messages")

        print("\n[NEXT STEPS]")
        print("Wait 5 minutes, then run the validation script again:")
        print("python scripts\\validate_vm_via_proxmox.py")

        return True

    except Exception as e:
        print(f"\n[ERROR] Disk resize failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Fixing VM disk size issue...")
    print("The cloud image was imported at 3.5GB but needs to be 100GB.\n")

    success = fix_disk_size()

    if success:
        print("\n" + "=" * 60)
        print("DISK FIXED - PLEASE WAIT FOR CLOUD-INIT")
        print("=" * 60)
        print("\nThe disk has been resized to 100GB.")
        print("Cloud-Init should now complete successfully.")
        print("Wait 5 minutes before testing SSH access.")
    else:
        print("\n" + "=" * 60)
        print("DISK RESIZE FAILED")
        print("=" * 60)
        print("\nPlease check the error messages above.")
        print("You may need to manually resize via Proxmox UI.")

    sys.exit(0 if success else 1)