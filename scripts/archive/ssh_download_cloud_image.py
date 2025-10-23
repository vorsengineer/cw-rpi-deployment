#!/usr/bin/env python3
"""
SSH to Proxmox and download Ubuntu Cloud Image directly
"""

import paramiko
import sys
import time

# SSH Configuration
SSH_HOST = "192.168.11.194"
SSH_USER = "root"
SSH_PASSWORD = "Ati4870_x5"
SSH_PORT = 22

# Cloud Image
CLOUD_IMAGE_URL = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
CLOUD_IMAGE_NAME = "ubuntu-24.04-server-cloudimg-amd64.img"
ISO_PATH = "/var/lib/vz/template/iso"

def ssh_download_cloud_image():
    """SSH to Proxmox and download the cloud image"""

    print("=" * 60)
    print("Downloading Ubuntu Cloud Image via SSH")
    print("=" * 60)

    try:
        # Create SSH client
        print(f"\nConnecting to Proxmox via SSH...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect
        ssh.connect(
            hostname=SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=30
        )
        print(f"[OK] Connected to {SSH_HOST}")

        # First, check if the file already exists
        print("\nChecking if cloud image already exists...")
        stdin, stdout, stderr = ssh.exec_command(f"ls -la {ISO_PATH}/{CLOUD_IMAGE_NAME} 2>/dev/null")
        result = stdout.read().decode()

        if CLOUD_IMAGE_NAME in result:
            print(f"[OK] Cloud image already exists at {ISO_PATH}/{CLOUD_IMAGE_NAME}")

            # Get file size
            stdin, stdout, stderr = ssh.exec_command(f"ls -lh {ISO_PATH}/{CLOUD_IMAGE_NAME} | awk '{{print $5}}'")
            size = stdout.read().decode().strip()
            print(f"    Size: {size}")

            ssh.close()
            return True

        # File doesn't exist, download it
        print(f"\n[INFO] Cloud image not found, downloading...")
        print(f"       URL: {CLOUD_IMAGE_URL}")
        print(f"       Destination: {ISO_PATH}/{CLOUD_IMAGE_NAME}")
        print("\n[INFO] This will take 2-5 minutes depending on connection speed...")

        # Change to ISO directory and download with wget
        download_cmd = f"""
        cd {ISO_PATH} && \
        echo "Starting download..." && \
        wget -O {CLOUD_IMAGE_NAME} {CLOUD_IMAGE_URL} 2>&1 | \
        while read line; do
            echo "$line"
            if [[ "$line" == *"%"* ]]; then
                echo "$line" | grep -o "[0-9]*%" | tail -1
            fi
        done
        """

        # Execute download command
        stdin, stdout, stderr = ssh.exec_command(download_cmd, timeout=600)  # 10 minute timeout

        # Monitor download progress
        print("\nDownload progress:")
        last_percent = ""
        for line in stdout:
            line = line.strip()
            if line:
                if '%' in line:
                    # Extract percentage
                    import re
                    percent_match = re.search(r'(\d+)%', line)
                    if percent_match:
                        percent = percent_match.group(1) + '%'
                        if percent != last_percent:
                            print(f"  {percent}", end='\r')
                            last_percent = percent
                elif 'saved' in line.lower() or 'complete' in line.lower():
                    print(f"\n  {line}")

        # Check if download was successful
        print("\nVerifying download...")
        stdin, stdout, stderr = ssh.exec_command(f"ls -lh {ISO_PATH}/{CLOUD_IMAGE_NAME}")
        result = stdout.read().decode()

        if CLOUD_IMAGE_NAME in result:
            # Get file size
            size_line = result.strip()
            parts = size_line.split()
            if len(parts) >= 5:
                size = parts[4]
                print(f"[OK] Cloud image downloaded successfully!")
                print(f"     File: {ISO_PATH}/{CLOUD_IMAGE_NAME}")
                print(f"     Size: {size}")

                # Calculate checksum for verification
                print("\nCalculating checksum (this may take a moment)...")
                stdin, stdout, stderr = ssh.exec_command(f"sha256sum {ISO_PATH}/{CLOUD_IMAGE_NAME} | cut -d' ' -f1")
                checksum = stdout.read().decode().strip()
                if checksum:
                    print(f"[OK] SHA256: {checksum[:16]}...")

                ssh.close()
                return True
        else:
            print("[ERROR] Download failed - file not found after download")
            error = stderr.read().decode()
            if error:
                print(f"       Error: {error}")

        ssh.close()
        return False

    except paramiko.AuthenticationException:
        print(f"[ERROR] Authentication failed for {SSH_USER}@{SSH_HOST}")
        print("       Please verify username and password")
        return False

    except paramiko.SSHException as e:
        print(f"[ERROR] SSH connection failed: {e}")
        return False

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = ssh_download_cloud_image()

    if success:
        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print("\nThe Ubuntu Cloud Image is ready on your Proxmox server.")
        print("You can now proceed with creating the Cloud-Init VM.")
    else:
        print("\n" + "=" * 60)
        print("DOWNLOAD FAILED")
        print("=" * 60)
        print("\nPlease check the error messages above.")

    sys.exit(0 if success else 1)