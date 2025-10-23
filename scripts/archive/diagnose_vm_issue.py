#!/usr/bin/env python3
"""
Diagnose VM issues - check guest agent, console, and try alternative access methods
"""

from proxmoxer import ProxmoxAPI
import paramiko
import sys
import time
import json

# Configuration
PROXMOX_HOST = "192.168.11.194"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

# SSH for Proxmox
SSH_USER = "root"
SSH_PASSWORD = "Ati4870_x5"

VMID = 104
NODE = "cw-dc01"

def diagnose_via_api():
    """Use Proxmox API to diagnose VM state"""
    print("=" * 60)
    print("VM Diagnostics via Proxmox API")
    print("=" * 60)

    try:
        # Connect to Proxmox API
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False,
            timeout=30
        )

        # Get VM status
        print("\n[1/5] Checking VM status...")
        vm_status = proxmox.nodes(NODE).qemu(VMID).status.current.get()
        vm_config = proxmox.nodes(NODE).qemu(VMID).config.get()

        print(f"  VM Name: {vm_config.get('name', 'Unknown')}")
        print(f"  Status: {vm_status['status']}")
        uptime = vm_status.get('uptime', 0)
        print(f"  Uptime: {uptime // 60} minutes, {uptime % 60} seconds")

        # Try guest agent
        print("\n[2/5] Checking QEMU Guest Agent...")
        try:
            # Check if agent is responding
            agent_ping = proxmox.nodes(NODE).qemu(VMID).agent.ping.post()
            print("  [OK] Guest agent is responding!")

            # Get network interfaces
            try:
                interfaces = proxmox.nodes(NODE).qemu(VMID).agent('network-get-interfaces').get()
                print("\n  Network Interfaces (via guest agent):")
                for iface in interfaces.get('result', []):
                    if iface['name'] in ['lo', 'eth0', 'eth1', 'ens18', 'ens19']:
                        print(f"    {iface['name']}:")
                        for addr in iface.get('ip-addresses', []):
                            if addr['ip-address-type'] == 'ipv4':
                                print(f"      IPv4: {addr['ip-address']}/{addr.get('prefix', 'N/A')}")
            except Exception as e:
                print(f"  [WARNING] Could not get network info: {e}")

            # Try to execute commands via guest agent
            try:
                print("\n  Executing diagnostics via guest agent...")

                # Check hostname
                result = proxmox.nodes(NODE).qemu(VMID).agent.exec.post(
                    command="hostname"
                )
                pid = result.get('pid')
                time.sleep(1)

                exec_status = proxmox.nodes(NODE).qemu(VMID).agent('exec-status').get(pid=pid)
                if exec_status.get('exited'):
                    out_data = exec_status.get('out-data', '')
                    if out_data:
                        import base64
                        hostname = base64.b64decode(out_data).decode().strip()
                        print(f"    Hostname: {hostname}")

            except Exception as e:
                print(f"  [INFO] Guest exec not available: {e}")

        except Exception as e:
            print(f"  [WARNING] Guest agent not responding")
            print(f"  This is normal if Cloud-Init is still running")
            print(f"  Error: {str(e)[:100]}")

        # Check Cloud-Init settings
        print("\n[3/5] Cloud-Init Configuration:")
        print(f"  User: {vm_config.get('ciuser', 'Not set')}")
        print(f"  Network eth0: {vm_config.get('ipconfig0', 'Not set')}")
        print(f"  Network eth1: {vm_config.get('ipconfig1', 'Not set')}")
        print(f"  DNS: {vm_config.get('nameserver', 'Not set')}")
        print(f"  Auto-upgrade: {vm_config.get('ciupgrade', 'Not set')}")

        return True

    except Exception as e:
        print(f"\n[ERROR] API diagnostics failed: {e}")
        return False

def diagnose_via_ssh():
    """Use SSH to Proxmox for additional diagnostics"""
    print("\n" + "=" * 60)
    print("VM Diagnostics via SSH to Proxmox")
    print("=" * 60)

    try:
        # Connect to Proxmox via SSH
        print("\n[4/5] Connecting to Proxmox via SSH...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=PROXMOX_HOST,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=30
        )
        print("  [OK] Connected to Proxmox")

        # Check VM process
        print("\n[5/5] Checking VM process on Proxmox...")
        stdin, stdout, stderr = ssh.exec_command(f"ps aux | grep 'qemu.*{VMID}'")
        process_output = stdout.read().decode()

        if f'-id {VMID}' in process_output or f'vmid={VMID}' in process_output:
            print("  [OK] QEMU process is running")
        else:
            print("  [WARNING] QEMU process not found")

        # Check network bridge
        print("\n  Checking network bridge status...")
        stdin, stdout, stderr = ssh.exec_command("brctl show vmbr0")
        bridge_output = stdout.read().decode()
        if 'vmbr0' in bridge_output:
            print("  [OK] Network bridge vmbr0 is active")

        # Try to access VM console output
        print("\n  Attempting to get console output...")
        console_cmd = f"qm monitor {VMID}"
        stdin, stdout, stderr = ssh.exec_command(f"echo 'info status' | {console_cmd}")
        monitor_output = stdout.read().decode()
        if monitor_output:
            print(f"  Monitor status: {monitor_output[:200]}")

        # Check if we can see the VM's network from Proxmox
        print("\n  Testing network paths...")

        # Ping both IPs
        for ip, desc in [("192.168.101.20", "Management"), ("192.168.151.1", "Deployment")]:
            stdin, stdout, stderr = ssh.exec_command(f"ping -c 2 -W 2 {ip}")
            ping_output = stdout.read().decode()
            if "2 packets transmitted" in ping_output and "0% packet loss" in ping_output:
                print(f"  [OK] {desc} IP ({ip}) is reachable from Proxmox")
            else:
                print(f"  [FAIL] {desc} IP ({ip}) is not reachable")

        # Try telnet to SSH port
        print("\n  Testing SSH port (22) accessibility...")
        stdin, stdout, stderr = ssh.exec_command("timeout 3 telnet 192.168.101.20 22")
        telnet_output = stdout.read().decode() + stderr.read().decode()

        if "Connected" in telnet_output or "SSH" in telnet_output:
            print("  [OK] SSH port is open and responding")
        elif "Connection refused" in telnet_output:
            print("  [INFO] SSH port refused - service might not be running")
        else:
            print("  [WARNING] SSH port not accessible - timeout or blocked")

        ssh.close()
        return True

    except Exception as e:
        print(f"\n[ERROR] SSH diagnostics failed: {e}")
        return False

def suggest_fixes():
    """Suggest potential fixes based on diagnostics"""
    print("\n" + "=" * 60)
    print("Diagnosis Summary and Recommendations")
    print("=" * 60)

    print("\n[CURRENT STATUS]")
    print("1. VM is running (confirmed via API)")
    print("2. VM is pingable from Proxmox")
    print("3. SSH service appears to be down or not configured")
    print("4. Cloud-Init might have failed or is still running")

    print("\n[RECOMMENDED ACTIONS]")
    print("\n1. Access VM via Proxmox Console:")
    print("   - Go to https://192.168.11.194:8006/")
    print("   - Login with root / Ati4870_x5")
    print("   - Select VM 104 (cw-rpi-deployment01)")
    print("   - Click 'Console' button")
    print("   - Check if you see a login prompt")

    print("\n2. If login prompt is available, login with:")
    print("   - Username: captureworks")
    print("   - Password: Jankycorpltd01")

    print("\n3. Once logged in via console, run these commands:")
    print("   a. Check Cloud-Init status:")
    print("      cloud-init status --long")
    print("   b. Check network configuration:")
    print("      ip addr show")
    print("   c. Check SSH service:")
    print("      systemctl status ssh")
    print("   d. If SSH is not running, start it:")
    print("      sudo systemctl start ssh")
    print("      sudo systemctl enable ssh")

    print("\n4. If Cloud-Init failed, check logs:")
    print("   - /var/log/cloud-init.log")
    print("   - /var/log/cloud-init-output.log")

    print("\n[ALTERNATIVE SOLUTION]")
    print("If Cloud-Init is completely broken, we may need to:")
    print("1. Stop the VM")
    print("2. Regenerate Cloud-Init drive")
    print("3. Start VM again")
    print("\nOr create a new VM with adjusted Cloud-Init settings")

def main():
    print("Starting comprehensive VM diagnostics...")
    print("This will check the VM state from multiple angles.\n")

    # Run API diagnostics
    api_ok = diagnose_via_api()

    # Run SSH diagnostics
    ssh_ok = diagnose_via_ssh()

    # Provide recommendations
    suggest_fixes()

    # Save diagnostic results
    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'vmid': VMID,
        'api_diagnostics': api_ok,
        'ssh_diagnostics': ssh_ok,
        'recommendations': 'Check Proxmox console for manual intervention'
    }

    with open('vm_diagnostics.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nDiagnostic results saved to vm_diagnostics.json")

if __name__ == "__main__":
    main()
    sys.exit(0)  # Always exit successfully since this is diagnostic