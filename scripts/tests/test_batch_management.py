#!/usr/bin/env python3
"""
Unit Tests for Batch Management Methods

Tests all batch-related methods in the HostnameManager class following TDD principles.
Tests are written before implementation to define expected behavior.

Author: Raspberry Pi Deployment System
Date: 2025-10-23
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import datetime
import sys

# Add parent directory to path to import hostname_manager
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hostname_manager import HostnameManager
from database_setup import initialize_database


class TestBatchManagement(unittest.TestCase):
    """Test cases for deployment batch management functionality."""

    def setUp(self):
        """Create temporary database for each test."""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        initialize_database(self.test_db_path)
        self.manager = HostnameManager(self.test_db_path)

        # Create test venues
        self.manager.create_venue('CORO', 'Corona Test', 'CA', 'test@corona.com')
        self.manager.create_venue('ARIA', 'Aria Test', 'NV', 'test@aria.com')

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    # ===========================================
    # Test: create_deployment_batch()
    # ===========================================

    def test_create_kxp2_batch_from_pool(self):
        """Test creating a KXP2 batch from existing pool."""
        # Import kart numbers first
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002', '003'], product_type='KXP2')

        # Create batch
        batch_id = self.manager.create_deployment_batch(
            venue_code='CORO',
            product_type='KXP2',
            total_count=3,
            priority=0
        )

        # Verify batch created
        self.assertIsNotNone(batch_id)
        self.assertIsInstance(batch_id, int)

        # Verify batch details
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['venue_code'], 'CORO')
        self.assertEqual(batch['product_type'], 'KXP2')
        self.assertEqual(batch['total_count'], 3)
        self.assertEqual(batch['remaining_count'], 3)
        self.assertEqual(batch['priority'], 0)
        self.assertEqual(batch['status'], 'pending')

    def test_create_rxp2_batch_quantity_only(self):
        """Test creating an RXP2 batch with quantity only (no pool needed)."""
        # Create RXP2 batch without importing numbers
        batch_id = self.manager.create_deployment_batch(
            venue_code='ARIA',
            product_type='RXP2',
            total_count=10,
            priority=1
        )

        # Verify batch created
        self.assertIsNotNone(batch_id)

        # Verify batch details
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['venue_code'], 'ARIA')
        self.assertEqual(batch['product_type'], 'RXP2')
        self.assertEqual(batch['total_count'], 10)
        self.assertEqual(batch['remaining_count'], 10)
        self.assertEqual(batch['priority'], 1)

    def test_create_kxp2_batch_insufficient_pool(self):
        """Test creating KXP2 batch fails if pool has insufficient hostnames."""
        # Import only 2 kart numbers
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002'], product_type='KXP2')

        # Try to create batch for 5
        with self.assertRaises(ValueError) as context:
            self.manager.create_deployment_batch(
                venue_code='CORO',
                product_type='KXP2',
                total_count=5,
                priority=0
            )

        self.assertIn('Insufficient available hostnames', str(context.exception))

    def test_create_batch_invalid_venue(self):
        """Test creating batch with invalid venue fails."""
        with self.assertRaises(ValueError) as context:
            self.manager.create_deployment_batch(
                venue_code='INVALID',
                product_type='KXP2',
                total_count=5,
                priority=0
            )

        self.assertIn('Venue', str(context.exception))

    def test_create_batch_invalid_product_type(self):
        """Test creating batch with invalid product type fails."""
        with self.assertRaises(ValueError) as context:
            self.manager.create_deployment_batch(
                venue_code='CORO',
                product_type='INVALID',
                total_count=5,
                priority=0
            )

        self.assertIn('product_type', str(context.exception))

    def test_create_batch_invalid_count(self):
        """Test creating batch with zero or negative count fails."""
        with self.assertRaises(ValueError) as context:
            self.manager.create_deployment_batch(
                venue_code='CORO',
                product_type='RXP2',
                total_count=0,
                priority=0
            )

        self.assertIn('total_count', str(context.exception))

    # ===========================================
    # Test: get_active_batch()
    # ===========================================

    def test_get_active_batch_returns_highest_priority(self):
        """Test that get_active_batch returns the highest priority active batch."""
        # Create multiple batches with different priorities
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002', '003'], product_type='KXP2')
        self.manager.bulk_import_kart_numbers('ARIA', ['001', '002'], product_type='KXP2')

        batch1_id = self.manager.create_deployment_batch('CORO', 'KXP2', 3, priority=5)
        batch2_id = self.manager.create_deployment_batch('ARIA', 'KXP2', 2, priority=10)  # Higher
        batch3_id = self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=3)

        # Start batches
        self.manager.start_batch(batch1_id)
        self.manager.start_batch(batch2_id)
        self.manager.start_batch(batch3_id)

        # Get active batch
        active_batch = self.manager.get_active_batch()

        # Should return batch2 (priority 10)
        self.assertIsNotNone(active_batch)
        self.assertEqual(active_batch['id'], batch2_id)
        self.assertEqual(active_batch['priority'], 10)

    def test_get_active_batch_no_active_batches(self):
        """Test get_active_batch returns None when no active batches exist."""
        # Create pending batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)

        # Get active batch (should be None)
        active_batch = self.manager.get_active_batch()
        self.assertIsNone(active_batch)

    def test_get_active_batch_ignores_paused_and_completed(self):
        """Test that get_active_batch ignores paused and completed batches."""
        # Create and start batches
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002'], product_type='KXP2')
        batch1_id = self.manager.create_deployment_batch('CORO', 'KXP2', 2, priority=5)
        self.manager.start_batch(batch1_id)

        # Pause the batch
        self.manager.pause_batch(batch1_id)

        # Get active batch (should be None since only batch is paused)
        active_batch = self.manager.get_active_batch()
        self.assertIsNone(active_batch)

    # ===========================================
    # Test: assign_from_batch()
    # ===========================================

    def test_assign_from_kxp2_batch(self):
        """Test assigning hostname from KXP2 batch."""
        # Create KXP2 batch
        self.manager.bulk_import_kart_numbers('CORO', ['001', '002'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 2, priority=0)
        self.manager.start_batch(batch_id)

        # Assign from batch
        hostname = self.manager.assign_from_batch(
            batch_id=batch_id,
            mac_address='AA:BB:CC:DD:EE:01',
            serial_number='SN001'
        )

        # Verify hostname assigned
        self.assertIsNotNone(hostname)
        self.assertTrue(hostname.startswith('KXP2-CORO-'))

        # Verify batch count decremented
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['remaining_count'], 1)

    def test_assign_from_rxp2_batch_creates_dynamic_hostname(self):
        """Test assigning hostname from RXP2 batch creates dynamic hostname."""
        # Create RXP2 batch
        batch_id = self.manager.create_deployment_batch('ARIA', 'RXP2', 5, priority=0)
        self.manager.start_batch(batch_id)

        # Assign from batch
        hostname = self.manager.assign_from_batch(
            batch_id=batch_id,
            mac_address='AA:BB:CC:DD:EE:02',
            serial_number='ABC12345'
        )

        # Verify hostname format
        self.assertIsNotNone(hostname)
        self.assertEqual(hostname, 'RXP2-ARIA-ABC12345')

        # Verify batch count decremented
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['remaining_count'], 4)

    def test_assign_from_batch_completes_when_empty(self):
        """Test that batch is marked completed when remaining_count reaches 0."""
        # Create small batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)
        self.manager.start_batch(batch_id)

        # Assign the only hostname
        self.manager.assign_from_batch(
            batch_id=batch_id,
            mac_address='AA:BB:CC:DD:EE:03',
            serial_number='SN003'
        )

        # Verify batch is completed
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['status'], 'completed')
        self.assertEqual(batch['remaining_count'], 0)
        self.assertIsNotNone(batch['completed_at'])

    def test_assign_from_inactive_batch_fails(self):
        """Test that assigning from non-active batch fails."""
        # Create pending batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)

        # Try to assign from pending batch
        with self.assertRaises(ValueError) as context:
            self.manager.assign_from_batch(
                batch_id=batch_id,
                mac_address='AA:BB:CC:DD:EE:04',
                serial_number='SN004'
            )

        self.assertIn('active', str(context.exception).lower())

    def test_assign_from_nonexistent_batch_fails(self):
        """Test that assigning from non-existent batch fails."""
        with self.assertRaises(ValueError) as context:
            self.manager.assign_from_batch(
                batch_id=99999,
                mac_address='AA:BB:CC:DD:EE:05',
                serial_number='SN005'
            )

        self.assertIn('Batch', str(context.exception))

    # ===========================================
    # Test: start_batch()
    # ===========================================

    def test_start_pending_batch(self):
        """Test starting a pending batch."""
        # Create pending batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)

        # Start batch
        self.manager.start_batch(batch_id)

        # Verify status changed
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['status'], 'active')
        self.assertIsNotNone(batch['started_at'])

    def test_start_already_active_batch_no_error(self):
        """Test starting already active batch is idempotent."""
        # Create and start batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)
        self.manager.start_batch(batch_id)

        # Start again (should not error)
        self.manager.start_batch(batch_id)

        # Verify still active
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['status'], 'active')

    def test_start_completed_batch_fails(self):
        """Test that starting a completed batch fails."""
        # Create, start, and complete batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)
        self.manager.start_batch(batch_id)
        self.manager.assign_from_batch(batch_id, 'AA:BB:CC:DD:EE:06', 'SN006')

        # Try to start completed batch
        with self.assertRaises(ValueError) as context:
            self.manager.start_batch(batch_id)

        self.assertIn('completed', str(context.exception).lower())

    def test_start_nonexistent_batch_fails(self):
        """Test that starting non-existent batch fails."""
        with self.assertRaises(ValueError) as context:
            self.manager.start_batch(99999)

        self.assertIn('Batch', str(context.exception))

    # ===========================================
    # Test: pause_batch()
    # ===========================================

    def test_pause_active_batch(self):
        """Test pausing an active batch."""
        # Create and start batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)
        self.manager.start_batch(batch_id)

        # Pause batch
        self.manager.pause_batch(batch_id)

        # Verify status changed
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['status'], 'paused')

    def test_pause_already_paused_batch_no_error(self):
        """Test pausing already paused batch is idempotent."""
        # Create, start, and pause batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)
        self.manager.start_batch(batch_id)
        self.manager.pause_batch(batch_id)

        # Pause again (should not error)
        self.manager.pause_batch(batch_id)

        # Verify still paused
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['status'], 'paused')

    def test_pause_pending_batch_fails(self):
        """Test that pausing a pending batch fails."""
        # Create pending batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)

        # Try to pause pending batch
        with self.assertRaises(ValueError) as context:
            self.manager.pause_batch(batch_id)

        self.assertIn('active', str(context.exception).lower())

    def test_resume_paused_batch(self):
        """Test resuming a paused batch by starting it again."""
        # Create, start, and pause batch
        self.manager.bulk_import_kart_numbers('CORO', ['001'], product_type='KXP2')
        batch_id = self.manager.create_deployment_batch('CORO', 'KXP2', 1, priority=0)
        self.manager.start_batch(batch_id)
        self.manager.pause_batch(batch_id)

        # Resume by starting again
        self.manager.start_batch(batch_id)

        # Verify status changed
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['status'], 'active')

    # ===========================================
    # Test: update_batch_priority()
    # ===========================================

    def test_update_batch_priority(self):
        """Test updating batch priority."""
        # Create batch with priority 0
        batch_id = self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=0)

        # Update priority to 10
        self.manager.update_batch_priority(batch_id, 10)

        # Verify priority changed
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['priority'], 10)

    def test_update_batch_priority_negative(self):
        """Test updating batch priority to negative value."""
        # Create batch
        batch_id = self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=0)

        # Update to negative priority (lower priority)
        self.manager.update_batch_priority(batch_id, -5)

        # Verify priority changed
        batch = self.manager.get_batch_by_id(batch_id)
        self.assertEqual(batch['priority'], -5)

    def test_update_priority_affects_active_batch_order(self):
        """Test that updating priority affects which batch is returned by get_active_batch."""
        # Create two batches
        batch1_id = self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=5)
        batch2_id = self.manager.create_deployment_batch('ARIA', 'RXP2', 3, priority=3)

        # Start both
        self.manager.start_batch(batch1_id)
        self.manager.start_batch(batch2_id)

        # Verify batch1 is active (higher priority)
        active = self.manager.get_active_batch()
        self.assertEqual(active['id'], batch1_id)

        # Update batch2 to higher priority
        self.manager.update_batch_priority(batch2_id, 10)

        # Verify batch2 is now active
        active = self.manager.get_active_batch()
        self.assertEqual(active['id'], batch2_id)

    def test_update_priority_nonexistent_batch_fails(self):
        """Test that updating priority of non-existent batch fails."""
        with self.assertRaises(ValueError) as context:
            self.manager.update_batch_priority(99999, 5)

        self.assertIn('Batch', str(context.exception))

    # ===========================================
    # Test: get_all_batches()
    # ===========================================

    def test_get_all_batches_no_filter(self):
        """Test getting all batches without filter."""
        # Create multiple batches
        self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=0)
        self.manager.create_deployment_batch('ARIA', 'RXP2', 3, priority=1)

        # Get all batches
        batches = self.manager.get_all_batches()

        # Verify count
        self.assertEqual(len(batches), 2)

    def test_get_all_batches_filter_by_venue(self):
        """Test getting batches filtered by venue."""
        # Create batches for different venues
        self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=0)
        self.manager.create_deployment_batch('ARIA', 'RXP2', 3, priority=1)
        self.manager.create_deployment_batch('CORO', 'RXP2', 2, priority=2)

        # Get CORO batches
        batches = self.manager.get_all_batches(venue_code='CORO')

        # Verify count and venue
        self.assertEqual(len(batches), 2)
        for batch in batches:
            self.assertEqual(batch['venue_code'], 'CORO')

    def test_get_all_batches_filter_by_status(self):
        """Test getting batches filtered by status."""
        # Create and start some batches
        batch1_id = self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=0)
        batch2_id = self.manager.create_deployment_batch('ARIA', 'RXP2', 3, priority=1)

        self.manager.start_batch(batch1_id)
        # batch2 stays pending

        # Get active batches
        active_batches = self.manager.get_all_batches(status='active')
        self.assertEqual(len(active_batches), 1)
        self.assertEqual(active_batches[0]['status'], 'active')

        # Get pending batches
        pending_batches = self.manager.get_all_batches(status='pending')
        self.assertEqual(len(pending_batches), 1)
        self.assertEqual(pending_batches[0]['status'], 'pending')

    def test_get_all_batches_filter_by_venue_and_status(self):
        """Test getting batches filtered by both venue and status."""
        # Create multiple batches
        batch1_id = self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=0)
        batch2_id = self.manager.create_deployment_batch('CORO', 'RXP2', 3, priority=1)
        batch3_id = self.manager.create_deployment_batch('ARIA', 'RXP2', 2, priority=2)

        self.manager.start_batch(batch1_id)
        self.manager.start_batch(batch3_id)
        # batch2 stays pending

        # Get CORO active batches
        batches = self.manager.get_all_batches(venue_code='CORO', status='active')

        # Should return only batch1
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]['venue_code'], 'CORO')
        self.assertEqual(batches[0]['status'], 'active')

    def test_get_all_batches_ordered_by_priority(self):
        """Test that batches are ordered by priority (highest first)."""
        # Create batches with different priorities
        self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=3)
        self.manager.create_deployment_batch('ARIA', 'RXP2', 3, priority=10)
        self.manager.create_deployment_batch('CORO', 'RXP2', 2, priority=1)

        # Get all batches
        batches = self.manager.get_all_batches()

        # Verify order
        self.assertEqual(batches[0]['priority'], 10)
        self.assertEqual(batches[1]['priority'], 3)
        self.assertEqual(batches[2]['priority'], 1)

    # ===========================================
    # Test: get_batch_by_id()
    # ===========================================

    def test_get_batch_by_id_valid(self):
        """Test getting batch by valid ID."""
        # Create batch
        batch_id = self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=0)

        # Get batch
        batch = self.manager.get_batch_by_id(batch_id)

        # Verify details
        self.assertIsNotNone(batch)
        self.assertEqual(batch['id'], batch_id)
        self.assertEqual(batch['venue_code'], 'CORO')
        self.assertEqual(batch['product_type'], 'RXP2')
        self.assertEqual(batch['total_count'], 5)

    def test_get_batch_by_id_nonexistent(self):
        """Test getting non-existent batch returns None."""
        batch = self.manager.get_batch_by_id(99999)
        self.assertIsNone(batch)

    def test_get_batch_by_id_includes_timestamps(self):
        """Test that batch includes all timestamp fields."""
        # Create and start batch
        batch_id = self.manager.create_deployment_batch('CORO', 'RXP2', 5, priority=0)
        self.manager.start_batch(batch_id)

        # Get batch
        batch = self.manager.get_batch_by_id(batch_id)

        # Verify timestamps exist
        self.assertIsNotNone(batch['created_at'])
        self.assertIsNotNone(batch['started_at'])
        self.assertIsNone(batch['completed_at'])  # Not completed yet


if __name__ == '__main__':
    unittest.main()
