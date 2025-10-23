#!/usr/bin/env python3
"""
Test connection to Proxmox host
Tests API connectivity before proceeding with VM creation
"""

import requests
import json
import urllib3
from urllib.parse import quote

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Proxmox connection details
PROXMOX_HOST = "192.168.11.194"
PROXMOX_PORT = "8006"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ati4870_x5"

def test_proxmox_connection():
    """Test connection to Proxmox API"""

    print("=" * 60)
    print("Testing Proxmox Connection")
    print("=" * 60)
    print(f"Host: {PROXMOX_HOST}:{PROXMOX_PORT}")
    print(f"User: {PROXMOX_USER}")
    print("-" * 60)

    # Build authentication URL
    auth_url = f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json/access/ticket"

    # Authentication data
    auth_data = {
        'username': PROXMOX_USER,
        'password': PROXMOX_PASSWORD
    }

    try:
        print("1. Testing network connectivity...")
        # First test if we can reach the host
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((PROXMOX_HOST, int(PROXMOX_PORT)))
        sock.close()

        if result != 0:
            print(f"   [FAIL] Cannot reach {PROXMOX_HOST}:{PROXMOX_PORT}")
            print("   Please check network connectivity and firewall settings")
            return False

        print(f"   [OK] Host {PROXMOX_HOST}:{PROXMOX_PORT} is reachable")

        print("\n2. Testing API authentication...")
        # Try to authenticate
        response = requests.post(
            auth_url,
            data=auth_data,
            verify=False,  # Skip SSL verification for self-signed cert
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if 'data' in result:
                print("   [OK] Authentication successful!")

                # Extract ticket and CSRF token
                ticket = result['data'].get('ticket')
                csrf = result['data'].get('CSRFPreventionToken')

                if ticket:
                    print(f"   [OK] Received authentication ticket")
                    print(f"   [OK] Received CSRF token")

                    # Test API access by getting version info
                    print("\n3. Testing API access (getting version info)...")

                    headers = {
                        'Cookie': f"PVEAuthCookie={ticket}",
                        'CSRFPreventionToken': csrf
                    }

                    version_url = f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json/version"
                    version_response = requests.get(
                        version_url,
                        headers=headers,
                        verify=False,
                        timeout=10
                    )

                    if version_response.status_code == 200:
                        version_data = version_response.json()
                        if 'data' in version_data:
                            version_info = version_data['data']
                            print(f"   [OK] Proxmox VE Version: {version_info.get('version', 'Unknown')}")
                            print(f"   [OK] Release: {version_info.get('release', 'Unknown')}")
                            print(f"   [OK] Repository: {version_info.get('repoid', 'Unknown')}")

                    print("\n" + "=" * 60)
                    print("[SUCCESS] CONNECTION TEST SUCCESSFUL!")
                    print("=" * 60)
                    print("\nProxmox host is accessible and credentials are valid.")
                    print("Ready to proceed with VM creation.")

                    return True
                else:
                    print("   [FAIL] Authentication failed - no ticket received")
                    return False
        else:
            print(f"   [FAIL] Authentication failed with status code: {response.status_code}")
            if response.status_code == 401:
                print("   Please verify username and password")
            return False

    except requests.exceptions.ConnectionError as e:
        print(f"   [FAIL] Connection error: Cannot reach Proxmox host at {PROXMOX_HOST}:{PROXMOX_PORT}")
        print(f"   Error details: {str(e)}")
        print("\n   Possible issues:")
        print("   - Proxmox host is not running")
        print("   - Firewall blocking port 8006")
        print("   - Network connectivity issue")
        return False

    except requests.exceptions.Timeout:
        print(f"   [FAIL] Connection timeout: Host {PROXMOX_HOST} is not responding")
        return False

    except Exception as e:
        print(f"   [FAIL] Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_proxmox_connection()

    if not success:
        print("\n" + "=" * 60)
        print("[FAILED] CONNECTION TEST FAILED")
        print("=" * 60)
        print("\nPlease resolve the connection issues before proceeding.")
        exit(1)
    else:
        print("\n[OK] You can now proceed to the next step: Installing Proxmoxer library")
        exit(0)