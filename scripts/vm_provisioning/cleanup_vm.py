#!/usr/bin/env python3
"""
VM Cleanup Script for KXP/RXP Deployment Server
Safely removes VM and associated resources

Author: Claude Code
Version: 2.0
Date: 2025-10-23
"""

import sys
import time
import argparse
from datetime import datetime
from proxmoxer import ProxmoxAPI
import paramiko

# Default configuration
DEFAULT_CONFIG = {
    'proxmox': {
        'host': '192.168.11.194',
        'user': 'root@pam',
        'password': 'Ati4870_x5',
        'node': 'cw-dc01'
    }
}


class VMCleaner:
    def __init__(self, config=None):
        """Initialize cleaner with configuration"""
        self.config = config or DEFAULT_CONFIG
        self.proxmox = None

    def log(self, message, level="INFO"):
        """Log messages to console"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefixes = {
            'INFO': '',
            'OK': '[OK]',
            'ERROR': '[ERROR]',
            'WARNING': '[WARNING]'
        }
        prefix = prefixes.get(level, '')
        if prefix:
            print(f"[{timestamp}] {prefix} {message}")
        else:
            print(f"[{timestamp}] {message}")

    def connect_proxmox(self):
        """Connect to Proxmox API"""
        self.log("Connecting to Proxmox API...")
        try:
            self.proxmox = ProxmoxAPI(
                self.config['proxmox']['host'],
                user=self.config['proxmox']['user'],
                password=self.config['proxmox']['password'],
                verify_ssl=False,
                timeout=30
            )
            self.log("Connected to Proxmox", "OK")
            return True
        except Exception as e:
            self.log(f"Failed to connect: {e}", "ERROR")
            return False

    def get_vm_info(self, vmid):
        """Get information about a VM"""
        try:
            node = self.config['proxmox']['node']
            vm_config = self.proxmox.nodes(node).qemu(vmid).config.get()
            vm_status = self.proxmox.nodes(node).qemu(vmid).status.current.get()

            info = {
                'exists': True,
                'name': vm_config.get('name', 'Unknown'),
                'status': vm_status['status'],
                'memory': vm_config.get('memory', 0),
                'cores': vm_config.get('cores', 0),
                'disks': [],
                'networks': []
            }

            # Find disks
            for key, value in vm_config.items():
                if key.startswith(('scsi', 'ide', 'sata', 'virtio')):
                    info['disks'].append(f"{key}: {value}")

            # Find network interfaces
            for key, value in vm_config.items():
                if key.startswith('net'):
                    info['networks'].append(f"{key}: {value}")

            return info

        except Exception as e:
            if '500' in str(e) and 'does not exist' in str(e):
                return {'exists': False}
            else:
                self.log(f"Error getting VM info: {e}", "ERROR")
                return None

    def stop_vm(self, vmid):
        """Stop a running VM"""
        try:
            node = self.config['proxmox']['node']
            vm_status = self.proxmox.nodes(node).qemu(vmid).status.current.get()

            if vm_status['status'] == 'running':
                self.log(f"Stopping VM {vmid}...")

                # Try graceful shutdown first
                try:
                    self.proxmox.nodes(node).qemu(vmid).status.shutdown.post()
                    self.log("Graceful shutdown initiated, waiting...")

                    # Wait up to 30 seconds for graceful shutdown
                    for i in range(30):
                        time.sleep(1)
                        status = self.proxmox.nodes(node).qemu(vmid).status.current.get()
                        if status['status'] == 'stopped':
                            self.log(f"VM stopped gracefully after {i+1} seconds", "OK")
                            return True

                    # If still running, force stop
                    self.log("Graceful shutdown timeout, forcing stop...", "WARNING")
                    self.proxmox.nodes(node).qemu(vmid).status.stop.post()
                    time.sleep(3)
                    self.log("VM force stopped", "OK")

                except Exception as e:
                    self.log(f"Error during shutdown: {e}", "ERROR")
                    # Try force stop as fallback
                    self.proxmox.nodes(node).qemu(vmid).status.stop.post()
                    time.sleep(3)

                return True

            else:
                self.log(f"VM {vmid} is already stopped", "INFO")
                return True

        except Exception as e:
            self.log(f"Failed to stop VM: {e}", "ERROR")
            return False

    def delete_vm(self, vmid, purge=False):
        """Delete a VM and optionally purge its disks"""
        try:
            node = self.config['proxmox']['node']

            # Delete the VM
            self.log(f"Deleting VM {vmid}...")

            if purge:
                # Delete with purge flag (removes disks)
                self.proxmox.nodes(node).qemu(vmid).delete(purge=1)
                self.log(f"VM {vmid} deleted with disk purge", "OK")
            else:
                # Delete without purge (keeps disks)
                self.proxmox.nodes(node).qemu(vmid).delete()
                self.log(f"VM {vmid} deleted (disks preserved)", "OK")

            return True

        except Exception as e:
            if 'does not exist' in str(e):
                self.log(f"VM {vmid} does not exist", "WARNING")
                return True
            else:
                self.log(f"Failed to delete VM: {e}", "ERROR")
                return False

    def cleanup_cloud_images(self):
        """Clean up downloaded cloud images (optional)"""
        self.log("Checking for cloud images to clean up...", "INFO")

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.config['proxmox']['host'],
                username=self.config['proxmox']['user'].split('@')[0],
                password=self.config['proxmox']['password'],
                timeout=30
            )

            # List cloud images
            image_path = "/var/lib/vz/template/iso/"
            stdin, stdout, stderr = ssh.exec_command(f"ls -lh {image_path}*cloudimg*.img 2>/dev/null")
            output = stdout.read().decode()

            if output:
                self.log("Found cloud images:", "INFO")
                for line in output.split('\n'):
                    if line:
                        self.log(f"  {line}", "INFO")
            else:
                self.log("No cloud images found", "INFO")

            ssh.close()

        except Exception as e:
            self.log(f"Could not check cloud images: {e}", "WARNING")

    def cleanup_vm(self, vmid, purge_disks=False, force=False):
        """Main cleanup function"""
        print("=" * 70)
        print(f"VM Cleanup - VMID: {vmid}")
        print("=" * 70)

        # Connect to Proxmox
        if not self.connect_proxmox():
            return False

        # Get VM information
        self.log(f"Getting information for VM {vmid}...")
        vm_info = self.get_vm_info(vmid)

        if not vm_info:
            self.log("Could not get VM information", "ERROR")
            return False

        if not vm_info['exists']:
            self.log(f"VM {vmid} does not exist", "WARNING")
            return True

        # Display VM information
        print("\n" + "=" * 70)
        print("VM Information")
        print("=" * 70)
        print(f"  Name: {vm_info['name']}")
        print(f"  Status: {vm_info['status']}")
        print(f"  Memory: {vm_info['memory']} MB")
        print(f"  Cores: {vm_info['cores']}")

        if vm_info['disks']:
            print(f"  Disks:")
            for disk in vm_info['disks']:
                print(f"    - {disk}")

        if vm_info['networks']:
            print(f"  Networks:")
            for net in vm_info['networks']:
                print(f"    - {net}")

        # Confirm deletion
        if not force:
            print("\n" + "=" * 70)
            print("CONFIRMATION REQUIRED")
            print("=" * 70)
            print(f"You are about to delete VM {vmid} ({vm_info['name']})")
            if purge_disks:
                print("WARNING: This will also DELETE ALL VM DISKS permanently!")
            else:
                print("Note: VM disks will be preserved")

            response = input("\nAre you sure you want to continue? (yes/no): ").lower()
            if response != 'yes':
                self.log("Cleanup cancelled by user", "WARNING")
                return False

        # Stop the VM if running
        if vm_info['status'] == 'running':
            if not self.stop_vm(vmid):
                if not force:
                    self.log("Failed to stop VM, aborting", "ERROR")
                    return False
                else:
                    self.log("Failed to stop VM, continuing with force flag", "WARNING")

        # Delete the VM
        if not self.delete_vm(vmid, purge=purge_disks):
            self.log("Failed to delete VM", "ERROR")
            return False

        # Success
        print("\n" + "=" * 70)
        print("CLEANUP COMPLETE")
        print("=" * 70)
        print(f"VM {vmid} has been successfully removed")
        if purge_disks:
            print("All associated disks have been deleted")
        else:
            print("VM disks have been preserved for potential recovery")

        # Optional: Show cloud images
        self.cleanup_cloud_images()

        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Clean up KXP/RXP Deployment Server VM'
    )
    parser.add_argument(
        'vmid',
        help='VM ID to clean up',
        type=int
    )
    parser.add_argument(
        '--purge-disks',
        help='Also delete VM disks permanently',
        action='store_true'
    )
    parser.add_argument(
        '--force',
        help='Skip confirmation prompt',
        action='store_true'
    )
    parser.add_argument(
        '--config',
        help='Path to configuration file',
        default=None
    )

    args = parser.parse_args()

    # Load configuration
    config = DEFAULT_CONFIG.copy()

    if args.config:
        import json
        with open(args.config, 'r') as f:
            custom_config = json.load(f)
            config.update(custom_config)

    # Create cleaner and run
    cleaner = VMCleaner(config)
    success = cleaner.cleanup_vm(
        vmid=args.vmid,
        purge_disks=args.purge_disks,
        force=args.force
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()