#!/usr/bin/env python3
"""
Final cleanup - archive remaining old scripts
"""

import os
import shutil

base_dir = r"C:\Temp\Claude_Desktop\RPi5_Network_Deployment\scripts"

# Scripts to archive (the remaining old ones)
scripts_to_archive = [
    "check_and_fix_vm.py",
    "configure_vm_networks.py",
    "create_deployment_vm.py",
    "create_proxmox_vm.py",
    "download_cloud_image_ssh.py",
    "setup_cloudinit_vm.py",
    "organize_scripts.py",
    "validate_vm_from_proxmox.sh"
]

archived = []
for script in scripts_to_archive:
    src = os.path.join(base_dir, script)
    dst = os.path.join(base_dir, "archive", script)
    if os.path.exists(src):
        shutil.move(src, dst)
        archived.append(script)
        print(f"Archived: {script}")

print(f"\nArchived {len(archived)} additional scripts")

# List what's left in main scripts folder
remaining = [f for f in os.listdir(base_dir)
             if os.path.isfile(os.path.join(base_dir, f))
             and not f.startswith('cleanup')]

print(f"\nRemaining in main scripts folder:")
for f in remaining:
    print(f"  - {f}")

print("\n✓ Cleanup complete!")
print("\nOrganized structure:")
print("  vm_provisioning/ - Production-ready VM provisioning scripts")
print("  deployment/      - (Ready for Phase 2+ scripts)")
print("  archive/         - Old scripts (for reference)")