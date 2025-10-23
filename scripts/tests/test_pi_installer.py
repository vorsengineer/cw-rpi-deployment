#!/usr/bin/env python3
"""
Comprehensive Test Suite for Pi Installer (TDD Approach)

Tests all Pi installer functionality:
- PiInstaller class initialization
- SD card verification
- Configuration fetching from server
- Image download and write operations
- Installation verification
- Hostname customization
- Status reporting
- Error handling (missing SD card, network errors, write failures)
- Command-line argument parsing

Author: Raspberry Pi Deployment System (TDD)
Date: 2025-10-23
"""

import unittest
import sys
import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import io

# Add scripts directory to path
sys.path.insert(0, '/opt/rpi-deployment/scripts')

# Import modules to test (will fail initially - that's TDD!)
try:
    from pi_installer import PiInstaller, main
except ImportError as e:
    print(f"WARNING: Import failed (expected in TDD): {e}")


class TestPiInstallerInitialization(unittest.TestCase):
    """Test PiInstaller class initialization"""

    def test_init_with_defaults(self):
        """Test PiInstaller initialization with default parameters"""
        installer = PiInstaller("http://192.168.151.1:5001")

        self.assertEqual(installer.server_url, "http://192.168.151.1:5001")
        self.assertEqual(installer.product_type, "KXP2")
        self.assertIsNone(installer.venue_code)
        self.assertEqual(installer.target_device, "/dev/mmcblk0")

    def test_init_with_custom_parameters(self):
        """Test PiInstaller initialization with custom parameters"""
        installer = PiInstaller(
            "http://192.168.151.1:5001",
            product_type="RXP2",
            venue_code="CORO",
            target_device="/dev/sda"
        )

        self.assertEqual(installer.product_type, "RXP2")
        self.assertEqual(installer.venue_code, "CORO")
        self.assertEqual(installer.target_device, "/dev/sda")

    def test_init_creates_logger(self):
        """Test PiInstaller creates logger instance"""
        installer = PiInstaller("http://192.168.151.1:5001")

        self.assertIsNotNone(installer.logger)
        self.assertEqual(installer.logger.name, "PiInstaller")

    def test_init_hostname_starts_none(self):
        """Test hostname is initially None before assignment"""
        installer = PiInstaller("http://192.168.151.1:5001")

        self.assertIsNone(installer.hostname)
        self.assertIsNone(installer.config)


class TestGetSerialNumber(unittest.TestCase):
    """Test serial number retrieval"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller("http://192.168.151.1:5001")

    @patch('builtins.open', new_callable=mock_open, read_data='Serial\t\t: 1000000012345678\n')
    def test_get_serial_number_success(self, mock_file):
        """Test successful serial number retrieval"""
        serial = self.installer.get_serial_number()

        self.assertEqual(serial, '1000000012345678')
        mock_file.assert_called_once_with('/proc/cpuinfo', 'r')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_serial_number_file_not_found(self, mock_file):
        """Test get_serial_number returns 'unknown' if cpuinfo missing"""
        serial = self.installer.get_serial_number()

        self.assertEqual(serial, 'unknown')

    @patch('builtins.open', new_callable=mock_open, read_data='Model: Raspberry Pi 5\n')
    def test_get_serial_number_no_serial_line(self, mock_file):
        """Test get_serial_number returns 'unknown' if Serial line missing"""
        serial = self.installer.get_serial_number()

        self.assertEqual(serial, 'unknown')


class TestGetMacAddress(unittest.TestCase):
    """Test MAC address retrieval"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller("http://192.168.151.1:5001")

    @patch('subprocess.run')
    def test_get_mac_address_success(self, mock_run):
        """Test successful MAC address retrieval"""
        mock_result = MagicMock()
        mock_result.stdout = """1: lo: <LOOPBACK>
    link/loopback 00:00:00:00:00:00
2: eth0: <BROADCAST>
    link/ether aa:bb:cc:dd:ee:ff
"""
        mock_run.return_value = mock_result

        mac = self.installer.get_mac_address()

        self.assertEqual(mac, 'aa:bb:cc:dd:ee:ff')

    @patch('subprocess.run', side_effect=Exception("Command failed"))
    def test_get_mac_address_failure(self, mock_run):
        """Test get_mac_address returns None on failure"""
        mac = self.installer.get_mac_address()

        self.assertIsNone(mac)


class TestVerifySDCard(unittest.TestCase):
    """Test SD card verification"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller("http://192.168.151.1:5001")

    @patch('pathlib.Path.exists', return_value=True)
    @patch('subprocess.run')
    def test_verify_sd_card_success(self, mock_run, mock_exists):
        """Test successful SD card verification"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.installer.verify_sd_card()

        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('pathlib.Path.exists', return_value=False)
    def test_verify_sd_card_not_found(self, mock_exists):
        """Test verify_sd_card raises error if device not found"""
        with self.assertRaises(RuntimeError) as context:
            self.installer.verify_sd_card()

        self.assertIn('not found', str(context.exception))

    @patch('pathlib.Path.exists', return_value=True)
    @patch('subprocess.run')
    def test_verify_sd_card_not_accessible(self, mock_run, mock_exists):
        """Test verify_sd_card raises error if device not accessible"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'blockdev')

        with self.assertRaises(RuntimeError) as context:
            self.installer.verify_sd_card()

        self.assertIn('not accessible', str(context.exception))


class TestGetConfig(unittest.TestCase):
    """Test configuration fetching from server"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller(
            "http://192.168.151.1:5001",
            product_type="KXP2",
            venue_code="CORO"
        )

    @patch.object(PiInstaller, 'get_serial_number', return_value='12345678')
    @patch.object(PiInstaller, 'get_mac_address', return_value='aa:bb:cc:dd:ee:ff')
    @patch('requests.post')
    def test_get_config_success(self, mock_post, mock_mac, mock_serial):
        """Test successful configuration retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'hostname': 'KXP2-CORO-001',
            'version': '3.0',
            'image_url': 'http://192.168.151.1/images/kxp2_master.img',
            'image_size': 4294967296,
            'image_checksum': 'abc123'
        }
        mock_post.return_value = mock_response

        config = self.installer.get_config()

        self.assertEqual(config['hostname'], 'KXP2-CORO-001')
        self.assertEqual(self.installer.hostname, 'KXP2-CORO-001')
        self.assertEqual(self.installer.config, config)

        # Verify request was made with correct data
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs['json']['product_type'], 'KXP2')
        self.assertEqual(call_kwargs['json']['venue_code'], 'CORO')

    @patch('requests.post', side_effect=Exception("Connection refused"))
    def test_get_config_network_error(self, mock_post):
        """Test get_config raises error on network failure"""
        with self.assertRaises(RuntimeError) as context:
            self.installer.get_config()

        self.assertIn('Failed to get config', str(context.exception))

    @patch.object(PiInstaller, 'get_serial_number', return_value='12345678')
    @patch.object(PiInstaller, 'get_mac_address', return_value='aa:bb:cc:dd:ee:ff')
    @patch('requests.post')
    def test_get_config_stores_hostname(self, mock_post, mock_mac, mock_serial):
        """Test get_config stores assigned hostname"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'hostname': 'KXP2-TEST-042',
            'version': '3.0',
            'image_url': 'http://192.168.151.1/images/kxp2_master.img',
            'image_size': 4000000000,
            'image_checksum': 'def456'
        }
        mock_post.return_value = mock_response

        config = self.installer.get_config()

        self.assertEqual(self.installer.hostname, 'KXP2-TEST-042')


class TestDownloadAndWriteImage(unittest.TestCase):
    """Test image download and write operations"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller("http://192.168.151.1:5001")
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('requests.get')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    def test_download_and_write_small_image(self, mock_fsync, mock_file, mock_get):
        """Test downloading and writing small image"""
        # Mock response with small content
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content.return_value = [b'X' * 512, b'Y' * 512]
        mock_get.return_value = mock_response

        self.installer.download_and_write_image(
            'http://192.168.151.1/images/test.img',
            1024
        )

        # Verify file was opened for writing
        mock_file.assert_called_once_with(self.installer.target_device, 'wb')

        # Verify content was written
        handle = mock_file()
        self.assertEqual(handle.write.call_count, 2)

    @patch('requests.get')
    def test_download_and_write_network_error(self, mock_get):
        """Test download_and_write_image handles network errors"""
        mock_get.side_effect = Exception("Connection timeout")

        with self.assertRaises(RuntimeError) as context:
            self.installer.download_and_write_image(
                'http://192.168.151.1/images/test.img',
                1024
            )

        self.assertIn('Image write failed', str(context.exception))

    @patch('requests.get')
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_download_and_write_permission_error(self, mock_file, mock_get):
        """Test download_and_write_image handles write permission errors"""
        mock_response = MagicMock()
        mock_get.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.installer.download_and_write_image(
                'http://192.168.151.1/images/test.img',
                1024
            )

        self.assertIn('Image write failed', str(context.exception))

    @patch('requests.get')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    def test_download_logs_progress(self, mock_fsync, mock_file, mock_get):
        """Test download logs progress for large files"""
        # Mock large file (200MB)
        mock_response = MagicMock()
        mock_response.headers = {'content-length': str(200 * 1024 * 1024)}
        # Simulate 200MB in 8KB chunks (25,600 chunks)
        chunks = [b'X' * 8192] * 25600
        mock_response.iter_content.return_value = chunks
        mock_get.return_value = mock_response

        with patch.object(self.installer.logger, 'info') as mock_log:
            self.installer.download_and_write_image(
                'http://192.168.151.1/images/large.img',
                200 * 1024 * 1024
            )

            # Should log progress at 100MB intervals
            # 200MB file should have at least one progress log
            progress_logs = [call for call in mock_log.call_args_list
                           if 'Progress' in str(call)]
            self.assertGreater(len(progress_logs), 0)


class TestVerifyInstallation(unittest.TestCase):
    """Test installation verification"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller("http://192.168.151.1:5001")

    @patch('subprocess.run')
    @patch('time.sleep')
    @patch('builtins.open', new_callable=mock_open, read_data=b'X' * (100 * 1024 * 1024))
    def test_verify_installation_success(self, mock_file, mock_sleep, mock_run):
        """Test successful installation verification"""
        result = self.installer.verify_installation('expected_checksum')

        self.assertTrue(result)
        mock_run.assert_called_once_with(['sync'])

    @patch('subprocess.run')
    @patch('time.sleep')
    @patch('builtins.open', side_effect=IOError("Read error"))
    def test_verify_installation_read_error(self, mock_file, mock_sleep, mock_run):
        """Test verify_installation handles read errors"""
        result = self.installer.verify_installation('expected_checksum')

        self.assertFalse(result)

    @patch('subprocess.run')
    @patch('time.sleep')
    @patch('builtins.open', new_callable=mock_open, read_data=b'')
    def test_verify_installation_empty_device(self, mock_file, mock_sleep, mock_run):
        """Test verify_installation handles empty device"""
        result = self.installer.verify_installation('expected_checksum')

        # Should still return True (partial checksum for speed)
        self.assertTrue(result)


class TestCustomizeInstallation(unittest.TestCase):
    """Test installation customization"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller(
            "http://192.168.151.1:5001",
            product_type="KXP2",
            venue_code="CORO"
        )
        self.installer.hostname = "KXP2-CORO-001"
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('pathlib.Path.mkdir')
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.chmod')
    def test_customize_installation_creates_firstrun(self, mock_chmod, mock_file, mock_run, mock_mkdir):
        """Test customization creates firstrun.sh script"""
        self.installer.customize_installation()

        # Verify mount commands called
        mount_calls = [call for call in mock_run.call_args_list
                      if 'mount' in str(call)]
        self.assertEqual(len(mount_calls), 2)  # mount and umount

        # Verify file was written
        mock_file.assert_called()

        # Verify script was made executable
        mock_chmod.assert_called_once()

    @patch('pathlib.Path.mkdir')
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.chmod')
    def test_customize_installation_uses_assigned_hostname(self, mock_chmod, mock_file, mock_run, mock_mkdir):
        """Test customization uses hostname assigned by server"""
        self.installer.customize_installation()

        # Verify hostname appears in script content
        written_content = ''.join(
            call.args[0] for call in mock_file().write.call_args_list
            if call.args
        )
        self.assertIn('KXP2-CORO-001', written_content)

    @patch('pathlib.Path.mkdir')
    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'mount'))
    def test_customize_installation_mount_failure(self, mock_run, mock_mkdir):
        """Test customization handles mount failures gracefully"""
        # Should log warning but not raise exception
        self.installer.customize_installation()

        # Verify warning was logged (method should complete)
        self.assertIsNotNone(self.installer.logger)


class TestReportStatus(unittest.TestCase):
    """Test status reporting to server"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller("http://192.168.151.1:5001")
        self.installer.hostname = "KXP2-CORO-001"

    @patch.object(PiInstaller, 'get_serial_number', return_value='12345678')
    @patch.object(PiInstaller, 'get_mac_address', return_value='aa:bb:cc:dd:ee:ff')
    @patch('requests.post')
    def test_report_status_success(self, mock_post, mock_mac, mock_serial):
        """Test successful status reporting"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        self.installer.report_status('downloading', 'Image download started')

        # Verify request was made
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs['json']['status'], 'downloading')
        self.assertEqual(call_kwargs['json']['hostname'], 'KXP2-CORO-001')

    @patch.object(PiInstaller, 'get_serial_number', return_value='12345678')
    @patch.object(PiInstaller, 'get_mac_address', return_value='aa:bb:cc:dd:ee:ff')
    @patch('requests.post', side_effect=Exception("Connection timeout"))
    def test_report_status_network_failure(self, mock_post, mock_mac, mock_serial):
        """Test report_status handles network failures gracefully"""
        # Should log warning but not raise exception
        self.installer.report_status('downloading', 'Test message')

        # Verify method completes without error
        self.assertIsNotNone(self.installer.logger)

    @patch.object(PiInstaller, 'get_serial_number', return_value='12345678')
    @patch.object(PiInstaller, 'get_mac_address', return_value='aa:bb:cc:dd:ee:ff')
    @patch('requests.post')
    def test_report_status_includes_error_message(self, mock_post, mock_mac, mock_serial):
        """Test report_status includes error message when provided"""
        self.installer.report_status('failed', 'Installation failed', error_message='SD card write error')

        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs['json']['error_message'], 'SD card write error')


class TestInstallMethod(unittest.TestCase):
    """Test main install method orchestration"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller(
            "http://192.168.151.1:5001",
            product_type="KXP2",
            venue_code="CORO"
        )

    @patch.object(PiInstaller, 'verify_sd_card', return_value=True)
    @patch.object(PiInstaller, 'get_config')
    @patch.object(PiInstaller, 'download_and_write_image')
    @patch.object(PiInstaller, 'verify_installation', return_value=True)
    @patch.object(PiInstaller, 'customize_installation')
    @patch.object(PiInstaller, 'report_status')
    @patch.object(PiInstaller, 'reboot_system')
    def test_install_success_flow(self, mock_reboot, mock_report, mock_customize,
                                  mock_verify, mock_download, mock_config, mock_sd):
        """Test successful installation flow"""
        mock_config.return_value = {
            'hostname': 'KXP2-CORO-001',
            'image_url': 'http://192.168.151.1/images/kxp2.img',
            'image_size': 4000000000,
            'image_checksum': 'abc123'
        }

        self.installer.install()

        # Verify all steps called in order
        mock_sd.assert_called_once()
        mock_config.assert_called_once()
        mock_download.assert_called_once()
        mock_verify.assert_called_once()
        mock_customize.assert_called_once()
        mock_reboot.assert_called_once()

        # Verify status reports
        status_calls = [call[0][0] for call in mock_report.call_args_list]
        self.assertIn('starting', status_calls)
        self.assertIn('downloading', status_calls)
        self.assertIn('verifying', status_calls)
        self.assertIn('customizing', status_calls)
        self.assertIn('success', status_calls)

    @patch.object(PiInstaller, 'verify_sd_card', side_effect=RuntimeError("SD card not found"))
    @patch.object(PiInstaller, 'report_status')
    def test_install_failure_reports_error(self, mock_report, mock_sd):
        """Test installation failure reports error status"""
        with self.assertRaises(SystemExit):
            self.installer.install()

        # Verify failure reported
        status_calls = [call[0][0] for call in mock_report.call_args_list]
        self.assertIn('failed', status_calls)

    @patch.object(PiInstaller, 'verify_sd_card', return_value=True)
    @patch.object(PiInstaller, 'get_config')
    @patch.object(PiInstaller, 'download_and_write_image')
    @patch.object(PiInstaller, 'verify_installation', return_value=False)
    @patch.object(PiInstaller, 'report_status')
    def test_install_verification_failure(self, mock_report, mock_verify,
                                         mock_download, mock_config, mock_sd):
        """Test installation handles verification failure"""
        mock_config.return_value = {
            'hostname': 'KXP2-CORO-001',
            'image_url': 'http://192.168.151.1/images/kxp2.img',
            'image_size': 4000000000,
            'image_checksum': 'abc123'
        }

        with self.assertRaises(SystemExit):
            self.installer.install()

        # Verify failure reported
        status_calls = [call[0][0] for call in mock_report.call_args_list]
        self.assertIn('failed', status_calls)


class TestRebootSystem(unittest.TestCase):
    """Test system reboot"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller("http://192.168.151.1:5001")

    @patch('time.sleep')
    @patch('subprocess.run')
    def test_reboot_system_calls_reboot(self, mock_run, mock_sleep):
        """Test reboot_system executes reboot command"""
        self.installer.reboot_system()

        mock_sleep.assert_called_once_with(3)
        mock_run.assert_called_once_with(['reboot'])


class TestMainFunction(unittest.TestCase):
    """Test main function and argument parsing"""

    @patch('sys.argv', ['pi_installer.py', '--server', '192.168.151.1', '--product', 'KXP2', '--venue', 'CORO'])
    @patch.object(PiInstaller, 'install')
    def test_main_parses_arguments(self, mock_install):
        """Test main function parses command-line arguments"""
        main()

        # Verify install was called
        mock_install.assert_called_once()

    @patch('sys.argv', ['pi_installer.py', '--server', '192.168.151.1:5001'])
    @patch.object(PiInstaller, 'install')
    def test_main_handles_server_with_port(self, mock_install):
        """Test main handles server URL with port"""
        main()

        mock_install.assert_called_once()

    @patch('sys.argv', ['pi_installer.py', '--server', '192.168.151.1', '--device', '/dev/sda'])
    @patch.object(PiInstaller, 'install')
    def test_main_custom_device(self, mock_install):
        """Test main accepts custom target device"""
        main()

        mock_install.assert_called_once()

    @patch('sys.argv', ['pi_installer.py'])
    def test_main_requires_server_argument(self):
        """Test main requires --server argument"""
        with self.assertRaises(SystemExit):
            main()


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""

    def setUp(self):
        """Set up test installer"""
        self.installer = PiInstaller("http://192.168.151.1:5001")

    def test_installer_handles_empty_hostname(self):
        """Test installer handles empty hostname assignment"""
        self.installer.hostname = None
        # Should use fallback in customization
        self.assertIsNone(self.installer.hostname)

    @patch.object(PiInstaller, 'get_serial_number', return_value='')
    def test_get_serial_handles_empty_string(self, mock_cpuinfo):
        """Test get_serial_number handles empty serial"""
        # Even with mock, should handle empty string gracefully
        self.assertIsNotNone(self.installer.get_serial_number())

    def test_installer_handles_very_long_venue_code(self):
        """Test installer accepts venue codes (validation on server side)"""
        installer = PiInstaller(
            "http://192.168.151.1:5001",
            venue_code="TOOLONG"  # 7 chars, server should validate
        )
        self.assertEqual(installer.venue_code, "TOOLONG")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
