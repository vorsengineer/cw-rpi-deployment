#!/usr/bin/env python3
"""
Wait for SSH to become available - simple monitoring loop
"""

import time
import paramiko
from datetime import datetime

PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root"
PROXMOX_PASSWORD = "Ati4870_x5"

VM_IP = "192.168.101.20"
VM_USER = "captureworks"
VM_PASSWORD = "Jankycorpltd01"

def check_ssh():
    """Check if SSH is accessible via Proxmox jump"""
    try:
        # Connect to Proxmox
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(PROXMOX_HOST, username=PROXMOX_USER, password=PROXMOX_PASSWORD, timeout=5)

        # Test SSH to VM
        cmd = f"timeout 3 sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no {VM_USER}@{VM_IP} 'hostname'"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode().strip()

        ssh.close()
        return 'kxp-deployment' in output if output else False
    except:
        return False

print("=" * 60)
print("Waiting for SSH Access")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
print(f"Target: {VM_IP}")
print("Checking every 20 seconds...")
print("=" * 60)

start = time.time()
max_wait = 300  # 5 minutes

while time.time() - start < max_wait:
    elapsed = int(time.time() - start)
    print(f"\n[{elapsed}s] Checking SSH...", end="")

    if check_ssh():
        print(" ✓ SUCCESS!")
        print("\n" + "=" * 60)
        print("VM IS ACCESSIBLE!")
        print("=" * 60)
        print(f"\nSSH is now working after {elapsed} seconds")
        print(f"You can proceed with validation.")
        break
    else:
        print(" Not yet ready")
        if elapsed < max_wait - 20:
            time.sleep(20)

if time.time() - start >= max_wait:
    print("\n[TIMEOUT] SSH still not accessible after 5 minutes")
    print("Check the Proxmox console for any errors")