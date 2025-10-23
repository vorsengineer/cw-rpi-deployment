#!/usr/bin/env python3
"""
Database Administration Utility

Provides command-line tools for managing the deployment database:
- View all venues
- View hostname pool status
- View deployment history
- Export reports
- Database health checks

Author: Raspberry Pi Deployment System
Date: 2025-10-23
"""

import sqlite3
import argparse
import sys
from typing import List, Dict
from tabulate import tabulate


class DatabaseAdmin:
    """Database administration utilities"""

    def __init__(self, db_path: str = "/opt/rpi-deployment/database/deployment.db"):
        """
        Initialize database admin.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_venues(self) -> List[Dict]:
        """
        List all venues.

        Returns:
            List of venue dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    v.code,
                    v.name,
                    v.location,
                    v.contact_email,
                    COUNT(hp.id) as total_hostnames,
                    SUM(CASE WHEN hp.status = 'available' THEN 1 ELSE 0 END) as available,
                    SUM(CASE WHEN hp.status = 'assigned' THEN 1 ELSE 0 END) as assigned
                FROM venues v
                LEFT JOIN hostname_pool hp ON v.code = hp.venue_code
                GROUP BY v.code
                ORDER BY v.code
            """)
            return [dict(row) for row in cursor.fetchall()]

    def list_hostname_pool(
        self,
        venue_code: str = None,
        status: str = None,
        product_type: str = None
    ) -> List[Dict]:
        """
        List hostname pool entries.

        Args:
            venue_code: Filter by venue code (optional)
            status: Filter by status (optional)
            product_type: Filter by product type (optional)

        Returns:
            List of hostname pool dictionaries
        """
        query = "SELECT * FROM hostname_pool WHERE 1=1"
        params = []

        if venue_code:
            query += " AND venue_code = ?"
            params.append(venue_code.upper())

        if status:
            query += " AND status = ?"
            params.append(status)

        if product_type:
            query += " AND product_type = ?"
            params.append(product_type.upper())

        query += " ORDER BY venue_code, product_type, identifier"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def list_deployments(self, limit: int = 50) -> List[Dict]:
        """
        List recent deployments.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of deployment dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM deployment_history
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_system_stats(self) -> Dict:
        """
        Get overall system statistics.

        Returns:
            Dictionary with system-wide stats
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Venue count
            cursor.execute("SELECT COUNT(*) as count FROM venues")
            venue_count = cursor.fetchone()['count']

            # Hostname pool stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available,
                    SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as assigned,
                    SUM(CASE WHEN status = 'retired' THEN 1 ELSE 0 END) as retired
                FROM hostname_pool
            """)
            pool_stats = dict(cursor.fetchone())

            # Deployment stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN deployment_status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN deployment_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM deployment_history
            """)
            deployment_stats = dict(cursor.fetchone())

            return {
                'venues': venue_count,
                'hostname_pool': pool_stats,
                'deployments': deployment_stats
            }


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='Database Administration Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--db-path',
        default='/opt/rpi-deployment/database/deployment.db',
        help='Path to database file'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List venues
    subparsers.add_parser('venues', help='List all venues')

    # List hostname pool
    pool_parser = subparsers.add_parser('pool', help='List hostname pool')
    pool_parser.add_argument('--venue', help='Filter by venue code')
    pool_parser.add_argument('--status', choices=['available', 'assigned', 'retired'], help='Filter by status')
    pool_parser.add_argument('--product', choices=['KXP2', 'RXP2'], help='Filter by product type')

    # List deployments
    deploy_parser = subparsers.add_parser('deployments', help='List recent deployments')
    deploy_parser.add_argument('--limit', type=int, default=50, help='Number of records to show')

    # System statistics
    subparsers.add_parser('stats', help='Show system statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    admin = DatabaseAdmin(args.db_path)

    try:
        if args.command == 'venues':
            venues = admin.list_venues()
            if venues:
                print("\nVenues:")
                print(tabulate(
                    venues,
                    headers='keys',
                    tablefmt='grid'
                ))
            else:
                print("No venues found.")

        elif args.command == 'pool':
            pool = admin.list_hostname_pool(
                venue_code=args.venue,
                status=args.status,
                product_type=args.product
            )
            if pool:
                # Select relevant columns for display
                display_data = [
                    {
                        'Product': row['product_type'],
                        'Venue': row['venue_code'],
                        'ID': row['identifier'],
                        'Status': row['status'],
                        'MAC': row['mac_address'] or '-',
                        'Assigned': row['assigned_date'][:10] if row['assigned_date'] else '-'
                    }
                    for row in pool
                ]
                print(f"\nHostname Pool ({len(pool)} entries):")
                print(tabulate(display_data, headers='keys', tablefmt='grid'))
            else:
                print("No hostname pool entries found.")

        elif args.command == 'deployments':
            deployments = admin.list_deployments(limit=args.limit)
            if deployments:
                display_data = [
                    {
                        'Hostname': row['hostname'],
                        'Product': row['product_type'] or '-',
                        'IP': row['ip_address'] or '-',
                        'Status': row['deployment_status'] or '-',
                        'Started': row['started_at'][:19] if row['started_at'] else '-',
                        'Completed': row['completed_at'][:19] if row['completed_at'] else '-'
                    }
                    for row in deployments
                ]
                print(f"\nRecent Deployments (last {len(deployments)}):")
                print(tabulate(display_data, headers='keys', tablefmt='grid'))
            else:
                print("No deployment history found.")

        elif args.command == 'stats':
            stats = admin.get_system_stats()
            print("\n=== System Statistics ===\n")
            print(f"Venues: {stats['venues']}")
            print(f"\nHostname Pool:")
            print(f"  Total:     {stats['hostname_pool']['total']}")
            print(f"  Available: {stats['hostname_pool']['available']}")
            print(f"  Assigned:  {stats['hostname_pool']['assigned']}")
            print(f"  Retired:   {stats['hostname_pool']['retired']}")
            print(f"\nDeployments:")
            print(f"  Total:      {stats['deployments']['total']}")
            print(f"  Successful: {stats['deployments']['successful']}")
            print(f"  Failed:     {stats['deployments']['failed']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
