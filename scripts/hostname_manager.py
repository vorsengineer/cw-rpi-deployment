#!/usr/bin/env python3
"""
Hostname Manager for Raspberry Pi Deployment System

Manages venue-based hostname assignment for KXP2 and RXP2 devices:

- KXP2 (KartXPro): Pre-loaded pool of kart numbers
  Format: KXP2-{VENUE}-{NUMBER} (e.g., KXP2-CORO-001)
  Assignment: Sequential from available pool

- RXP2 (RaceXPro): Dynamic creation using serial numbers
  Format: RXP2-{VENUE}-{SERIAL} (e.g., RXP2-CORO-ABC12345)
  Assignment: Created on-demand from Pi serial number

All operations are logged and tracked in SQLite database.

Author: Raspberry Pi Deployment System
Date: 2025-10-23
"""

import sqlite3
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HostnameManager:
    """
    Manages hostname assignment and tracking for Raspberry Pi deployments.

    Provides methods for:
    - Creating and managing venues
    - Bulk importing kart numbers for KXP2
    - Assigning hostnames based on product type
    - Releasing hostnames back to available pool
    - Generating venue statistics
    """

    VALID_PRODUCT_TYPES = ['KXP2', 'RXP2']
    VALID_STATUSES = ['available', 'assigned', 'retired']

    def __init__(self, db_path: str = "/opt/rpi-deployment/database/deployment.db"):
        """
        Initialize hostname manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        logger.info(f"HostnameManager initialized with database: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection with row factory.

        Returns:
            sqlite3.Connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _validate_venue_code(self, code: str) -> str:
        """
        Validate and normalize venue code.

        Args:
            code: Venue code to validate

        Returns:
            Normalized (uppercase) venue code

        Raises:
            ValueError: If code is invalid
        """
        if not code:
            raise ValueError("Venue code cannot be empty")

        code = code.upper()

        if len(code) != 4:
            raise ValueError(f"Venue code must be exactly 4 characters, got: {code}")

        if not re.match(r'^[A-Z0-9]{4}$', code):
            raise ValueError(f"Venue code must be alphanumeric only, got: {code}")

        return code

    def _validate_product_type(self, product_type: str) -> str:
        """
        Validate product type.

        Args:
            product_type: Product type to validate

        Returns:
            Validated product type

        Raises:
            ValueError: If product type is invalid
        """
        if product_type not in self.VALID_PRODUCT_TYPES:
            raise ValueError(
                f"Invalid product type '{product_type}'. "
                f"Must be one of: {', '.join(self.VALID_PRODUCT_TYPES)}"
            )
        return product_type

    def create_venue(
        self,
        code: str,
        name: str,
        location: Optional[str] = None,
        contact_email: Optional[str] = None
    ) -> bool:
        """
        Create a new venue.

        Args:
            code: 4-character venue code (will be uppercased)
            name: Venue name
            location: Optional location/address
            contact_email: Optional contact email

        Returns:
            True if successful

        Raises:
            ValueError: If code is invalid
            sqlite3.IntegrityError: If code already exists
        """
        code = self._validate_venue_code(code)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO venues (code, name, location, contact_email)
                    VALUES (?, ?, ?, ?)
                    """,
                    (code, name, location, contact_email)
                )
                conn.commit()

            logger.info(f"Created venue: {code} - {name}")
            return True

        except sqlite3.IntegrityError as e:
            logger.error(f"Failed to create venue {code}: {e}")
            raise

    def _venue_exists(self, venue_code: str) -> bool:
        """
        Check if venue exists.

        Args:
            venue_code: Venue code to check

        Returns:
            True if venue exists, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM venues WHERE code = ?",
                (venue_code,)
            )
            count = cursor.fetchone()[0]
            return count > 0

    def bulk_import_kart_numbers(
        self,
        venue_code: str,
        numbers: List[str],
        product_type: str = 'KXP2'
    ) -> Dict[str, int]:
        """
        Bulk import kart numbers for specified product type (KXP2 or RXP2).

        Numbers are formatted with leading zeros (e.g., "1" becomes "001").
        Duplicate numbers are skipped gracefully.

        Args:
            venue_code: 4-character venue code
            numbers: List of kart numbers (will be formatted)
            product_type: Product type ('KXP2' or 'RXP2'), defaults to 'KXP2'

        Returns:
            Dictionary with:
            - imported: Number of entries successfully imported
            - duplicates: Number of duplicates skipped

        Raises:
            ValueError: If venue doesn't exist or invalid product_type
        """
        # Validate product type
        if product_type not in ('KXP2', 'RXP2'):
            raise ValueError(f"Invalid product_type: {product_type}. Must be 'KXP2' or 'RXP2'")
        venue_code = self._validate_venue_code(venue_code)

        if not self._venue_exists(venue_code):
            raise ValueError(f"Venue does not exist: {venue_code}")

        if not numbers:
            logger.warning(f"No numbers provided for bulk import to {venue_code}")
            return {'imported': 0, 'duplicates': 0}

        imported = 0
        duplicates = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            for number in numbers:
                # Format with leading zeros (minimum 3 digits)
                formatted = f"{int(number):03d}"

                try:
                    cursor.execute(
                        """
                        INSERT INTO hostname_pool
                        (product_type, venue_code, identifier, status)
                        VALUES (?, ?, ?, ?)
                        """,
                        (product_type, venue_code, formatted, 'available')
                    )
                    imported += 1

                except sqlite3.IntegrityError:
                    # Duplicate entry - skip silently
                    logger.debug(f"Skipping duplicate: KXP2-{venue_code}-{formatted}")
                    duplicates += 1
                    continue

            conn.commit()

        logger.info(f"Imported {imported} kart numbers for venue {venue_code} ({duplicates} duplicates skipped)")
        return {'imported': imported, 'duplicates': duplicates}

    def assign_hostname(
        self,
        product_type: str,
        venue_code: str,
        mac_address: Optional[str] = None,
        serial_number: Optional[str] = None
    ) -> Optional[str]:
        """
        Assign a hostname based on product type and venue.

        KXP2: Assigns next available kart number from pre-loaded pool
        RXP2: Creates new entry using last 8 chars of serial number

        Args:
            product_type: 'KXP2' or 'RXP2'
            venue_code: 4-character venue code
            mac_address: Optional MAC address to record
            serial_number: Optional serial number (required for RXP2)

        Returns:
            Assigned hostname (e.g., "KXP2-CORO-001") or None if unavailable

        Raises:
            ValueError: If product type invalid or RXP2 missing serial number
        """
        product_type = self._validate_product_type(product_type)
        venue_code = self._validate_venue_code(venue_code)

        if product_type == 'KXP2':
            return self._assign_kxp2_hostname(venue_code, mac_address, serial_number)
        else:  # RXP2
            return self._assign_rxp2_hostname(venue_code, mac_address, serial_number)

    def _assign_kxp2_hostname(
        self,
        venue_code: str,
        mac_address: Optional[str],
        serial_number: Optional[str]
    ) -> Optional[str]:
        """
        Assign KXP2 hostname from pre-loaded pool.

        Args:
            venue_code: Venue code
            mac_address: MAC address to record
            serial_number: Serial number to record

        Returns:
            Assigned hostname or None if pool exhausted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Find next available hostname (order by identifier for sequential assignment)
            cursor.execute(
                """
                SELECT id, identifier FROM hostname_pool
                WHERE product_type = 'KXP2'
                  AND venue_code = ?
                  AND status = 'available'
                ORDER BY identifier
                LIMIT 1
                """,
                (venue_code,)
            )

            row = cursor.fetchone()

            if not row:
                logger.warning(f"No available KXP2 hostnames for venue {venue_code}")
                return None

            pool_id = row['id']
            identifier = row['identifier']
            hostname = f"KXP2-{venue_code}-{identifier}"

            # Update pool entry
            cursor.execute(
                """
                UPDATE hostname_pool
                SET status = 'assigned',
                    mac_address = ?,
                    serial_number = ?,
                    assigned_date = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (mac_address, serial_number, pool_id)
            )

            conn.commit()

        logger.info(f"Assigned KXP2 hostname: {hostname}")
        return hostname

    def _assign_rxp2_hostname(
        self,
        venue_code: str,
        mac_address: Optional[str],
        serial_number: Optional[str]
    ) -> Optional[str]:
        """
        Assign RXP2 hostname using serial number.

        Creates new pool entry dynamically if it doesn't exist.

        Args:
            venue_code: Venue code
            mac_address: MAC address to record
            serial_number: Serial number (required)

        Returns:
            Assigned hostname

        Raises:
            ValueError: If serial_number is None
        """
        if not serial_number:
            raise ValueError("RXP2 hostname assignment requires serial_number")

        # Use last 8 characters of serial, or full serial if shorter
        identifier = serial_number[-8:].upper() if len(serial_number) >= 8 else serial_number.upper()
        hostname = f"RXP2-{venue_code}-{identifier}"

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if this serial already exists
            cursor.execute(
                """
                SELECT id FROM hostname_pool
                WHERE product_type = 'RXP2'
                  AND venue_code = ?
                  AND identifier = ?
                """,
                (venue_code, identifier)
            )

            existing = cursor.fetchone()

            if existing:
                logger.info(f"RXP2 hostname already exists: {hostname}")
                return hostname

            # Create new pool entry
            cursor.execute(
                """
                INSERT INTO hostname_pool
                (product_type, venue_code, identifier, status, mac_address, serial_number, assigned_date)
                VALUES (?, ?, ?, 'assigned', ?, ?, CURRENT_TIMESTAMP)
                """,
                ('RXP2', venue_code, identifier, mac_address, serial_number)
            )

            conn.commit()

        logger.info(f"Assigned RXP2 hostname: {hostname}")
        return hostname

    def release_hostname(self, hostname: str) -> bool:
        """
        Release hostname back to available pool.

        Clears MAC address, serial number, and changes status to 'available'.

        Args:
            hostname: Full hostname to release (e.g., "KXP2-CORO-001")

        Returns:
            True if released, False if hostname not found
        """
        # Parse hostname
        parts = hostname.split('-')
        if len(parts) != 3:
            logger.error(f"Invalid hostname format: {hostname}")
            return False

        product_type, venue_code, identifier = parts

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE hostname_pool
                SET status = 'available',
                    mac_address = NULL,
                    serial_number = NULL,
                    assigned_date = NULL
                WHERE product_type = ?
                  AND venue_code = ?
                  AND identifier = ?
                """,
                (product_type, venue_code, identifier)
            )

            rows_affected = cursor.rowcount
            conn.commit()

        if rows_affected > 0:
            logger.info(f"Released hostname: {hostname}")
            return True
        else:
            logger.warning(f"Hostname not found: {hostname}")
            return False

    def list_venues(self) -> List[Dict[str, Any]]:
        """
        Get list of all venues with hostname statistics.

        Returns:
            List of dictionaries containing venue information:
            - code: Venue code
            - name: Venue name
            - location: Venue location
            - contact_email: Contact email
            - created_at: Creation timestamp
            - kxp2_available: Number of available KXP2 hostnames
            - kxp2_assigned: Number of assigned KXP2 hostnames
            - rxp2_available: Number of available RXP2 hostnames
            - rxp2_assigned: Number of assigned RXP2 hostnames
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    v.code,
                    v.name,
                    v.location,
                    v.contact_email,
                    v.created_at,
                    COALESCE(SUM(CASE WHEN h.product_type = 'KXP2' AND h.status = 'available' THEN 1 ELSE 0 END), 0) as kxp2_available,
                    COALESCE(SUM(CASE WHEN h.product_type = 'KXP2' AND h.status = 'assigned' THEN 1 ELSE 0 END), 0) as kxp2_assigned,
                    COALESCE(SUM(CASE WHEN h.product_type = 'RXP2' AND h.status = 'available' THEN 1 ELSE 0 END), 0) as rxp2_available,
                    COALESCE(SUM(CASE WHEN h.product_type = 'RXP2' AND h.status = 'assigned' THEN 1 ELSE 0 END), 0) as rxp2_assigned
                FROM venues v
                LEFT JOIN hostname_pool h ON v.code = h.venue_code
                GROUP BY v.code, v.name, v.location, v.contact_email, v.created_at
                ORDER BY v.code
            """)

            venues = []
            for row in cursor.fetchall():
                venues.append({
                    'code': row['code'],
                    'name': row['name'],
                    'location': row['location'],
                    'contact_email': row['contact_email'],
                    'created_at': row['created_at'],
                    'kxp2_available': row['kxp2_available'],
                    'kxp2_assigned': row['kxp2_assigned'],
                    'rxp2_available': row['rxp2_available'],
                    'rxp2_assigned': row['rxp2_assigned']
                })

        return venues

    def get_venue_statistics(self, venue_code: str) -> Dict[str, Any]:
        """
        Get statistics for a venue.

        Args:
            venue_code: 4-character venue code

        Returns:
            Dictionary with counts and venue info:
            - venue_code: Venue code
            - total_hostnames: Total hostnames in pool
            - available_hostnames: Number of available hostnames
            - assigned_hostnames: Number of assigned hostnames
            - retired_hostnames: Number of retired hostnames
        """
        venue_code = self._validate_venue_code(venue_code)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available,
                    SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as assigned,
                    SUM(CASE WHEN status = 'retired' THEN 1 ELSE 0 END) as retired,
                    COUNT(*) as total
                FROM hostname_pool
                WHERE venue_code = ?
                """,
                (venue_code,)
            )

            row = cursor.fetchone()

            if row and row['total'] > 0:
                stats = {
                    'venue_code': venue_code,
                    'total_hostnames': row['total'],
                    'available_hostnames': row['available'] or 0,
                    'assigned_hostnames': row['assigned'] or 0,
                    'retired_hostnames': row['retired'] or 0
                }
            else:
                stats = {
                    'venue_code': venue_code,
                    'total_hostnames': 0,
                    'available_hostnames': 0,
                    'assigned_hostnames': 0,
                    'retired_hostnames': 0
                }

        logger.debug(f"Statistics for {venue_code}: {stats}")
        return stats

    # =============================================================================
    # Batch Management Methods
    # =============================================================================

    def create_deployment_batch(
        self,
        venue_code: str,
        product_type: str,
        total_count: int,
        priority: int = 0
    ) -> int:
        """
        Create a new deployment batch.

        For KXP2: Validates sufficient available hostnames exist in pool
        For RXP2: Creates batch without pool validation (serial-based)

        Args:
            venue_code: 4-character venue code
            product_type: 'KXP2' or 'RXP2'
            total_count: Number of devices to deploy
            priority: Priority level (higher = deployed first)

        Returns:
            batch_id: ID of created batch

        Raises:
            ValueError: If venue invalid, product_type invalid, count <= 0,
                       or insufficient KXP2 hostnames in pool
        """
        # Validate inputs
        if product_type not in ('KXP2', 'RXP2'):
            raise ValueError(f"Invalid product_type: {product_type}. Must be 'KXP2' or 'RXP2'")

        if total_count <= 0:
            raise ValueError(f"total_count must be > 0, got {total_count}")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Verify venue exists
            cursor.execute("SELECT code FROM venues WHERE code = ?", (venue_code,))
            if not cursor.fetchone():
                raise ValueError(f"Venue not found: {venue_code}")

            # For KXP2, verify sufficient available hostnames
            if product_type == 'KXP2':
                cursor.execute(
                    """
                    SELECT COUNT(*) as available
                    FROM hostname_pool
                    WHERE venue_code = ? AND product_type = ? AND status = 'available'
                    """,
                    (venue_code, product_type)
                )
                available = cursor.fetchone()['available']
                if available < total_count:
                    raise ValueError(
                        f"Insufficient available hostnames. Requested: {total_count}, Available: {available}"
                    )

            # Create batch
            cursor.execute(
                """
                INSERT INTO deployment_batches
                (venue_code, product_type, total_count, remaining_count, priority, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (venue_code, product_type, total_count, total_count, priority)
            )

            batch_id = cursor.lastrowid
            logger.info(
                f"Created deployment batch {batch_id}: {product_type} for {venue_code}, "
                f"count={total_count}, priority={priority}"
            )
            return batch_id

    def get_active_batch(self) -> Optional[dict]:
        """
        Get the highest priority active batch.

        Returns:
            Batch dict with highest priority, or None if no active batches
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM deployment_batches
                WHERE status = 'active'
                ORDER BY priority DESC, id ASC
                LIMIT 1
                """
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def assign_from_batch(
        self,
        batch_id: int,
        mac_address: str,
        serial_number: str
    ) -> str:
        """
        Assign a hostname from a deployment batch.

        For KXP2: Assigns next available hostname from pool
        For RXP2: Creates dynamic hostname using serial number

        Args:
            batch_id: ID of batch to assign from
            mac_address: Device MAC address
            serial_number: Device serial number

        Returns:
            Assigned hostname

        Raises:
            ValueError: If batch not found, not active, or no available hostnames
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get batch details
            cursor.execute("SELECT * FROM deployment_batches WHERE id = ?", (batch_id,))
            batch = cursor.fetchone()

            if not batch:
                raise ValueError(f"Batch not found: {batch_id}")

            if batch['status'] != 'active':
                raise ValueError(f"Batch {batch_id} is not active (status: {batch['status']})")

            if batch['remaining_count'] <= 0:
                raise ValueError(f"Batch {batch_id} has no remaining deployments")

            venue_code = batch['venue_code']
            product_type = batch['product_type']

            # Assign hostname based on product type
            if product_type == 'KXP2':
                # Assign from pool
                hostname = self.assign_hostname(
                    product_type=product_type,
                    venue_code=venue_code,
                    mac_address=mac_address,
                    serial_number=serial_number
                )
            else:  # RXP2
                # Create dynamic hostname
                hostname = self.assign_hostname(
                    product_type=product_type,
                    venue_code=venue_code,
                    mac_address=mac_address,
                    serial_number=serial_number
                )

            # Decrement remaining count
            new_remaining = batch['remaining_count'] - 1

            # Mark batch as completed if no more remaining
            if new_remaining == 0:
                cursor.execute(
                    """
                    UPDATE deployment_batches
                    SET remaining_count = ?, status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_remaining, batch_id)
                )
                logger.info(f"Batch {batch_id} completed")
            else:
                cursor.execute(
                    """
                    UPDATE deployment_batches
                    SET remaining_count = ?
                    WHERE id = ?
                    """,
                    (new_remaining, batch_id)
                )

            logger.info(
                f"Assigned hostname {hostname} from batch {batch_id} "
                f"({new_remaining} remaining)"
            )
            return hostname

    def start_batch(self, batch_id: int) -> None:
        """
        Start a pending or paused batch.

        Args:
            batch_id: ID of batch to start

        Raises:
            ValueError: If batch not found or already completed/cancelled
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get batch
            cursor.execute("SELECT * FROM deployment_batches WHERE id = ?", (batch_id,))
            batch = cursor.fetchone()

            if not batch:
                raise ValueError(f"Batch not found: {batch_id}")

            # Check if batch can be started
            if batch['status'] == 'completed':
                raise ValueError(f"Cannot start completed batch {batch_id}")

            if batch['status'] == 'cancelled':
                raise ValueError(f"Cannot start cancelled batch {batch_id}")

            # If already active, no-op
            if batch['status'] == 'active':
                logger.debug(f"Batch {batch_id} already active")
                return

            # Start batch
            cursor.execute(
                """
                UPDATE deployment_batches
                SET status = 'active', started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                WHERE id = ?
                """,
                (batch_id,)
            )

            logger.info(f"Started batch {batch_id}")

    def pause_batch(self, batch_id: int) -> None:
        """
        Pause an active batch.

        Args:
            batch_id: ID of batch to pause

        Raises:
            ValueError: If batch not found or not active
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get batch
            cursor.execute("SELECT * FROM deployment_batches WHERE id = ?", (batch_id,))
            batch = cursor.fetchone()

            if not batch:
                raise ValueError(f"Batch not found: {batch_id}")

            # Check if batch can be paused
            if batch['status'] not in ('active', 'paused'):
                raise ValueError(f"Batch {batch_id} must be active to pause (current status: {batch['status']})")

            # If already paused, no-op
            if batch['status'] == 'paused':
                logger.debug(f"Batch {batch_id} already paused")
                return

            # Pause batch
            cursor.execute(
                "UPDATE deployment_batches SET status = 'paused' WHERE id = ?",
                (batch_id,)
            )

            logger.info(f"Paused batch {batch_id}")

    def update_batch_priority(self, batch_id: int, priority: int) -> None:
        """
        Update batch priority.

        Args:
            batch_id: ID of batch to update
            priority: New priority level

        Raises:
            ValueError: If batch not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Verify batch exists
            cursor.execute("SELECT id FROM deployment_batches WHERE id = ?", (batch_id,))
            if not cursor.fetchone():
                raise ValueError(f"Batch not found: {batch_id}")

            # Update priority
            cursor.execute(
                "UPDATE deployment_batches SET priority = ? WHERE id = ?",
                (priority, batch_id)
            )

            logger.info(f"Updated batch {batch_id} priority to {priority}")

    def get_all_batches(
        self,
        venue_code: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[dict]:
        """
        Get all deployment batches with optional filtering.

        Args:
            venue_code: Filter by venue (optional)
            status: Filter by status (optional)

        Returns:
            List of batch dicts ordered by priority (highest first)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build query with optional filters
            query = "SELECT * FROM deployment_batches WHERE 1=1"
            params = []

            if venue_code:
                query += " AND venue_code = ?"
                params.append(venue_code)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY priority DESC, id ASC"

            cursor.execute(query, params)

            batches = [dict(row) for row in cursor.fetchall()]
            return batches

    def get_batch_by_id(self, batch_id: int) -> Optional[dict]:
        """
        Get a single batch by ID.

        Args:
            batch_id: ID of batch to retrieve

        Returns:
            Batch dict or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM deployment_batches WHERE id = ?", (batch_id,))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None


if __name__ == '__main__':
    """
    Command-line interface for hostname management.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Hostname Manager CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Create venue command
    venue_parser = subparsers.add_parser('create-venue', help='Create a new venue')
    venue_parser.add_argument('code', help='4-character venue code')
    venue_parser.add_argument('name', help='Venue name')
    venue_parser.add_argument('--location', help='Venue location')
    venue_parser.add_argument('--email', help='Contact email')

    # Bulk import command
    import_parser = subparsers.add_parser('import', help='Bulk import kart numbers')
    import_parser.add_argument('venue_code', help='Venue code')
    import_parser.add_argument('numbers', nargs='+', help='Kart numbers')

    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show venue statistics')
    stats_parser.add_argument('venue_code', help='Venue code')

    # Database path for all commands
    parser.add_argument(
        '--db-path',
        default='/opt/rpi-deployment/database/deployment.db',
        help='Path to database file'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        exit(1)

    manager = HostnameManager(args.db_path)

    if args.command == 'create-venue':
        try:
            manager.create_venue(
                args.code,
                args.name,
                args.location,
                args.email
            )
            print(f"Venue created: {args.code}")
        except Exception as e:
            print(f"Error: {e}")
            exit(1)

    elif args.command == 'import':
        try:
            imported = manager.bulk_import_kart_numbers(args.venue_code, args.numbers)
            print(f"Imported {imported} kart numbers for {args.venue_code}")
        except Exception as e:
            print(f"Error: {e}")
            exit(1)

    elif args.command == 'stats':
        try:
            stats = manager.get_venue_statistics(args.venue_code)
            print(f"\nStatistics for {args.venue_code}:")
            print(f"  Available: {stats['available']}")
            print(f"  Assigned:  {stats['assigned']}")
            print(f"  Retired:   {stats['retired']}")
            print(f"  Total:     {stats['total']}")
        except Exception as e:
            print(f"Error: {e}")
            exit(1)
