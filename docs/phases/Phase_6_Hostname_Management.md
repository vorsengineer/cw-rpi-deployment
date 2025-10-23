## Phase 6: Hostname Management System

### Step 6.1: Create Database Schema

Create `/opt/rpi-deployment/scripts/database_setup.py`:

```python
#!/usr/bin/env python3
"""
Initialize SQLite database for hostname management
"""

import sqlite3
from pathlib import Path
import logging

DB_PATH = Path("/opt/rpi-deployment/database/deployment.db")

def initialize_database():
    """Create database tables for hostname management"""

    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Hostname pool table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hostname_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_type TEXT NOT NULL CHECK(product_type IN ('KXP2', 'RXP2')),
            venue_code TEXT NOT NULL CHECK(length(venue_code) = 4),
            identifier TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('available', 'assigned', 'retired')),
            mac_address TEXT,
            serial_number TEXT,
            assigned_date TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(product_type, venue_code, identifier)
        )
    ''')

    # Venues table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS venues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL CHECK(length(code) = 4),
            name TEXT NOT NULL,
            location TEXT,
            contact_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Deployment history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deployment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            mac_address TEXT,
            serial_number TEXT,
            ip_address TEXT,
            product_type TEXT,
            venue_code TEXT,
            image_version TEXT,
            deployment_status TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT
        )
    ''')

    # Master images table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            product_type TEXT NOT NULL CHECK(product_type IN ('KXP2', 'RXP2')),
            version TEXT NOT NULL,
            size_bytes INTEGER,
            checksum TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hostname_status ON hostname_pool(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hostname_venue ON hostname_pool(venue_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deployment_date ON deployment_history(started_at)')

    conn.commit()
    conn.close()

    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    initialize_database()
```

### Step 6.2: Hostname Management Functions

Create `/opt/rpi-deployment/scripts/hostname_manager.py`:

```python
#!/usr/bin/env python3
"""
Hostname management functions for KXP/RXP deployment
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

class HostnameManager:
    def __init__(self, db_path="/opt/rpi-deployment/database/deployment.db"):
        self.db_path = db_path
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("HostnameManager")

    def create_venue(self, code: str, name: str, location: str = None, contact_email: str = None):
        """Create a new venue"""
        if len(code) != 4:
            raise ValueError("Venue code must be exactly 4 characters")

        code = code.upper()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO venues (code, name, location, contact_email)
                VALUES (?, ?, ?, ?)
            ''', (code, name, location, contact_email))

        self.logger.info(f"Created venue: {code} - {name}")
        return code

    def bulk_import_kart_numbers(self, venue_code: str, numbers: List[str]):
        """Import a list of kart numbers for a venue"""
        venue_code = venue_code.upper()
        added = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for number in numbers:
                # Format number with leading zeros (e.g., "1" -> "001")
                identifier = f"{int(number):03d}"

                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO hostname_pool
                        (product_type, venue_code, identifier, status)
                        VALUES ('KXP2', ?, ?, 'available')
                    ''', (venue_code, identifier))

                    if cursor.rowcount > 0:
                        added += 1

                except sqlite3.IntegrityError:
                    self.logger.warning(f"Duplicate entry: KXP2-{venue_code}-{identifier}")

        self.logger.info(f"Added {added} kart numbers for venue {venue_code}")
        return added

    def assign_hostname(self, product_type: str, venue_code: str,
                       mac_address: str = None, serial_number: str = None) -> Optional[str]:
        """Assign a hostname to a device"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if product_type == "KXP2":
                # Get next available kart number
                cursor.execute('''
                    SELECT identifier FROM hostname_pool
                    WHERE product_type = 'KXP2'
                    AND venue_code = ?
                    AND status = 'available'
                    ORDER BY identifier
                    LIMIT 1
                ''', (venue_code.upper(),))

                result = cursor.fetchone()
                if result:
                    identifier = result[0]
                    hostname = f"KXP2-{venue_code.upper()}-{identifier}"

                    # Mark as assigned
                    cursor.execute('''
                        UPDATE hostname_pool
                        SET status = 'assigned',
                            mac_address = ?,
                            serial_number = ?,
                            assigned_date = CURRENT_TIMESTAMP
                        WHERE product_type = 'KXP2'
                        AND venue_code = ?
                        AND identifier = ?
                    ''', (mac_address, serial_number, venue_code.upper(), identifier))

                    self.logger.info(f"Assigned hostname: {hostname}")
                    return hostname
                else:
                    self.logger.error(f"No available kart numbers for venue {venue_code}")
                    return None

            elif product_type == "RXP2":
                # Use serial number for RXP2
                if not serial_number:
                    self.logger.error("Serial number required for RXP2 hostname")
                    return None

                # Use last 8 characters of serial
                identifier = serial_number[-8:] if len(serial_number) > 8 else serial_number
                hostname = f"RXP2-{venue_code.upper()}-{identifier}"

                # Record assignment
                cursor.execute('''
                    INSERT OR REPLACE INTO hostname_pool
                    (product_type, venue_code, identifier, status, mac_address,
                     serial_number, assigned_date)
                    VALUES ('RXP2', ?, ?, 'assigned', ?, ?, CURRENT_TIMESTAMP)
                ''', (venue_code.upper(), identifier, mac_address, serial_number))

                self.logger.info(f"Assigned hostname: {hostname}")
                return hostname

            else:
                self.logger.error(f"Invalid product type: {product_type}")
                return None

    def release_hostname(self, hostname: str):
        """Release a hostname back to available pool"""
        parts = hostname.split('-')
        if len(parts) != 3:
            raise ValueError("Invalid hostname format")

        product_type = parts[0]
        venue_code = parts[1]
        identifier = parts[2]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE hostname_pool
                SET status = 'available',
                    mac_address = NULL,
                    serial_number = NULL,
                    assigned_date = NULL
                WHERE product_type = ?
                AND venue_code = ?
                AND identifier = ?
            ''', (product_type, venue_code, identifier))

        self.logger.info(f"Released hostname: {hostname}")

    def get_venue_statistics(self, venue_code: str) -> Dict:
        """Get deployment statistics for a venue"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get hostname pool stats
            cursor.execute('''
                SELECT status, COUNT(*)
                FROM hostname_pool
                WHERE venue_code = ?
                GROUP BY status
            ''', (venue_code.upper(),))

            stats = dict(cursor.fetchall())

            # Get deployment history
            cursor.execute('''
                SELECT COUNT(*), MAX(completed_at)
                FROM deployment_history
                WHERE venue_code = ?
                AND deployment_status = 'success'
            ''', (venue_code.upper(),))

            deployments, last_deployment = cursor.fetchone()

            return {
                'venue_code': venue_code.upper(),
                'available': stats.get('available', 0),
                'assigned': stats.get('assigned', 0),
                'retired': stats.get('retired', 0),
                'total_deployments': deployments or 0,
                'last_deployment': last_deployment
            }
```

---

