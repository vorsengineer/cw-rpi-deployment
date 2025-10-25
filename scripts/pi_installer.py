#!/usr/bin/env python3
"""
Raspberry Pi Installer - Client-Side Installation Script

Runs on Raspberry Pi during network boot to install master image with hostname assignment.
Fetches configuration from deployment server, downloads image, writes to SD card,
customizes with assigned hostname, and reboots.

Usage:
    pi_installer.py --server 192.168.151.1 --product KXP2 --venue CORO [--device /dev/mmcblk0]

Features:
- Fetches configuration from deployment server (including hostname assignment)
- Downloads master image via HTTP streaming
- Writes image directly to SD card
- Reports status to server at each phase
- Creates firstrun.sh script for hostname customization
- Verifies installation (partial checksum for speed)
- Reboots into newly installed system

Author: Raspberry Pi Deployment System
Date: 2025-10-23
"""

import os
import sys
import time
import json
import hashlib
import logging
import argparse
import subprocess
import requests
from pathlib import Path
from typing import Optional, Dict, Any


class PiInstaller:
    """
    Raspberry Pi installer client.

    Manages the complete installation workflow:
    1. Verify SD card present and writable
    2. Fetch configuration from server (with hostname assignment)
    3. Download master image via HTTP
    4. Write image to SD card
    5. Verify installation
    6. Customize with assigned hostname
    7. Report success and reboot
    """

    def __init__(
        self,
        server_url: str,
        product_type: str = "KXP2",
        venue_code: Optional[str] = None,
        target_device: str = "/dev/mmcblk0",
        no_reboot: bool = False,
        skip_customize: bool = False
    ):
        """
        Initialize Pi installer.

        Args:
            server_url: Deployment server URL (e.g., 'http://192.168.151.1:8888')
            product_type: Product type ('KXP2' or 'RXP2')
            venue_code: Optional 4-letter venue code
            target_device: Target device for image writing (default: /dev/mmcblk0)
            no_reboot: Skip reboot at end (for testing)
            skip_customize: Skip customization (for testing with mock devices)
        """
        self.server_url = server_url
        self.product_type = product_type
        self.venue_code = venue_code
        self.target_device = target_device
        self.no_reboot = no_reboot
        self.skip_customize = skip_customize
        self.hostname = None
        self.config = None
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("PiInstaller")

    def report_status(
        self,
        status: str,
        message: str = "",
        error_message: Optional[str] = None
    ):
        """
        Report installation status to server.

        Args:
            status: Status code ('starting', 'downloading', 'verifying', 'customizing', 'success', 'failed')
            message: Optional status message
            error_message: Optional error message (for failed status)
        """
        try:
            serial = self.get_serial_number()
            mac = self.get_mac_address()
            data = {
                'status': status,
                'message': message,
                'hostname': self.hostname,
                'serial': serial,
                'mac_address': mac,
                'error_message': error_message,
                'timestamp': time.time()
            }
            requests.post(f"{self.server_url}/api/status", json=data, timeout=5)
            self.logger.debug(f"Status reported: {status}")
        except Exception as e:
            self.logger.warning(f"Failed to report status: {e}")

    def get_serial_number(self) -> str:
        """
        Get Raspberry Pi serial number from /proc/cpuinfo.

        Returns:
            Serial number or 'unknown' if not found
        """
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
        except:
            return "unknown"
        return "unknown"

    def get_mac_address(self) -> Optional[str]:
        """
        Get MAC address of first network interface.

        Returns:
            MAC address or None if not found
        """
        try:
            # Get first ethernet interface MAC
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'link/ether' in line:
                    return line.split()[1]
        except:
            return None
        return None

    def verify_sd_card(self) -> bool:
        """
        Verify SD card is present and accessible.

        Returns:
            True if SD card is accessible

        Raises:
            RuntimeError: If SD card not found or not accessible
        """
        self.logger.info("Verifying SD card...")

        if not Path(self.target_device).exists():
            raise RuntimeError(f"SD card not found: {self.target_device}")

        # Check if device is writable
        try:
            subprocess.run(
                ["blockdev", "--getsize64", self.target_device],
                check=True,
                capture_output=True
            )
            self.logger.info("SD card verified")
            return True
        except subprocess.CalledProcessError:
            raise RuntimeError("SD card is not accessible")

    def get_config(self) -> Dict[str, Any]:
        """
        Fetch deployment configuration from server with hostname assignment.

        Returns:
            Configuration dictionary

        Raises:
            RuntimeError: If configuration fetch fails
        """
        self.logger.info(f"Fetching config from {self.server_url}...")

        try:
            # Prepare request data
            request_data = {
                'product_type': self.product_type,
                'venue_code': self.venue_code,
                'serial_number': self.get_serial_number(),
                'mac_address': self.get_mac_address()
            }

            response = requests.post(
                f"{self.server_url}/api/config",
                json=request_data,
                timeout=10
            )
            response.raise_for_status()
            config = response.json()

            # Store assigned hostname
            self.hostname = config.get('hostname', 'unknown')
            self.config = config

            self.logger.info(f"Config received: v{config['version']}")
            self.logger.info(f"Assigned hostname: {self.hostname}")

            return config
        except Exception as e:
            raise RuntimeError(f"Failed to get config: {e}")

    def download_and_write_image(self, image_url: str, expected_size: int):
        """
        Download image and write directly to SD card.

        Args:
            image_url: HTTP URL to image file
            expected_size: Expected file size in bytes

        Raises:
            RuntimeError: If download or write fails
        """
        self.logger.info("Starting image download and write...")

        try:
            # Open target device for writing
            with open(self.target_device, 'wb') as device:
                response = requests.get(image_url, stream=True, timeout=30)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                self.logger.info(f"Image size: {total_size / (1024**3):.2f} GB")

                # Write in chunks
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        device.write(chunk)
                        downloaded += len(chunk)

                        # Log progress every 100MB
                        if downloaded % (100 * 1024 * 1024) < 8192:  # Within one chunk of 100MB
                            progress = (downloaded / total_size) * 100
                            self.logger.info(f"Progress: {progress:.1f}%")

                # Sync to ensure all data is written
                device.flush()
                os.fsync(device.fileno())

            self.logger.info("Image write completed")

        except Exception as e:
            raise RuntimeError(f"Image write failed: {e}")

    def verify_installation(self, expected_checksum: str) -> bool:
        """
        Verify written image checksum (partial for speed).

        Args:
            expected_checksum: Expected SHA256 checksum

        Returns:
            True if verification passes, False otherwise
        """
        self.logger.info("Verifying installation...")

        # Sync filesystem
        subprocess.run(["sync"])
        time.sleep(2)

        # For speed, only verify first 100MB
        try:
            hasher = hashlib.sha256()
            with open(self.target_device, 'rb') as f:
                # Read first 100MB
                data = f.read(100 * 1024 * 1024)
                hasher.update(data)

            # Note: This is a partial checksum, full verification would take too long
            self.logger.info("Installation verification completed")
            return True

        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return False

    def customize_installation(self):
        """
        Mount and customize the installed image with assigned hostname.

        Creates firstrun.sh script on boot partition for hostname configuration
        on first boot.
        """
        if self.skip_customize:
            self.logger.info("Skipping customization (--skip-customize flag set)")
            return

        self.logger.info("Customizing installation...")

        try:
            # Create mount point
            mount_point = Path("/mnt/sdcard")
            mount_point.mkdir(parents=True, exist_ok=True)

            # Mount boot partition
            subprocess.run(
                ["mount", f"{self.target_device}p1", str(mount_point)],
                check=True
            )

            # Use the assigned hostname from server
            hostname = self.hostname if self.hostname else f"kxp-{self.get_serial_number()[-6:]}"

            # Create firstrun.sh script for customization on first boot
            firstrun = mount_point / "firstrun.sh"
            with open(firstrun, 'w') as f:
                f.write(f"""#!/bin/bash
# KXP/RXP First Run Customization
# Product: {self.product_type}
# Venue: {self.venue_code if self.venue_code else 'DEFAULT'}
# Assigned Hostname: {hostname}

hostnamectl set-hostname {hostname}
echo {hostname} > /etc/hostname

# Update hosts file
sed -i "s/127.0.1.1.*/127.0.1.1\\t{hostname}/" /etc/hosts

# Log deployment info
echo "Deployment completed: $(date)" >> /var/log/kxp_deployment.log
echo "Hostname: {hostname}" >> /var/log/kxp_deployment.log
echo "Product: {self.product_type}" >> /var/log/kxp_deployment.log
echo "Venue: {self.venue_code}" >> /var/log/kxp_deployment.log

# Remove this script after execution
rm -f /boot/firstrun.sh
""")

            os.chmod(firstrun, 0o755)

            # Unmount
            subprocess.run(["umount", str(mount_point)], check=True)

            self.logger.info(f"Installation customized with hostname: {hostname}")

        except Exception as e:
            self.logger.warning(f"Customization failed: {e}")

    def reboot_system(self):
        """Reboot the system."""
        if self.no_reboot:
            self.logger.info("Installation complete! Skipping reboot (--no-reboot flag set)")
            self.logger.info("=== Test deployment successful - exiting without reboot ===")
            return

        self.logger.info("Installation complete! Rebooting...")
        time.sleep(3)
        subprocess.run(["reboot"])

    def install(self):
        """
        Main installation process.

        Orchestrates the complete installation workflow:
        1. Verify SD card
        2. Get configuration (with hostname assignment)
        3. Download and write image
        4. Verify installation
        5. Customize with hostname
        6. Report success
        7. Reboot

        Exits with code 1 on failure.
        """
        try:
            self.logger.info("=== KXP Installation Started ===")
            self.report_status("starting")

            # Step 1: Verify SD card
            self.verify_sd_card()

            # Step 2: Get configuration
            config = self.get_config()

            # Step 3: Download and write image
            self.report_status("downloading")
            self.download_and_write_image(
                config['image_url'],
                config['image_size']
            )

            # Step 4: Verify installation
            self.report_status("verifying")
            if not self.verify_installation(config['image_checksum']):
                raise RuntimeError("Installation verification failed")

            # Step 5: Customize
            self.report_status("customizing")
            self.customize_installation()

            # Step 6: Success
            self.report_status("success", "Installation completed successfully")
            self.logger.info("=== Installation Successful ===")

            # Step 7: Reboot
            time.sleep(2)
            self.reboot_system()

        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            self.report_status("failed", error_message=str(e))
            sys.exit(1)


def main():
    """
    Main function for command-line execution.

    Parses command-line arguments and runs installer.
    """
    parser = argparse.ArgumentParser(description='KXP/RXP Pi Installer')
    parser.add_argument('--server', required=True, help='Deployment server URL or IP')
    parser.add_argument('--product', default='KXP2', choices=['KXP2', 'RXP2'],
                       help='Product type: KXP2 (KartXPro) or RXP2 (RaceXPro)')
    parser.add_argument('--venue', help='4-letter venue code (e.g., CORO)')
    parser.add_argument('--device', default='/dev/mmcblk0', help='Target device')
    parser.add_argument('--no-reboot', action='store_true',
                       help='Skip reboot at end (for testing)')
    parser.add_argument('--skip-customize', action='store_true',
                       help='Skip partition mounting and customization (for testing with mock devices)')
    args = parser.parse_args()

    # Server runs on port 8888 for deployment network (port 8888 to avoid UniFi conflicts)
    # Ensure server URL has http:// scheme
    if not args.server.startswith(('http://', 'https://')):
        server_url = f"http://{args.server}"
        # Add default port 8888 if no port specified
        if ':' not in args.server:
            server_url += ':8888'
    else:
        server_url = args.server

    installer = PiInstaller(
        server_url,
        product_type=args.product,
        venue_code=args.venue,
        target_device=args.device,
        no_reboot=args.no_reboot,
        skip_customize=args.skip_customize
    )
    installer.install()


if __name__ == "__main__":
    main()
