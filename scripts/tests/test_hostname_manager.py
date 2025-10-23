#!/usr/bin/env python3
"""
Unit tests for Hostname Management System

Tests are organized by functionality:
1. Database schema creation and validation
2. Venue management
3. Hostname assignment (KXP2 and RXP2)
4. Hostname release
5. Statistics and reporting
6. Edge cases and error handling

Following TDD principles: Tests written BEFORE implementation.
"""

import unittest
import sqlite3
import os
import tempfile
from datetime import datetime
from typing import Optional
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseSetup(unittest.TestCase):
    """Test database schema creation and validation"""

    def setUp(self):
        """Create temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

    def tearDown(self):
        """Remove temporary database after each test"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_database_creation(self):
        """Test that database file is created"""
        from database_setup import initialize_database

        initialize_database(self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

    def test_hostname_pool_table_exists(self):
        """Test hostname_pool table is created with correct schema"""
        from database_setup import initialize_database

        initialize_database(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='hostname_pool'"
        )
        self.assertIsNotNone(cursor.fetchone())

        # Check columns
        cursor.execute("PRAGMA table_info(hostname_pool)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        expected_columns = {
            'id': 'INTEGER',
            'product_type': 'TEXT',
            'venue_code': 'TEXT',
            'identifier': 'TEXT',
            'status': 'TEXT',
            'mac_address': 'TEXT',
            'serial_number': 'TEXT',
            'assigned_date': 'TIMESTAMP',
            'notes': 'TEXT',
            'created_at': 'TIMESTAMP'
        }

        for col, col_type in expected_columns.items():
            self.assertIn(col, columns)
            self.assertEqual(columns[col], col_type)

        conn.close()

    def test_venues_table_exists(self):
        """Test venues table is created with correct schema"""
        from database_setup import initialize_database

        initialize_database(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='venues'"
        )
        self.assertIsNotNone(cursor.fetchone())

        cursor.execute("PRAGMA table_info(venues)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        self.assertIn('code', columns)
        self.assertIn('name', columns)
        self.assertIn('location', columns)
        self.assertIn('contact_email', columns)

        conn.close()

    def test_deployment_history_table_exists(self):
        """Test deployment_history table is created"""
        from database_setup import initialize_database

        initialize_database(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='deployment_history'"
        )
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_master_images_table_exists(self):
        """Test master_images table is created"""
        from database_setup import initialize_database

        initialize_database(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='master_images'"
        )
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_indexes_created(self):
        """Test that required indexes are created"""
        from database_setup import initialize_database

        initialize_database(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        # Check our custom indexes (SQLite creates auto indexes for UNIQUE constraints)
        self.assertIn('idx_hostname_status', indexes)
        self.assertIn('idx_hostname_venue', indexes)
        self.assertIn('idx_deployment_date', indexes)

        conn.close()

    def test_unique_constraint_hostname_pool(self):
        """Test UNIQUE constraint on (product_type, venue_code, identifier)"""
        from database_setup import initialize_database

        initialize_database(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert first record
        cursor.execute(
            "INSERT INTO hostname_pool (product_type, venue_code, identifier, status) "
            "VALUES ('KXP2', 'CORO', '001', 'available')"
        )

        # Try to insert duplicate - should fail
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO hostname_pool (product_type, venue_code, identifier, status) "
                "VALUES ('KXP2', 'CORO', '001', 'available')"
            )

        conn.close()


class TestVenueManagement(unittest.TestCase):
    """Test venue creation and management"""

    def setUp(self):
        """Create temporary database and initialize manager"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        from database_setup import initialize_database
        initialize_database(self.db_path)

        from hostname_manager import HostnameManager
        self.manager = HostnameManager(self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_create_venue_valid(self):
        """Test creating a venue with valid 4-character code"""
        result = self.manager.create_venue(
            code='CORO',
            name='Corona Karting',
            location='California',
            contact_email='contact@corona.com'
        )
        self.assertTrue(result)

    def test_create_venue_code_too_short(self):
        """Test that venue code must be exactly 4 characters"""
        with self.assertRaises(ValueError):
            self.manager.create_venue(code='COR', name='Corona')

    def test_create_venue_code_too_long(self):
        """Test that venue code cannot be longer than 4 characters"""
        with self.assertRaises(ValueError):
            self.manager.create_venue(code='CORON', name='Corona')

    def test_create_venue_code_lowercase(self):
        """Test that venue code is automatically converted to uppercase"""
        self.manager.create_venue(code='coro', name='Corona')

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM venues WHERE name='Corona'")
        code = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(code, 'CORO')

    def test_create_venue_duplicate_code(self):
        """Test that duplicate venue codes are rejected"""
        self.manager.create_venue(code='CORO', name='Corona')

        # Second venue with same code should fail
        with self.assertRaises(sqlite3.IntegrityError):
            self.manager.create_venue(code='CORO', name='Another Venue')

    def test_create_venue_minimal_data(self):
        """Test creating venue with only required fields"""
        result = self.manager.create_venue(code='TEST', name='Test Venue')
        self.assertTrue(result)


class TestBulkImport(unittest.TestCase):
    """Test bulk import of kart numbers for KXP2"""

    def setUp(self):
        """Create temporary database and initialize manager"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        from database_setup import initialize_database
        initialize_database(self.db_path)

        from hostname_manager import HostnameManager
        self.manager = HostnameManager(self.db_path)

        # Create test venue
        self.manager.create_venue(code='CORO', name='Corona Karting')

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_bulk_import_success(self):
        """Test bulk importing kart numbers"""
        numbers = ['001', '002', '003', '004', '005']
        imported = self.manager.bulk_import_kart_numbers('CORO', numbers)

        self.assertEqual(imported, 5)

    def test_bulk_import_formats_numbers(self):
        """Test that numbers are formatted with leading zeros"""
        numbers = ['1', '2', '10', '100']
        self.manager.bulk_import_kart_numbers('CORO', numbers)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT identifier FROM hostname_pool WHERE venue_code='CORO' ORDER BY identifier"
        )
        identifiers = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.assertEqual(identifiers, ['001', '002', '010', '100'])

    def test_bulk_import_skips_duplicates(self):
        """Test that duplicate numbers are skipped gracefully"""
        # First import
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002'])

        # Second import with some duplicates
        imported = self.manager.bulk_import_kart_numbers('CORO', ['002', '003', '004'])

        # Should only import the new ones (003, 004)
        self.assertEqual(imported, 2)

    def test_bulk_import_nonexistent_venue(self):
        """Test importing for nonexistent venue raises error"""
        with self.assertRaises(ValueError):
            self.manager.bulk_import_kart_numbers('FAKE', ['001'])

    def test_bulk_import_creates_available_status(self):
        """Test that imported hostnames have 'available' status"""
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002'])

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM hostname_pool WHERE venue_code='CORO'"
        )
        statuses = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.assertTrue(all(status == 'available' for status in statuses))


class TestKXP2HostnameAssignment(unittest.TestCase):
    """Test KXP2 hostname assignment from pre-loaded pool"""

    def setUp(self):
        """Create temporary database and initialize manager"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        from database_setup import initialize_database
        initialize_database(self.db_path)

        from hostname_manager import HostnameManager
        self.manager = HostnameManager(self.db_path)

        # Create venue and import kart numbers
        self.manager.create_venue(code='CORO', name='Corona Karting')
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002', '003'])

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_assign_kxp2_hostname_format(self):
        """Test KXP2 hostname follows format KXP2-VENUE-NUMBER"""
        hostname = self.manager.assign_hostname(
            product_type='KXP2',
            venue_code='CORO',
            mac_address='aa:bb:cc:dd:ee:ff',
            serial_number='1234567890abcdef'
        )

        self.assertIsNotNone(hostname)
        self.assertTrue(hostname.startswith('KXP2-CORO-'))
        self.assertIn(hostname, ['KXP2-CORO-001', 'KXP2-CORO-002', 'KXP2-CORO-003'])

    def test_assign_kxp2_sequential_assignment(self):
        """Test KXP2 hostnames are assigned sequentially"""
        hostname1 = self.manager.assign_hostname('KXP2', 'CORO')
        hostname2 = self.manager.assign_hostname('KXP2', 'CORO')
        hostname3 = self.manager.assign_hostname('KXP2', 'CORO')

        self.assertEqual(hostname1, 'KXP2-CORO-001')
        self.assertEqual(hostname2, 'KXP2-CORO-002')
        self.assertEqual(hostname3, 'KXP2-CORO-003')

    def test_assign_kxp2_records_mac_address(self):
        """Test that MAC address is recorded during assignment"""
        mac = 'aa:bb:cc:dd:ee:ff'
        hostname = self.manager.assign_hostname('KXP2', 'CORO', mac_address=mac)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT mac_address FROM hostname_pool WHERE "
            "product_type='KXP2' AND venue_code='CORO' AND identifier='001'"
        )
        stored_mac = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(stored_mac, mac)

    def test_assign_kxp2_updates_status_to_assigned(self):
        """Test that status changes from 'available' to 'assigned'"""
        hostname = self.manager.assign_hostname('KXP2', 'CORO')

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM hostname_pool WHERE "
            "product_type='KXP2' AND venue_code='CORO' AND identifier='001'"
        )
        status = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(status, 'assigned')

    def test_assign_kxp2_records_timestamp(self):
        """Test that assigned_date is recorded"""
        hostname = self.manager.assign_hostname('KXP2', 'CORO')

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT assigned_date FROM hostname_pool WHERE "
            "product_type='KXP2' AND venue_code='CORO' AND identifier='001'"
        )
        assigned_date = cursor.fetchone()[0]
        conn.close()

        self.assertIsNotNone(assigned_date)

    def test_assign_kxp2_empty_pool(self):
        """Test assignment returns None when pool is exhausted"""
        # Assign all available hostnames
        self.manager.assign_hostname('KXP2', 'CORO')
        self.manager.assign_hostname('KXP2', 'CORO')
        self.manager.assign_hostname('KXP2', 'CORO')

        # Try to assign when pool is empty
        hostname = self.manager.assign_hostname('KXP2', 'CORO')
        self.assertIsNone(hostname)

    def test_assign_kxp2_nonexistent_venue(self):
        """Test assignment for nonexistent venue returns None"""
        hostname = self.manager.assign_hostname('KXP2', 'FAKE')
        self.assertIsNone(hostname)


class TestRXP2HostnameAssignment(unittest.TestCase):
    """Test RXP2 hostname assignment using serial numbers"""

    def setUp(self):
        """Create temporary database and initialize manager"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        from database_setup import initialize_database
        initialize_database(self.db_path)

        from hostname_manager import HostnameManager
        self.manager = HostnameManager(self.db_path)

        # Create venue (no kart numbers needed for RXP2)
        self.manager.create_venue(code='ARIA', name='Aria Speedway')

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_assign_rxp2_hostname_format(self):
        """Test RXP2 hostname follows format RXP2-VENUE-SERIAL"""
        serial = '1234567890abcdef'
        hostname = self.manager.assign_hostname(
            product_type='RXP2',
            venue_code='ARIA',
            serial_number=serial
        )

        # Should use last 8 characters of serial
        self.assertEqual(hostname, 'RXP2-ARIA-90ABCDEF')

    def test_assign_rxp2_creates_pool_entry(self):
        """Test RXP2 assignment creates new pool entry dynamically"""
        serial = '1234567890abcdef'
        hostname = self.manager.assign_hostname('RXP2', 'ARIA', serial_number=serial)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM hostname_pool WHERE "
            "product_type='RXP2' AND venue_code='ARIA' AND identifier='90ABCDEF'"
        )
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)

    def test_assign_rxp2_requires_serial_number(self):
        """Test RXP2 assignment requires serial number"""
        with self.assertRaises(ValueError):
            self.manager.assign_hostname('RXP2', 'ARIA', serial_number=None)

    def test_assign_rxp2_handles_short_serial(self):
        """Test RXP2 with serial shorter than 8 characters"""
        serial = 'ABC123'
        hostname = self.manager.assign_hostname('RXP2', 'ARIA', serial_number=serial)

        self.assertEqual(hostname, 'RXP2-ARIA-ABC123')

    def test_assign_rxp2_uppercases_serial(self):
        """Test RXP2 serial number is uppercased"""
        serial = 'abcdef1234567890'
        hostname = self.manager.assign_hostname('RXP2', 'ARIA', serial_number=serial)

        self.assertEqual(hostname, 'RXP2-ARIA-34567890')

    def test_assign_rxp2_duplicate_serial(self):
        """Test assigning same serial number twice returns existing hostname"""
        serial = '1234567890abcdef'

        hostname1 = self.manager.assign_hostname('RXP2', 'ARIA', serial_number=serial)
        hostname2 = self.manager.assign_hostname('RXP2', 'ARIA', serial_number=serial)

        self.assertEqual(hostname1, hostname2)


class TestHostnameRelease(unittest.TestCase):
    """Test releasing hostnames back to available pool"""

    def setUp(self):
        """Create temporary database and initialize manager"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        from database_setup import initialize_database
        initialize_database(self.db_path)

        from hostname_manager import HostnameManager
        self.manager = HostnameManager(self.db_path)

        # Create venue and assign hostname
        self.manager.create_venue(code='CORO', name='Corona')
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002'])
        self.assigned_hostname = self.manager.assign_hostname('KXP2', 'CORO')

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_release_hostname_success(self):
        """Test releasing assigned hostname"""
        result = self.manager.release_hostname(self.assigned_hostname)
        self.assertTrue(result)

    def test_release_hostname_status_changes(self):
        """Test status changes to 'available' after release"""
        self.manager.release_hostname(self.assigned_hostname)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM hostname_pool WHERE "
            "product_type='KXP2' AND venue_code='CORO' AND identifier='001'"
        )
        status = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(status, 'available')

    def test_release_hostname_clears_mac_address(self):
        """Test MAC address is cleared after release"""
        self.manager.release_hostname(self.assigned_hostname)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT mac_address FROM hostname_pool WHERE "
            "product_type='KXP2' AND venue_code='CORO' AND identifier='001'"
        )
        mac = cursor.fetchone()[0]
        conn.close()

        self.assertIsNone(mac)

    def test_release_hostname_clears_serial_number(self):
        """Test serial number is cleared after release"""
        self.manager.release_hostname(self.assigned_hostname)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT serial_number FROM hostname_pool WHERE "
            "product_type='KXP2' AND venue_code='CORO' AND identifier='001'"
        )
        serial = cursor.fetchone()[0]
        conn.close()

        self.assertIsNone(serial)

    def test_release_hostname_allows_reassignment(self):
        """Test hostname can be reassigned after release"""
        # Release first assignment
        self.manager.release_hostname(self.assigned_hostname)

        # Should be able to assign again
        new_hostname = self.manager.assign_hostname('KXP2', 'CORO')
        self.assertEqual(new_hostname, self.assigned_hostname)

    def test_release_nonexistent_hostname(self):
        """Test releasing nonexistent hostname returns False"""
        result = self.manager.release_hostname('KXP2-FAKE-999')
        self.assertFalse(result)


class TestVenueStatistics(unittest.TestCase):
    """Test venue statistics reporting"""

    def setUp(self):
        """Create temporary database and initialize manager"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        from database_setup import initialize_database
        initialize_database(self.db_path)

        from hostname_manager import HostnameManager
        self.manager = HostnameManager(self.db_path)

        # Set up test data
        self.manager.create_venue(code='CORO', name='Corona')
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002', '003', '004', '005'])

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_venue_statistics_all_available(self):
        """Test statistics when all hostnames are available"""
        stats = self.manager.get_venue_statistics('CORO')

        self.assertEqual(stats['available'], 5)
        self.assertEqual(stats['assigned'], 0)
        self.assertEqual(stats['retired'], 0)
        self.assertEqual(stats['total'], 5)

    def test_venue_statistics_mixed_status(self):
        """Test statistics with mixed status hostnames"""
        # Assign some hostnames
        self.manager.assign_hostname('KXP2', 'CORO')
        self.manager.assign_hostname('KXP2', 'CORO')

        # Retire one directly in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE hostname_pool SET status='retired' WHERE identifier='005'"
        )
        conn.commit()
        conn.close()

        stats = self.manager.get_venue_statistics('CORO')

        self.assertEqual(stats['available'], 2)
        self.assertEqual(stats['assigned'], 2)
        self.assertEqual(stats['retired'], 1)
        self.assertEqual(stats['total'], 5)

    def test_venue_statistics_nonexistent_venue(self):
        """Test statistics for nonexistent venue"""
        stats = self.manager.get_venue_statistics('FAKE')

        self.assertEqual(stats['available'], 0)
        self.assertEqual(stats['assigned'], 0)
        self.assertEqual(stats['retired'], 0)
        self.assertEqual(stats['total'], 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        """Create temporary database and initialize manager"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        from database_setup import initialize_database
        initialize_database(self.db_path)

        from hostname_manager import HostnameManager
        self.manager = HostnameManager(self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_invalid_product_type(self):
        """Test assignment with invalid product type"""
        self.manager.create_venue(code='TEST', name='Test')

        with self.assertRaises(ValueError):
            self.manager.assign_hostname('INVALID', 'TEST')

    def test_empty_venue_code(self):
        """Test creating venue with empty code"""
        with self.assertRaises(ValueError):
            self.manager.create_venue(code='', name='Test')

    def test_special_characters_in_venue_code(self):
        """Test venue code with special characters is rejected"""
        # Venue codes should be alphanumeric only
        with self.assertRaises(ValueError):
            self.manager.create_venue(code='CO-O', name='Test')

    def test_bulk_import_empty_list(self):
        """Test bulk import with empty list"""
        self.manager.create_venue(code='TEST', name='Test')
        imported = self.manager.bulk_import_kart_numbers('TEST', [])

        self.assertEqual(imported, 0)

    def test_concurrent_assignment_same_hostname(self):
        """Test that same hostname cannot be assigned twice simultaneously"""
        self.manager.create_venue(code='TEST', name='Test')
        self.manager.bulk_import_kart_numbers('TEST', ['001'])

        # First assignment
        hostname1 = self.manager.assign_hostname('KXP2', 'TEST')

        # Second assignment should get None (pool exhausted)
        hostname2 = self.manager.assign_hostname('KXP2', 'TEST')

        self.assertIsNotNone(hostname1)
        self.assertIsNone(hostname2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
