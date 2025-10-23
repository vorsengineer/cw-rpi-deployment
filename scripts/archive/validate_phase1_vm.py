#!/usr/bin/env python3
"""
Validate Phase 1 - Cloud-Init VM Setup
Tests SSH access and verifies all configurations are correctly applied
"""

import paramiko
import sys
import json
import time
from datetime import datetime

# Configuration
VM_IP = "192.168.101.20"
SSH_USER = "captureworks"
SSH_PASSWORD = "Jankycorpltd01"
SSH_PORT = 22

# Expected configurations
EXPECTED_CONFIG = {
    'hostname': 'kxp-deployment',
    'management_ip': '192.168.101.20/24',
    'deployment_ip': '192.168.151.1/24',
    'interfaces': ['eth0', 'eth1'],
    'gateway': '192.168.101.1',
    'dns_servers': ['8.8.8.8', '8.8.4.4']
}

def test_ssh_connection():
    """Test basic SSH connectivity"""
    print(f"[1/7] Testing SSH connection to {VM_IP}...")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=VM_IP,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=10,
            auth_timeout=10,
            banner_timeout=10
        )
        print(f"   [OK] SSH connection successful")
        return ssh
    except paramiko.AuthenticationException:
        print(f"   [ERROR] Authentication failed with provided credentials")
        return None
    except paramiko.SSHException as e:
        print(f"   [ERROR] SSH connection failed: {e}")
        return None
    except Exception as e:
        print(f"   [ERROR] Connection failed: {e}")
        return None

def check_hostname(ssh):
    """Verify hostname is correctly set"""
    print("\n[2/7] Checking hostname configuration...")

    stdin, stdout, stderr = ssh.exec_command('hostname')
    hostname = stdout.read().decode().strip()

    if hostname == EXPECTED_CONFIG['hostname']:
        print(f"   [OK] Hostname: {hostname}")
        return True
    else:
        print(f"   [ERROR] Hostname mismatch: expected '{EXPECTED_CONFIG['hostname']}', got '{hostname}'")
        return False

def check_network_interfaces(ssh):
    """Verify both network interfaces are configured"""
    print("\n[3/7] Checking network interfaces...")

    # Get all network interfaces
    stdin, stdout, stderr = ssh.exec_command('ip -j addr show')
    output = stdout.read().decode()

    try:
        import json
        interfaces = json.loads(output)

        eth0_found = False
        eth1_found = False
        eth0_ip = None
        eth1_ip = None

        for iface in interfaces:
            if iface['ifname'] == 'eth0':
                eth0_found = True
                for addr_info in iface.get('addr_info', []):
                    if addr_info['family'] == 'inet':
                        eth0_ip = f"{addr_info['local']}/{addr_info['prefixlen']}"

            elif iface['ifname'] == 'eth1':
                eth1_found = True
                for addr_info in iface.get('addr_info', []):
                    if addr_info['family'] == 'inet':
                        eth1_ip = f"{addr_info['local']}/{addr_info['prefixlen']}"

        # Verify eth0 (Management Network)
        if eth0_found and eth0_ip == EXPECTED_CONFIG['management_ip']:
            print(f"   [OK] eth0 (Management): {eth0_ip}")
        else:
            print(f"   [ERROR] eth0 configuration issue: {eth0_ip if eth0_found else 'not found'}")

        # Verify eth1 (Deployment Network)
        if eth1_found and eth1_ip == EXPECTED_CONFIG['deployment_ip']:
            print(f"   [OK] eth1 (Deployment): {eth1_ip}")
        else:
            print(f"   [ERROR] eth1 configuration issue: {eth1_ip if eth1_found else 'not found'}")

        return eth0_found and eth1_found and \
               eth0_ip == EXPECTED_CONFIG['management_ip'] and \
               eth1_ip == EXPECTED_CONFIG['deployment_ip']

    except Exception as e:
        # Fallback to non-JSON parsing
        stdin, stdout, stderr = ssh.exec_command('ip addr show')
        output = stdout.read().decode()

        eth0_found = 'eth0' in output and '192.168.101.20' in output
        eth1_found = 'eth1' in output and '192.168.151.1' in output

        if eth0_found:
            print(f"   [OK] eth0 (Management): 192.168.101.20/24")
        else:
            print(f"   [ERROR] eth0 not properly configured")

        if eth1_found:
            print(f"   [OK] eth1 (Deployment): 192.168.151.1/24")
        else:
            print(f"   [ERROR] eth1 not properly configured")

        return eth0_found and eth1_found

def check_routing(ssh):
    """Verify routing configuration"""
    print("\n[4/7] Checking routing configuration...")

    stdin, stdout, stderr = ssh.exec_command('ip route show default')
    default_route = stdout.read().decode().strip()

    if EXPECTED_CONFIG['gateway'] in default_route:
        print(f"   [OK] Default gateway: {EXPECTED_CONFIG['gateway']}")
        return True
    else:
        print(f"   [ERROR] Default gateway not configured correctly")
        print(f"          Current route: {default_route}")
        return False

def check_dns(ssh):
    """Verify DNS configuration"""
    print("\n[5/7] Checking DNS configuration...")

    stdin, stdout, stderr = ssh.exec_command('cat /etc/resolv.conf')
    resolv_conf = stdout.read().decode()

    dns_ok = True
    for dns_server in EXPECTED_CONFIG['dns_servers']:
        if f"nameserver {dns_server}" in resolv_conf:
            print(f"   [OK] DNS server: {dns_server}")
        else:
            print(f"   [ERROR] DNS server {dns_server} not configured")
            dns_ok = False

    return dns_ok

def check_qemu_guest_agent(ssh):
    """Verify QEMU guest agent is installed and running"""
    print("\n[6/7] Checking QEMU guest agent...")

    stdin, stdout, stderr = ssh.exec_command('systemctl is-active qemu-guest-agent')
    status = stdout.read().decode().strip()

    if status == 'active':
        print(f"   [OK] QEMU guest agent is active")
        return True
    else:
        print(f"   [WARNING] QEMU guest agent status: {status}")
        # Try to check if it's at least installed
        stdin, stdout, stderr = ssh.exec_command('dpkg -l | grep qemu-guest-agent')
        if 'qemu-guest-agent' in stdout.read().decode():
            print(f"   [INFO] QEMU guest agent is installed but not active")
        return False

def check_cloud_init_status(ssh):
    """Check if Cloud-Init completed successfully"""
    print("\n[7/7] Checking Cloud-Init status...")

    stdin, stdout, stderr = ssh.exec_command('cloud-init status')
    status = stdout.read().decode().strip()

    if 'done' in status.lower():
        print(f"   [OK] Cloud-Init completed: {status}")
        return True
    else:
        print(f"   [WARNING] Cloud-Init status: {status}")
        return False

def run_validation():
    """Main validation function"""
    print("=" * 60)
    print("Phase 1 VM Validation")
    print("=" * 60)
    print(f"\nTarget VM: {VM_IP}")
    print(f"User: {SSH_USER}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Test SSH connection
    ssh = test_ssh_connection()
    if not ssh:
        print("\n[FAILED] Cannot establish SSH connection")
        print("Cloud-Init may still be running. Please wait and try again.")
        return False

    # Run all validation checks
    checks = {
        'hostname': check_hostname(ssh),
        'network': check_network_interfaces(ssh),
        'routing': check_routing(ssh),
        'dns': check_dns(ssh),
        'guest_agent': check_qemu_guest_agent(ssh),
        'cloud_init': check_cloud_init_status(ssh)
    }

    # Get system information
    print("\n" + "=" * 60)
    print("System Information")
    print("=" * 60)

    # OS Version
    stdin, stdout, stderr = ssh.exec_command('lsb_release -d')
    os_version = stdout.read().decode().strip()
    print(f"OS: {os_version}")

    # Kernel
    stdin, stdout, stderr = ssh.exec_command('uname -r')
    kernel = stdout.read().decode().strip()
    print(f"Kernel: {kernel}")

    # Uptime
    stdin, stdout, stderr = ssh.exec_command('uptime -p')
    uptime = stdout.read().decode().strip()
    print(f"Uptime: {uptime}")

    # Memory
    stdin, stdout, stderr = ssh.exec_command("free -h | grep '^Mem:' | awk '{print $2}'")
    memory = stdout.read().decode().strip()
    print(f"Memory: {memory}")

    # Disk
    stdin, stdout, stderr = ssh.exec_command("df -h / | tail -1 | awk '{print $2}'")
    disk = stdout.read().decode().strip()
    print(f"Root disk: {disk}")

    ssh.close()

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    for check, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check.replace('_', ' ').title()}")

    print(f"\nResult: {passed}/{total} checks passed")

    # Overall result
    critical_checks = ['hostname', 'network', 'routing', 'cloud_init']
    critical_passed = all(checks[c] for c in critical_checks)

    if critical_passed:
        print("\n[SUCCESS] Phase 1 VM validation PASSED!")
        print("All critical checks completed successfully.")
        print("\nVM is ready for Phase 2: Deployment Server Base Configuration")

        # Save validation results
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'vm_ip': VM_IP,
            'checks': checks,
            'passed': passed,
            'total': total,
            'critical_passed': critical_passed,
            'status': 'PASSED'
        }

        with open('phase1_validation_results.json', 'w') as f:
            json.dump(validation_results, f, indent=2)
        print(f"\nValidation results saved to phase1_validation_results.json")

        return True
    else:
        print("\n[FAILED] Phase 1 VM validation FAILED!")
        print("Critical checks did not pass. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)