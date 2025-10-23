#!/usr/bin/env python3
"""
Fix VM boot issue - VM stuck at serial console
Switch from serial console to VGA display and regenerate Cloud-Init
"""

from proxmoxer import ProxmoxAPI
import paramiko
import sys
import time

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

SSH_USER = "root"
SSH_PASSWORD = "Ati4870_x5"

VMID = 104
NODE = "cw-dc01"

def fix_boot_configuration():
    """Fix VM boot and display configuration"""
    print("=" * 60)
    print("Fixing VM Boot Configuration")
    print("=" * 60)
    print("\nProblem: VM stuck at 'starting serial terminal on interface serial0'")
    print("Solution: Switch from serial to VGA display and reset Cloud-Init")
    print("=" * 60)

    try:
        # Connect to Proxmox
        print("\n[1/8] Connecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )
        print("   [OK] Connected")

        # Check current status
        print(f"\n[2/8] Checking VM {VMID} status...")
        vm_status = proxmox.nodes(NODE).qemu(VMID).status.current.get()
        vm_config = proxmox.nodes(NODE).qemu(VMID).config.get()

        print(f"   VM Name: {vm_config.get('name', 'Unknown')}")
        print(f"   Status: {vm_status['status']}")

        # Stop the VM
        print(f"\n[3/8] Stopping VM {VMID}...")
        if vm_status['status'] == 'running':
            proxmox.nodes(NODE).qemu(VMID).status.stop.post()
            print("   Stop signal sent, waiting...")

            # Wait for VM to stop
            for i in range(30):
                time.sleep(1)
                status = proxmox.nodes(NODE).qemu(VMID).status.current.get()
                if status['status'] == 'stopped':
                    print(f"   [OK] VM stopped after {i+1} seconds")
                    break
            else:
                print("   [WARNING] VM didn't stop cleanly")

        # Remove serial console and set VGA display
        print("\n[4/8] Removing serial console configuration...")
        try:
            # Remove serial0
            proxmox.nodes(NODE).qemu(VMID).config.delete('serial0')
            print("   [OK] Removed serial0")
        except:
            print("   [INFO] serial0 already removed or not present")

        # Set proper VGA display
        print("\n[5/8] Setting VGA display...")
        proxmox.nodes(NODE).qemu(VMID).config.set(
            vga='std'  # Standard VGA instead of serial
        )
        print("   [OK] VGA display set to 'std'")

        # Regenerate Cloud-Init drive to ensure clean state
        print("\n[6/8] Regenerating Cloud-Init configuration...")

        # Re-apply Cloud-Init settings
        config_updates = {
            'ciuser': 'captureworks',
            'cipassword': 'Jankycorpltd01',
            'ipconfig0': 'ip=192.168.101.20/24,gw=192.168.101.1',
            'ipconfig1': 'ip=192.168.151.1/24',
            'nameserver': '8.8.8.8,8.8.4.4',
            'searchdomain': 'local',
            'ciupgrade': 1
        }

        for key, value in config_updates.items():
            proxmox.nodes(NODE).qemu(VMID).config.set(**{key: value})
            print(f"   [OK] Set {key}")

        # SSH to Proxmox to run additional fixes
        print("\n[7/8] Running additional fixes via SSH...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=PROXMOX_HOST,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=30
        )

        # Regenerate the Cloud-Init ISO
        print("   Regenerating Cloud-Init ISO...")
        regen_cmd = f"qm cloudinit update {VMID}"
        stdin, stdout, stderr = ssh.exec_command(regen_cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()

        if error and 'error' in error.lower():
            print(f"   [WARNING] {error}")
        else:
            print("   [OK] Cloud-Init ISO regenerated")

        ssh.close()

        # Start the VM
        print(f"\n[8/8] Starting VM {VMID} with new configuration...")
        proxmox.nodes(NODE).qemu(VMID).status.start.post()
        print("   [OK] VM start command sent")

        # Wait and check status
        time.sleep(5)
        final_status = proxmox.nodes(NODE).qemu(VMID).status.current.get()
        print(f"   VM Status: {final_status['status']}")

        # Success message
        print("\n" + "=" * 60)
        print("BOOT CONFIGURATION FIXED")
        print("=" * 60)

        print("\n[WHAT CHANGED]")
        print("1. Removed serial console (was causing boot hang)")
        print("2. Set standard VGA display")
        print("3. Regenerated Cloud-Init configuration")
        print("4. VM should now boot properly")

        print("\n[MONITORING]")
        print(f"1. Open Proxmox Console: https://{PROXMOX_HOST}:8006/")
        print(f"2. Select VM {VMID} -> Console")
        print("3. You should now see normal boot messages")
        print("4. Cloud-Init should complete in 3-5 minutes")

        print("\n[NEXT STEPS]")
        print("Wait 5 minutes, then test SSH access:")
        print("python scripts\\validate_vm_via_proxmox.py")

        return True

    except Exception as e:
        print(f"\n[ERROR] Configuration fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def alternative_cloud_image_fix():
    """Alternative fix if the above doesn't work"""
    print("\n" + "=" * 60)
    print("Alternative Solution")
    print("=" * 60)

    print("\nIf the VM still doesn't boot properly, we may need to:")
    print("1. Download a different cloud image (Ubuntu 22.04 LTS)")
    print("2. Create a new VM from scratch")
    print("3. Use a different initialization method")

    print("\nOr manually install Ubuntu:")
    print("1. Attach the Ubuntu Server ISO")
    print("2. Boot from ISO")
    print("3. Install manually (takes ~30 minutes)")
    print("4. Configure network and SSH manually")

if __name__ == "__main__":
    print("Fixing VM boot configuration...")
    print("The serial console is causing the VM to hang.\n")

    success = fix_boot_configuration()

    if success:
        print("\n" + "=" * 60)
        print("FIX APPLIED - VM RESTARTING")
        print("=" * 60)
        print("\nThe VM is now booting with proper display configuration.")
        print("Cloud-Init should complete successfully.")
    else:
        print("\n" + "=" * 60)
        print("FIX FAILED")
        print("=" * 60)
        alternative_cloud_image_fix()

    sys.exit(0 if success else 1)