#!/usr/bin/env python3
"""
Organize scripts into proper folder structure
"""

import os
import shutil

# Base directory
base_dir = r"C:\Temp\Claude_Desktop\RPi5_Network_Deployment\scripts"

# Create new folder structure
folders = ["vm_provisioning", "deployment", "archive"]
for folder in folders:
    os.makedirs(os.path.join(base_dir, folder), exist_ok=True)
    print(f"Created: {folder}/")

# List of scripts to archive (the reactive fix scripts)
scripts_to_archive = [
    "check_proxmox_resources.py",
    "check_proxmox_resources_node.py",
    "check_vm_status.py",
    "complete_cloudinit_setup.py",
    "create_cloudinit_vm.py",  # Will be replaced with better version
    "create_proxmox_vm.py",     # Old manual version
    "diagnose_vm_issue.py",
    "fix_vm_boot_issue.py",
    "fix_vm_disk_size.py",
    "monitor_cloudinit_progress.py",
    "network_diagnostics.py",
    "ssh_download_cloud_image.py",  # Will be integrated
    "test_proxmox_connection.py",
    "validate_phase1_vm.py",
    "validate_vm_from_proxmox.sh",
    "validate_vm_via_proxmox.py",
    "wait_for_ssh.py"
]

# Move scripts to archive
archived = []
for script in scripts_to_archive:
    src = os.path.join(base_dir, script)
    dst = os.path.join(base_dir, "archive", script)
    if os.path.exists(src):
        shutil.move(src, dst)
        archived.append(script)
        print(f"Archived: {script}")

print(f"\nArchived {len(archived)} scripts")

# List remaining scripts in main folder
remaining = [f for f in os.listdir(base_dir)
             if f.endswith('.py') and os.path.isfile(os.path.join(base_dir, f))]
print(f"\nRemaining in main folder: {remaining}")

print("\nFolder structure created successfully!")
print("Ready to create consolidated scripts in vm_provisioning/")