#!/usr/bin/env python3
"""
Download Ubuntu Cloud Image to Proxmox via SSH command execution
Or check if it already exists
"""

from proxmoxer import ProxmoxAPI
import subprocess
import sys

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"
NODE = "cw-dc01"

# Cloud Image
CLOUD_IMAGE_URL = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
CLOUD_IMAGE_NAME = "ubuntu-24.04-server-cloudimg-amd64.img"

def check_cloud_image_exists(proxmox, node):
    """Check if cloud image already exists in storage"""
    print("Checking for existing cloud image...")

    try:
        contents = proxmox.nodes(node).storage('local').content.get()

        for item in contents:
            volid = item.get('volid', '')
            # Check for our cloud image or any Ubuntu 24.04 cloud image
            if CLOUD_IMAGE_NAME in volid or ('ubuntu' in volid.lower() and 'cloud' in volid.lower() and '24' in volid):
                print(f"[OK] Found cloud image: {volid}")
                return True, volid

        print("[INFO] Cloud image not found in storage")
        return False, None

    except Exception as e:
        print(f"[WARNING] Could not check storage: {e}")
        return False, None

def main():
    try:
        print("=" * 60)
        print("Ubuntu Cloud Image Download Check")
        print("=" * 60)

        # Connect to Proxmox
        print("\nConnecting to Proxmox...")
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )
        print("[OK] Connected")

        # Check if cloud image exists
        exists, volid = check_cloud_image_exists(proxmox, NODE)

        if exists:
            print("\n[SUCCESS] Cloud image is already available!")
            print("You can proceed with VM creation.")
        else:
            print("\n" + "=" * 60)
            print("MANUAL DOWNLOAD REQUIRED")
            print("=" * 60)
            print("\nThe Ubuntu Cloud Image needs to be downloaded to Proxmox.")
            print("\nOption 1: Via Proxmox Web UI")
            print("-" * 30)
            print(f"1. Open https://{PROXMOX_HOST}:8006")
            print(f"2. Select node '{NODE}'")
            print("3. Go to: local -> Content -> Upload")
            print("4. Click 'Download from URL'")
            print(f"5. Enter URL: {CLOUD_IMAGE_URL}")
            print(f"6. Filename: {CLOUD_IMAGE_NAME}")
            print("7. Click 'Query URL' then 'Download'")

            print("\nOption 2: Via SSH to Proxmox")
            print("-" * 30)
            print("Run these commands:")
            print(f"ssh root@{PROXMOX_HOST}")
            print("cd /var/lib/vz/template/iso/")
            print(f"wget {CLOUD_IMAGE_URL}")
            print(f"# Or with progress bar:")
            print(f"curl -L -o {CLOUD_IMAGE_NAME} {CLOUD_IMAGE_URL}")

            print("\nOption 3: Download locally and upload")
            print("-" * 30)
            print("1. Download the image locally")
            print("2. Upload via Proxmox Web UI")

            print("\n[INFO] The cloud image is about 650MB")
            print("[INFO] Download time: ~2-5 minutes on fast connection")

        return exists

    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False

if __name__ == "__main__":
    exists = main()
    sys.exit(0 if exists else 1)