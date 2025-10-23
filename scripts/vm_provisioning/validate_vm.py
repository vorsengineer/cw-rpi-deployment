#!/usr/bin/env python3
"""
VM Validation Script for KXP/RXP Deployment Server
Validates that the VM is properly configured and accessible

Author: Claude Code
Version: 2.0
Date: 2025-10-23
"""

import sys
import json
import time
import argparse
from datetime import datetime
import paramiko
from proxmoxer import ProxmoxAPI

# Default configuration
DEFAULT_CONFIG = {
    'proxmox': {
        'host': '192.168.11.194',
        'user': 'root@pam',
        'password': 'Ati4870_x5',
        'node': 'cw-dc01'
    },
    'vm': {
        'vmid': 104,
        'management_ip': None,  # Will be provided via --ip or discovered via DHCP
        'deployment_ip': '192.168.151.1',
        'username': 'captureworks',
        'password': 'Jankycorpltd01',
        'expected_hostname': 'cw-rpi-deployment01'
    }
}


class VMValidator:
    def __init__(self, config=None):
        """Initialize validator with configuration"""
        self.config = config or DEFAULT_CONFIG
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }

    def log(self, message, level="INFO"):
        """Log messages to console"""
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Text prefixes for different levels
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

    def check_proxmox_api(self):
        """Check VM status via Proxmox API"""
        self.log("Checking VM status via Proxmox API...", "INFO")

        try:
            proxmox = ProxmoxAPI(
                self.config['proxmox']['host'],
                user=self.config['proxmox']['user'],
                password=self.config['proxmox']['password'],
                verify_ssl=False,
                timeout=30
            )

            node = self.config['proxmox']['node']
            vmid = self.config['vm']['vmid']

            # Get VM status
            vm_status = proxmox.nodes(node).qemu(vmid).status.current.get()
            vm_config = proxmox.nodes(node).qemu(vmid).config.get()

            self.log(f"VM Name: {vm_config.get('name', 'Unknown')}", "INFO")
            self.log(f"VM Status: {vm_status['status']}", "INFO")

            if vm_status['status'] == 'running':
                uptime = vm_status.get('uptime', 0)
                self.log(f"Uptime: {uptime // 60} minutes", "INFO")
                self.results['checks']['vm_running'] = True
                self.results['passed'] += 1
            else:
                self.log(f"VM is not running", "ERROR")
                self.results['checks']['vm_running'] = False
                self.results['failed'] += 1
                return False

            # Check guest agent
            try:
                proxmox.nodes(node).qemu(vmid).agent.ping.post()
                self.log("Guest agent is responding", "OK")
                self.results['checks']['guest_agent'] = True
                self.results['passed'] += 1

                # Try to get network info via guest agent
                try:
                    interfaces = proxmox.nodes(node).qemu(vmid).agent('network-get-interfaces').get()
                    self.log("Network interfaces via guest agent:", "INFO")
                    for iface in interfaces.get('result', []):
                        if iface['name'] in ['eth0', 'eth1', 'ens18', 'ens19']:
                            for addr in iface.get('ip-addresses', []):
                                if addr.get('ip-address-type') == 'ipv4':
                                    self.log(f"  {iface['name']}: {addr.get('ip-address')}", "INFO")
                except:
                    pass

            except:
                self.log("Guest agent not responding (Cloud-Init may still be running)", "WARNING")
                self.results['checks']['guest_agent'] = False
                self.results['warnings'] += 1

            return True

        except Exception as e:
            self.log(f"Failed to connect to Proxmox API: {e}", "ERROR")
            self.results['checks']['proxmox_api'] = False
            self.results['failed'] += 1
            return False

    def discover_vm_ip(self):
        """Try to discover VM IP via guest agent"""
        if self.config['vm']['management_ip']:
            return self.config['vm']['management_ip']

        self.log("Attempting to discover VM IP address...", "INFO")

        try:
            proxmox = ProxmoxAPI(
                self.config['proxmox']['host'],
                user=self.config['proxmox']['user'],
                password=self.config['proxmox']['password'],
                verify_ssl=False,
                timeout=30
            )

            node = self.config['proxmox']['node']
            vmid = self.config['vm']['vmid']

            # Try to get IP via guest agent
            try:
                interfaces = proxmox.nodes(node).qemu(vmid).agent('network-get-interfaces').get()
                for iface in interfaces.get('result', []):
                    if iface['name'] in ['eth0', 'ens18']:  # Management interface
                        for addr in iface.get('ip-addresses', []):
                            if addr.get('ip-address-type') == 'ipv4':
                                ip = addr.get('ip-address')
                                if ip and not ip.startswith('127.'):
                                    self.log(f"Discovered management IP: {ip}", "OK")
                                    self.config['vm']['management_ip'] = ip
                                    return ip
            except:
                pass

            self.log("Could not discover IP via guest agent", "WARNING")
            self.log("Please check UniFi DHCP leases or VM console for IP address", "INFO")
            return None

        except Exception as e:
            self.log(f"Failed to discover IP: {e}", "ERROR")
            return None

    def check_network_connectivity(self):
        """Check network connectivity from Proxmox to VM"""
        self.log("Checking network connectivity via Proxmox...", "INFO")

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.config['proxmox']['host'],
                username=self.config['proxmox']['user'].split('@')[0],
                password=self.config['proxmox']['password'],
                timeout=30
            )

            # Test management network (only if IP is known)
            mgmt_ip = self.config['vm']['management_ip']
            if mgmt_ip:
                stdin, stdout, stderr = ssh.exec_command(f"ping -c 3 -W 2 {mgmt_ip}")
                output = stdout.read().decode()

                if "3 packets transmitted" in output and "0% packet loss" in output:
                    self.log(f"Management IP ({mgmt_ip}) is reachable", "OK")
                    self.results['checks']['management_network'] = True
                    self.results['passed'] += 1
                else:
                    self.log(f"Management IP ({mgmt_ip}) is not reachable", "ERROR")
                    self.results['checks']['management_network'] = False
                    self.results['failed'] += 1
            else:
                self.log("Management IP not known (DHCP)", "WARNING")
                self.results['checks']['management_network'] = False
                self.results['warnings'] += 1

            # Test deployment network
            deploy_ip = self.config['vm']['deployment_ip']
            stdin, stdout, stderr = ssh.exec_command(f"ping -c 3 -W 2 {deploy_ip}")
            output = stdout.read().decode()

            if "3 packets transmitted" in output and "0% packet loss" in output:
                self.log(f"Deployment IP ({deploy_ip}) is reachable", "OK")
                self.results['checks']['deployment_network'] = True
                self.results['passed'] += 1
            else:
                self.log(f"Deployment IP ({deploy_ip}) is not reachable", "ERROR")
                self.results['checks']['deployment_network'] = False
                self.results['failed'] += 1

            ssh.close()
            return True

        except Exception as e:
            self.log(f"Failed to check network connectivity: {e}", "ERROR")
            return False

    def check_ssh_access(self):
        """Check SSH access to VM"""
        self.log("Checking SSH access to VM...", "INFO")

        # Skip if no management IP
        if not self.config['vm']['management_ip']:
            self.log("Cannot check SSH - management IP not known", "WARNING")
            self.log("Please provide IP with --ip parameter after checking UniFi DHCP", "INFO")
            self.results['checks']['ssh_access'] = False
            self.results['warnings'] += 1
            return False

        try:
            # First, connect to Proxmox
            proxmox_ssh = paramiko.SSHClient()
            proxmox_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            proxmox_ssh.connect(
                hostname=self.config['proxmox']['host'],
                username=self.config['proxmox']['user'].split('@')[0],
                password=self.config['proxmox']['password'],
                timeout=30
            )

            # Install sshpass if needed
            stdin, stdout, stderr = proxmox_ssh.exec_command("which sshpass")
            if not stdout.read().decode().strip():
                self.log("Installing sshpass on Proxmox...", "INFO")
                stdin, stdout, stderr = proxmox_ssh.exec_command("apt-get update && apt-get install -y sshpass")
                stdout.read()  # Wait for completion

            # Test SSH to VM
            vm_ip = self.config['vm']['management_ip']
            vm_user = self.config['vm']['username']
            vm_pass = self.config['vm']['password']

            ssh_cmd = f"sshpass -p '{vm_pass}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {vm_user}@{vm_ip} 'echo SUCCESS'"
            stdin, stdout, stderr = proxmox_ssh.exec_command(ssh_cmd)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if "SUCCESS" in output:
                self.log("SSH access is working", "OK")
                self.results['checks']['ssh_access'] = True
                self.results['passed'] += 1

                # Get additional system info
                self.log("Gathering system information...", "INFO")

                # Check hostname
                cmd = f"sshpass -p '{vm_pass}' ssh -o StrictHostKeyChecking=no {vm_user}@{vm_ip} 'hostname'"
                stdin, stdout, stderr = proxmox_ssh.exec_command(cmd)
                hostname = stdout.read().decode().strip()
                self.log(f"  Hostname: {hostname}", "INFO")

                if hostname == self.config['vm']['expected_hostname']:
                    self.results['checks']['hostname'] = True
                    self.results['passed'] += 1
                else:
                    self.log(f"  Hostname mismatch: expected '{self.config['vm']['expected_hostname']}'", "WARNING")
                    self.results['checks']['hostname'] = False
                    self.results['warnings'] += 1

                # Check Cloud-Init status
                cmd = f"sshpass -p '{vm_pass}' ssh -o StrictHostKeyChecking=no {vm_user}@{vm_ip} 'cloud-init status'"
                stdin, stdout, stderr = proxmox_ssh.exec_command(cmd)
                ci_status = stdout.read().decode().strip()
                self.log(f"  Cloud-Init: {ci_status}", "INFO")

                if 'done' in ci_status.lower():
                    self.results['checks']['cloud_init'] = True
                    self.results['passed'] += 1
                elif 'error' in ci_status.lower():
                    self.log("  Cloud-Init reported errors", "ERROR")
                    self.results['checks']['cloud_init'] = False
                    self.results['failed'] += 1
                else:
                    self.log("  Cloud-Init still running", "WARNING")
                    self.results['checks']['cloud_init'] = False
                    self.results['warnings'] += 1

                # Check key services
                services = ['ssh', 'qemu-guest-agent', 'systemd-networkd']
                for service in services:
                    cmd = f"sshpass -p '{vm_pass}' ssh -o StrictHostKeyChecking=no {vm_user}@{vm_ip} 'systemctl is-active {service}'"
                    stdin, stdout, stderr = proxmox_ssh.exec_command(cmd)
                    status = stdout.read().decode().strip()

                    if status == 'active':
                        self.log(f"  Service {service}: active", "OK")
                        self.results['checks'][f'service_{service}'] = True
                        self.results['passed'] += 1
                    else:
                        self.log(f"  Service {service}: {status}", "WARNING")
                        self.results['checks'][f'service_{service}'] = False
                        self.results['warnings'] += 1

            else:
                self.log(f"SSH access failed: {error}", "ERROR")
                self.results['checks']['ssh_access'] = False
                self.results['failed'] += 1

            proxmox_ssh.close()
            return self.results['checks'].get('ssh_access', False)

        except Exception as e:
            self.log(f"Failed to check SSH access: {e}", "ERROR")
            self.results['checks']['ssh_access'] = False
            self.results['failed'] += 1
            return False

    def validate(self):
        """Run all validation checks"""
        print("=" * 70)
        print("VM Validation for KXP/RXP Deployment Server")
        print("=" * 70)
        print(f"Target VM: {self.config['vm']['vmid']}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Run checks
        self.check_proxmox_api()

        # Try to discover IP if not provided
        if not self.config['vm']['management_ip']:
            self.discover_vm_ip()

        if self.config['vm']['management_ip']:
            print(f"Management IP: {self.config['vm']['management_ip']}")
        else:
            print("Management IP: Not discovered (check UniFi DHCP leases)")

        print("=" * 70)
        self.check_network_connectivity()
        self.check_ssh_access()

        # Summary
        print("\n" + "=" * 70)
        print("Validation Summary")
        print("=" * 70)

        total_checks = self.results['passed'] + self.results['failed'] + self.results['warnings']

        print(f"\nResults:")
        print(f"  Passed: {self.results['passed']}")
        print(f"  Failed: {self.results['failed']}")
        print(f"  Warnings: {self.results['warnings']}")
        print(f"  Total checks: {total_checks}")

        # Determine overall status
        critical_checks = ['vm_running', 'management_network', 'ssh_access']
        critical_passed = all(
            self.results['checks'].get(check, False) for check in critical_checks
        )

        if critical_passed and self.results['failed'] == 0:
            print("\n[SUCCESS] All critical checks passed!")
            print("The VM is fully operational and ready for use.")
            self.results['status'] = 'PASSED'
        elif critical_passed and self.results['failed'] > 0:
            print("\n[WARNING] Critical checks passed but some issues detected.")
            print("The VM is usable but may need attention.")
            self.results['status'] = 'PASSED_WITH_WARNINGS'
        else:
            print("\n[FAILED] Critical checks failed.")
            print("The VM is not ready. Please review the errors above.")
            self.results['status'] = 'FAILED'

            if not self.results['checks'].get('ssh_access', False):
                print("\nTroubleshooting tips:")
                print("1. Check if Cloud-Init is still running (wait 3-5 minutes)")
                print("2. Access the VM console via Proxmox web interface")
                print("3. Login with captureworks/Jankycorpltd01 and check:")
                print("   - cloud-init status")
                print("   - systemctl status ssh")
                print("   - ip addr show")

        # Save results
        results_file = f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nValidation results saved to: {results_file}")

        return self.results['status'] == 'PASSED'


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Validate KXP/RXP Deployment Server VM'
    )
    parser.add_argument(
        '--vmid',
        help='VM ID to validate (default: 104)',
        type=int,
        default=104
    )
    parser.add_argument(
        '--ip',
        help='Management IP to test (will try to discover via guest agent if not provided)',
        default=None
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
        with open(args.config, 'r') as f:
            config = json.load(f)

    # Override with command line arguments
    if args.vmid:
        config['vm']['vmid'] = args.vmid
    if args.ip:
        config['vm']['management_ip'] = args.ip

    # Create validator and run
    validator = VMValidator(config)
    success = validator.validate()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()