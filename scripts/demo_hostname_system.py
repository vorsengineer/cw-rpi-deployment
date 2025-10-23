#!/usr/bin/env python3
"""
Demonstration of Hostname Management System

This script demonstrates:
1. Creating venues
2. Bulk importing kart numbers for KXP2
3. Assigning KXP2 hostnames (from pool)
4. Assigning RXP2 hostnames (dynamic)
5. Viewing statistics
6. Releasing and reassigning hostnames

Author: Raspberry Pi Deployment System
Date: 2025-10-23
"""

from hostname_manager import HostnameManager


def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    """Run comprehensive demonstration"""

    # Initialize manager
    manager = HostnameManager()

    print_section("Phase 6: Hostname Management System - Demonstration")

    # 1. Create venues
    print_section("1. Creating Venues")
    venues = [
        ('CORO', 'Corona Karting', 'California', 'contact@corona.com'),
        ('ARIA', 'Aria Speedway', 'Nevada', 'info@aria.com'),
        ('TXMO', 'Texas Motor Speedway', 'Texas', 'racing@txmo.com')
    ]

    for code, name, location, email in venues:
        manager.create_venue(code, name, location, email)
        print(f"✓ Created venue: {code} - {name}")

    # 2. Bulk import kart numbers for KXP2
    print_section("2. Bulk Import Kart Numbers (KXP2)")

    # Corona gets karts 1-10
    karts_coro = [str(i) for i in range(1, 11)]
    imported = manager.bulk_import_kart_numbers('CORO', karts_coro)
    print(f"✓ Imported {imported} kart numbers for CORO")

    # Aria gets karts 1-5
    karts_aria = [str(i) for i in range(1, 6)]
    imported = manager.bulk_import_kart_numbers('ARIA', karts_aria)
    print(f"✓ Imported {imported} kart numbers for ARIA")

    # 3. Assign KXP2 hostnames
    print_section("3. Assigning KXP2 Hostnames (from pool)")

    kxp2_assignments = [
        ('CORO', 'aa:bb:cc:dd:ee:01', '1000000001234567'),
        ('CORO', 'aa:bb:cc:dd:ee:02', '1000000002234567'),
        ('CORO', 'aa:bb:cc:dd:ee:03', '1000000003234567'),
        ('ARIA', 'aa:bb:cc:dd:ee:04', '1000000004234567'),
        ('ARIA', 'aa:bb:cc:dd:ee:05', '1000000005234567'),
    ]

    for venue, mac, serial in kxp2_assignments:
        hostname = manager.assign_hostname('KXP2', venue, mac, serial)
        print(f"✓ Assigned: {hostname} (MAC: {mac})")

    # 4. Assign RXP2 hostnames (dynamic creation)
    print_section("4. Assigning RXP2 Hostnames (dynamic)")

    rxp2_assignments = [
        ('CORO', 'bb:cc:dd:ee:ff:01', '10000000abcdef01'),
        ('CORO', 'bb:cc:dd:ee:ff:02', '10000000abcdef02'),
        ('ARIA', 'bb:cc:dd:ee:ff:03', '10000000xyz12345'),
        ('TXMO', 'bb:cc:dd:ee:ff:04', '10000000qwerty99'),
    ]

    for venue, mac, serial in rxp2_assignments:
        hostname = manager.assign_hostname('RXP2', venue, mac, serial)
        print(f"✓ Assigned: {hostname} (Serial: {serial[-8:].upper()})")

    # 5. Show venue statistics
    print_section("5. Venue Statistics")

    for code, name, _, _ in venues:
        stats = manager.get_venue_statistics(code)
        print(f"{code} ({name}):")
        print(f"  Available: {stats['available']:2d}")
        print(f"  Assigned:  {stats['assigned']:2d}")
        print(f"  Retired:   {stats['retired']:2d}")
        print(f"  Total:     {stats['total']:2d}")
        print()

    # 6. Demonstrate hostname release and reassignment
    print_section("6. Release and Reassign Hostname")

    hostname_to_release = 'KXP2-CORO-001'
    print(f"Releasing hostname: {hostname_to_release}")
    result = manager.release_hostname(hostname_to_release)
    print(f"✓ Released: {result}")

    print(f"\nReassigning to different Pi...")
    new_hostname = manager.assign_hostname(
        'KXP2', 'CORO',
        mac_address='aa:bb:cc:dd:ee:99',
        serial_number='9999999999999999'
    )
    print(f"✓ Reassigned: {new_hostname}")

    # 7. Try to exhaust pool
    print_section("7. Testing Pool Exhaustion")

    print("ARIA has 5 kart numbers in pool, 2 already assigned...")
    print("Assigning remaining 3...")

    for i in range(3):
        hostname = manager.assign_hostname('KXP2', 'ARIA')
        if hostname:
            print(f"  ✓ {hostname}")

    print("\nTrying to assign one more (pool should be empty)...")
    hostname = manager.assign_hostname('KXP2', 'ARIA')
    if hostname is None:
        print("  ✓ Correctly returned None - pool exhausted!")

    # 8. Final statistics
    print_section("8. Final System Statistics")

    total_available = 0
    total_assigned = 0
    total_hostnames = 0

    for code, name, _, _ in venues:
        stats = manager.get_venue_statistics(code)
        total_available += stats['available']
        total_assigned += stats['assigned']
        total_hostnames += stats['total']

    print(f"Total Venues:           3")
    print(f"Total Hostnames:        {total_hostnames}")
    print(f"  Available:            {total_available}")
    print(f"  Assigned:             {total_assigned}")
    print(f"\nDeployments Simulated:  9 (5 KXP2 + 4 RXP2)")

    print_section("Demonstration Complete!")
    print("Database location: /opt/rpi-deployment/database/deployment.db")
    print("Use db_admin.py to view detailed information")
    print()


if __name__ == '__main__':
    main()
