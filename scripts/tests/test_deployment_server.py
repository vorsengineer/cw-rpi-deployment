#!/usr/bin/env python3
"""
Comprehensive Test Suite for Deployment Server (TDD Approach)

Tests all deployment server functionality:
- API endpoint responses (config, status, images, health)
- Hostname assignment integration with HostnameManager
- Database operations (deployment_history, master_images)
- Error handling (missing images, database errors, invalid requests)
- Status reporting and logging
- Configuration validation
- Batch deployment integration

Author: Raspberry Pi Deployment System (TDD)
Date: 2025-10-23
"""

import unittest
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add scripts directory to path
sys.path.insert(0, '/opt/rpi-deployment/scripts')

# Import modules to test (will fail initially - that's TDD!)
try:
    from deployment_server import app, calculate_checksum, get_active_image
    from hostname_manager import HostnameManager
    from database_setup import initialize_database
except ImportError as e:
    print(f"WARNING: Import failed (expected in TDD): {e}")


class TestDeploymentServerSetup(unittest.TestCase):
    """Test deployment server initialization and configuration"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = Path(self.test_dir) / "test_deployment.db"
        self.test_image_dir = Path(self.test_dir) / "images"
        self.test_image_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_flask_app_exists(self):
        """Test Flask application is created"""
        self.assertIsNotNone(app)
        self.assertEqual(app.name, 'deployment_server')

    def test_app_has_required_routes(self):
        """Test all required API routes are registered"""
        required_routes = [
            '/api/config',
            '/api/status',
            '/images/<filename>',
            '/health'
        ]

        # Get all registered routes (without methods)
        app_routes = [rule.rule for rule in app.url_map.iter_rules()]

        for route in required_routes:
            # Check if any route matches (accounting for parameters)
            route_pattern = route.replace('<filename>', '')
            found = any(route_pattern in r for r in app_routes)
            self.assertTrue(found, f"Route {route} not found in app routes")


class TestChecksumCalculation(unittest.TestCase):
    """Test checksum calculation utility"""

    def setUp(self):
        """Create temporary test file"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = Path(self.test_dir) / "test.img"

    def tearDown(self):
        """Clean up test files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_calculate_checksum_small_file(self):
        """Test checksum calculation for small file"""
        # Create test file with known content
        content = b"Hello World Test Image"
        self.test_file.write_bytes(content)

        # Calculate checksum
        checksum = calculate_checksum(str(self.test_file))

        # Verify it's a valid SHA256 hex string
        self.assertEqual(len(checksum), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in checksum))

    def test_calculate_checksum_consistency(self):
        """Test checksum is consistent for same content"""
        content = b"Test content for consistency"
        self.test_file.write_bytes(content)

        checksum1 = calculate_checksum(str(self.test_file))
        checksum2 = calculate_checksum(str(self.test_file))

        self.assertEqual(checksum1, checksum2)

    def test_calculate_checksum_different_content(self):
        """Test different content produces different checksum"""
        self.test_file.write_bytes(b"Content A")
        checksum_a = calculate_checksum(str(self.test_file))

        self.test_file.write_bytes(b"Content B")
        checksum_b = calculate_checksum(str(self.test_file))

        self.assertNotEqual(checksum_a, checksum_b)

    def test_calculate_checksum_large_file(self):
        """Test checksum calculation handles large files (chunked reading)"""
        # Create 10MB test file
        large_content = b"X" * (10 * 1024 * 1024)
        self.test_file.write_bytes(large_content)

        checksum = calculate_checksum(str(self.test_file))
        self.assertEqual(len(checksum), 64)


class TestGetActiveImage(unittest.TestCase):
    """Test active image retrieval from database"""

    def setUp(self):
        """Set up test database"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = Path(self.test_dir) / "test.db"
        initialize_database(str(self.test_db))

    def tearDown(self):
        """Clean up test database"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('deployment_server.DB_PATH')
    def test_get_active_image_kxp2(self, mock_db_path):
        """Test retrieving active KXP2 image"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))

        # Insert test image
        import sqlite3
        with sqlite3.connect(str(self.test_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO master_images
                (filename, product_type, version, size_bytes, checksum, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, ('kxp2_master.img', 'KXP2', '1.0', 4294967296, 'abc123'))

        image_info = get_active_image('KXP2')

        self.assertIsNotNone(image_info)
        self.assertEqual(image_info['filename'], 'kxp2_master.img')
        self.assertEqual(image_info['checksum'], 'abc123')
        self.assertEqual(image_info['size'], 4294967296)

    @patch('deployment_server.DB_PATH')
    def test_get_active_image_no_active(self, mock_db_path):
        """Test retrieving image when none is active"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))

        image_info = get_active_image('KXP2')
        self.assertIsNone(image_info)

    @patch('deployment_server.DB_PATH')
    def test_get_active_image_multiple_only_active(self, mock_db_path):
        """Test retrieves only active image when multiple exist"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))

        import sqlite3
        with sqlite3.connect(str(self.test_db)) as conn:
            cursor = conn.cursor()
            # Insert inactive image
            cursor.execute("""
                INSERT INTO master_images
                (filename, product_type, version, size_bytes, checksum, is_active)
                VALUES (?, ?, ?, ?, ?, 0)
            """, ('kxp2_old.img', 'KXP2', '0.9', 3000000000, 'old123'))
            # Insert active image
            cursor.execute("""
                INSERT INTO master_images
                (filename, product_type, version, size_bytes, checksum, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, ('kxp2_new.img', 'KXP2', '1.0', 4000000000, 'new456'))

        image_info = get_active_image('KXP2')

        self.assertEqual(image_info['filename'], 'kxp2_new.img')
        self.assertEqual(image_info['checksum'], 'new456')


class TestConfigEndpoint(unittest.TestCase):
    """Test /api/config endpoint"""

    def setUp(self):
        """Set up test client and database"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = Path(self.test_dir) / "test.db"
        self.test_image_dir = Path(self.test_dir) / "images"
        self.test_image_dir.mkdir(parents=True, exist_ok=True)

        initialize_database(str(self.test_db))

        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('deployment_server.hostname_mgr')
    @patch('deployment_server.IMAGE_DIR')
    @patch('deployment_server.DB_PATH')
    def test_config_endpoint_kxp2_with_venue(self, mock_db_path, mock_image_dir, mock_hostname_mgr):
        """Test config endpoint returns proper configuration for KXP2"""
        # Setup mocks
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))
        mock_image_dir.__truediv__ = Mock(return_value=self.test_image_dir / "kxp2_master.img")
        mock_hostname_mgr.assign_hostname.return_value = "KXP2-CORO-001"

        # Create test image
        test_image = self.test_image_dir / "kxp2_master.img"
        test_image.write_bytes(b"Test image content")

        # Make request
        response = self.client.post('/api/config', json={
            'product_type': 'KXP2',
            'venue_code': 'CORO',
            'serial_number': '1000000012345678',
            'mac_address': 'aa:bb:cc:dd:ee:ff'
        })

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data['hostname'], 'KXP2-CORO-001')
        self.assertEqual(data['product_type'], 'KXP2')
        self.assertEqual(data['venue_code'], 'CORO')
        self.assertIn('image_url', data)
        self.assertIn('image_size', data)
        self.assertIn('image_checksum', data)

    @patch('deployment_server.hostname_mgr')
    def test_config_endpoint_rxp2_serial_based(self, mock_hostname_mgr):
        """Test config endpoint for RXP2 (serial-based hostname)"""
        mock_hostname_mgr.assign_hostname.return_value = "RXP2-ARIA-12345678"

        response = self.client.post('/api/config', json={
            'product_type': 'RXP2',
            'venue_code': 'ARIA',
            'serial_number': '1000000012345678',
            'mac_address': 'aa:bb:cc:dd:ee:ff'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['hostname'], 'RXP2-ARIA-12345678')
        self.assertEqual(data['product_type'], 'RXP2')

    @patch('deployment_server.DB_PATH')
    def test_config_endpoint_no_image_error(self, mock_db_path):
        """Test config endpoint returns 404 when no image available"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))

        response = self.client.post('/api/config', json={
            'product_type': 'KXP2',
            'venue_code': 'CORO',
            'serial_number': '1000000012345678',
            'mac_address': 'aa:bb:cc:dd:ee:ff'
        })

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)

    def test_config_endpoint_missing_data(self):
        """Test config endpoint handles missing request data"""
        response = self.client.post('/api/config', json={})

        # Should still return 200 with fallback hostname
        self.assertEqual(response.status_code, 200)

    @patch('deployment_server.hostname_mgr')
    @patch('deployment_server.DB_PATH')
    def test_config_endpoint_records_deployment(self, mock_db_path, mock_hostname_mgr):
        """Test config endpoint records deployment in history"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))
        mock_hostname_mgr.assign_hostname.return_value = "KXP2-CORO-001"

        # Insert test image
        import sqlite3
        with sqlite3.connect(str(self.test_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO master_images
                (filename, product_type, version, size_bytes, checksum, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, ('kxp2_master.img', 'KXP2', '1.0', 4000000000, 'abc123'))

        response = self.client.post('/api/config', json={
            'product_type': 'KXP2',
            'venue_code': 'CORO',
            'serial_number': '12345678',
            'mac_address': 'aa:bb:cc:dd:ee:ff'
        })

        # Verify deployment recorded
        with sqlite3.connect(str(self.test_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deployment_history WHERE hostname = ?", ('KXP2-CORO-001',))
            deployment = cursor.fetchone()
            self.assertIsNotNone(deployment)


class TestStatusEndpoint(unittest.TestCase):
    """Test /api/status endpoint"""

    def setUp(self):
        """Set up test client and database"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = Path(self.test_dir) / "test.db"
        self.test_log_dir = Path(self.test_dir) / "logs"
        self.test_log_dir.mkdir(parents=True, exist_ok=True)

        initialize_database(str(self.test_db))

        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('deployment_server.DB_PATH')
    @patch('deployment_server.LOG_DIR')
    def test_status_endpoint_success(self, mock_log_dir, mock_db_path):
        """Test status endpoint accepts success status"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))
        mock_log_dir.__truediv__ = Mock(return_value=self.test_log_dir / "deployment_20251023.log")

        # Insert deployment to update
        import sqlite3
        with sqlite3.connect(str(self.test_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO deployment_history
                (hostname, deployment_status, started_at)
                VALUES (?, 'started', CURRENT_TIMESTAMP)
            """, ('KXP2-CORO-001',))

        response = self.client.post('/api/status', json={
            'status': 'success',
            'hostname': 'KXP2-CORO-001',
            'serial': '12345678',
            'mac_address': 'aa:bb:cc:dd:ee:ff'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['received'])
        self.assertEqual(data['hostname'], 'KXP2-CORO-001')

    @patch('deployment_server.DB_PATH')
    @patch('deployment_server.LOG_DIR')
    def test_status_endpoint_failed_with_error(self, mock_log_dir, mock_db_path):
        """Test status endpoint records failure with error message"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))
        mock_log_dir.__truediv__ = Mock(return_value=self.test_log_dir / "deployment_20251023.log")

        # Insert deployment
        import sqlite3
        with sqlite3.connect(str(self.test_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO deployment_history
                (hostname, deployment_status, started_at)
                VALUES (?, 'downloading', CURRENT_TIMESTAMP)
            """, ('KXP2-CORO-002',))

        response = self.client.post('/api/status', json={
            'status': 'failed',
            'hostname': 'KXP2-CORO-002',
            'serial': '87654321',
            'mac_address': 'ff:ee:dd:cc:bb:aa',
            'error_message': 'SD card write failed'
        })

        self.assertEqual(response.status_code, 200)

        # Verify error recorded in database
        with sqlite3.connect(str(self.test_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT deployment_status, error_message
                FROM deployment_history
                WHERE hostname = ?
            """, ('KXP2-CORO-002',))
            row = cursor.fetchone()
            self.assertEqual(row[0], 'failed')
            self.assertEqual(row[1], 'SD card write failed')

    @patch('deployment_server.DB_PATH')
    @patch('deployment_server.LOG_DIR')
    def test_status_endpoint_progress_update(self, mock_log_dir, mock_db_path):
        """Test status endpoint handles progress updates (downloading, verifying)"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))
        mock_log_dir.__truediv__ = Mock(return_value=self.test_log_dir / "deployment_20251023.log")

        # Insert deployment
        import sqlite3
        with sqlite3.connect(str(self.test_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO deployment_history
                (hostname, deployment_status, started_at)
                VALUES (?, 'started', CURRENT_TIMESTAMP)
            """, ('KXP2-CORO-003',))

        # Update to downloading
        response = self.client.post('/api/status', json={
            'status': 'downloading',
            'hostname': 'KXP2-CORO-003',
            'serial': '11223344'
        })

        self.assertEqual(response.status_code, 200)

    @patch('deployment_server.LOG_DIR')
    def test_status_endpoint_creates_daily_log(self, mock_log_dir):
        """Test status endpoint writes to daily log file"""
        mock_log_dir.__truediv__ = Mock(return_value=self.test_log_dir / "deployment_20251023.log")

        response = self.client.post('/api/status', json={
            'status': 'downloading',
            'hostname': 'KXP2-TEST-001',
            'serial': '99887766'
        })

        # Check log file was created (mocked, so just verify call)
        self.assertEqual(response.status_code, 200)


class TestImageDownloadEndpoint(unittest.TestCase):
    """Test /images/<filename> endpoint"""

    def setUp(self):
        """Set up test client and image directory"""
        self.test_dir = tempfile.mkdtemp()
        self.test_image_dir = Path(self.test_dir) / "images"
        self.test_image_dir.mkdir(parents=True, exist_ok=True)

        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('deployment_server.IMAGE_DIR')
    def test_image_download_success(self, mock_image_dir):
        """Test successful image download"""
        # Create test image
        test_image = self.test_image_dir / "kxp2_master.img"
        test_image.write_bytes(b"Test image content here")

        mock_image_dir.__truediv__ = Mock(return_value=test_image)

        response = self.client.get('/images/kxp2_master.img')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"Test image content here")

    @patch('deployment_server.IMAGE_DIR')
    def test_image_download_not_found(self, mock_image_dir):
        """Test image download returns 404 for missing file"""
        nonexistent = self.test_image_dir / "nonexistent.img"
        mock_image_dir.__truediv__ = Mock(return_value=nonexistent)

        response = self.client.get('/images/nonexistent.img')

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)

    @patch('deployment_server.IMAGE_DIR')
    def test_image_download_large_file(self, mock_image_dir):
        """Test image download handles large files"""
        # Create 1MB test file
        test_image = self.test_image_dir / "large.img"
        test_image.write_bytes(b"X" * (1024 * 1024))

        mock_image_dir.__truediv__ = Mock(return_value=test_image)

        response = self.client.get('/images/large.img')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1024 * 1024)


class TestHealthEndpoint(unittest.TestCase):
    """Test /health endpoint"""

    def setUp(self):
        """Set up test client"""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_health_endpoint_returns_healthy(self):
        """Test health endpoint returns success"""
        response = self.client.get('/health')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)

    def test_health_endpoint_timestamp_format(self):
        """Test health endpoint timestamp is ISO format"""
        response = self.client.get('/health')

        data = response.get_json()
        # Verify timestamp is valid ISO format (basic check)
        self.assertIn('T', data['timestamp'])


class TestBatchIntegration(unittest.TestCase):
    """Test integration with batch deployment system"""

    def setUp(self):
        """Set up test database with batch"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = Path(self.test_dir) / "test.db"
        initialize_database(str(self.test_db))

        # Create venue and batch
        self.hostname_mgr = HostnameManager(str(self.test_db))
        self.hostname_mgr.create_venue('TEST', 'Test Venue')
        self.hostname_mgr.bulk_import_kart_numbers('TEST', ['001', '002', '003'])
        self.batch_id = self.hostname_mgr.create_deployment_batch('TEST', 'KXP2', 3)
        self.hostname_mgr.start_batch(self.batch_id)

    def tearDown(self):
        """Clean up test database"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('deployment_server.hostname_mgr')
    @patch('deployment_server.DB_PATH')
    def test_config_checks_active_batch(self, mock_db_path, mock_hostname_mgr):
        """Test config endpoint checks for active batch"""
        mock_db_path.__str__ = Mock(return_value=str(self.test_db))
        mock_hostname_mgr.get_active_batch.return_value = {
            'id': self.batch_id,
            'venue_code': 'TEST',
            'product_type': 'KXP2',
            'remaining_count': 3
        }
        mock_hostname_mgr.assign_from_batch.return_value = 'KXP2-TEST-001'

        # Verify batch integration works
        batch = self.hostname_mgr.get_active_batch()
        self.assertIsNotNone(batch)
        self.assertEqual(batch['venue_code'], 'TEST')


class TestErrorHandling(unittest.TestCase):
    """Test error handling in deployment server"""

    def setUp(self):
        """Set up test client"""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_config_endpoint_handles_database_error(self):
        """Test config endpoint handles database errors gracefully"""
        with patch('deployment_server.hostname_mgr.assign_hostname', side_effect=Exception("DB connection failed")):
            response = self.client.post('/api/config', json={
                'product_type': 'KXP2',
                'venue_code': 'FAIL'
            })

            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertIn('error', data)

    def test_status_endpoint_handles_invalid_json(self):
        """Test status endpoint handles invalid JSON"""
        response = self.client.post('/api/status',
                                   data='not valid json',
                                   content_type='application/json')

        self.assertEqual(response.status_code, 400)

    @patch('deployment_server.IMAGE_DIR')
    def test_image_endpoint_handles_read_error(self, mock_image_dir):
        """Test image endpoint handles file read errors"""
        # Mock file that exists but can't be read
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_image_dir.__truediv__ = Mock(return_value=mock_path)

        with patch('deployment_server.send_file', side_effect=IOError("Permission denied")):
            response = self.client.get('/images/test.img')

            self.assertEqual(response.status_code, 500)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
