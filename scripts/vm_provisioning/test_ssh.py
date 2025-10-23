#!/usr/bin/env python3
"""
Test SSH connection to Proxmox
"""

import paramiko
import sys

def test_ssh():
    host = "192.168.11.194"
    user = "root"
    password = "Ati4870_x5"

    print(f"Testing SSH connection to {host}")
    print(f"User: {user}")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print("Connecting...")
        ssh.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=10,  # Shorter timeout for testing
            look_for_keys=False,  # Don't look for SSH keys
            allow_agent=False  # Don't use SSH agent
        )

        print("[OK] SSH connection successful!")

        # Test a simple command
        stdin, stdout, stderr = ssh.exec_command("hostname")
        result = stdout.read().decode().strip()
        print(f"Hostname: {result}")

        ssh.close()
        return True

    except paramiko.AuthenticationException as e:
        print(f"[ERROR] Authentication failed: {e}")
        return False
    except paramiko.SSHException as e:
        print(f"[ERROR] SSH connection failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_ssh()
    sys.exit(0 if success else 1)