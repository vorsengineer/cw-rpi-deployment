#!/usr/bin/env python3
"""
Clean up temporary files from Phase 1 troubleshooting
"""

import os
import shutil

base_dir = r"C:\Temp\Claude_Desktop\RPi5_Network_Deployment"

# Create temp_archive folder
archive_dir = os.path.join(base_dir, "temp_archive")
os.makedirs(archive_dir, exist_ok=True)

# Files to archive
temp_files = [
    "vm_details.json",
    "vm_final_details.json",
    "vm_diagnostics.json",
    "vm_cloudinit_details.json",
    "phase1_validation_results.json",
    "phase1_validation_proxmox.json",
    "validate_vm_from_proxmox.sh",
    "validation_results_*.json",
    "vm_provisioning_*.log"
]

archived = []
for pattern in temp_files:
    if '*' in pattern:
        # Handle wildcards
        import glob
        files = glob.glob(os.path.join(base_dir, pattern))
        for file in files:
            if os.path.exists(file):
                filename = os.path.basename(file)
                dst = os.path.join(archive_dir, filename)
                shutil.move(file, dst)
                archived.append(filename)
    else:
        # Handle specific files
        src = os.path.join(base_dir, pattern)
        if os.path.exists(src):
            dst = os.path.join(archive_dir, pattern)
            shutil.move(src, dst)
            archived.append(pattern)

# Also clean up the cleanup scripts themselves
cleanup_scripts = ["cleanup_final.py", "cleanup_temp_files.py"]
for script in cleanup_scripts:
    src = os.path.join(base_dir, "scripts", script)
    if os.path.exists(src):
        dst = os.path.join(base_dir, "scripts", "archive", script)
        shutil.move(src, dst)
        print(f"Archived cleanup script: {script}")

print(f"Archived {len(archived)} temporary files to temp_archive/")
for f in archived:
    print(f"  - {f}")

print("\nCleanup complete!")
print("\nProject structure is now clean and organized:")
print("  - Production scripts in scripts/vm_provisioning/")
print("  - Old scripts archived in scripts/archive/")
print("  - Temp files archived in temp_archive/")