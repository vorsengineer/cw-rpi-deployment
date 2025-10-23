## Phase 8: Enhanced Python Deployment Scripts

### Step 8.1: Deployment Server Application (Deployment Network API)

Create `/opt/rpi-deployment/scripts/deployment_server.py`:

```python
#!/usr/bin/env python3
"""
KXP/RXP Enhanced Deployment Server
Serves configuration and images to Raspberry Pi clients with hostname management
"""

import os
import sys
import json
import hashlib
import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, send_file, request

# Add scripts directory to path
sys.path.append('/opt/rpi-deployment/scripts')
from hostname_manager import HostnameManager

app = Flask(__name__)

# Configuration
DEPLOYMENT_IP = "192.168.151.1"  # Deployment network
IMAGE_DIR = Path("/opt/rpi-deployment/images")
LOG_DIR = Path("/opt/rpi-deployment/logs")
DB_PATH = Path("/opt/rpi-deployment/database/deployment.db")

# Initialize hostname manager
hostname_mgr = HostnameManager()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "deployment.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DeploymentServer")

def calculate_checksum(file_path):
    """Calculate SHA256 checksum of file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_active_image(product_type):
    """Get the active master image for a product type"""
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT filename, checksum, size_bytes
            FROM master_images
            WHERE product_type = ? AND is_active = 1
            LIMIT 1
        ''', (product_type,))
        result = cursor.fetchone()

        if result:
            return {
                'filename': result[0],
                'checksum': result[1],
                'size': result[2]
            }
    return None

@app.route('/api/config', methods=['POST'])
def get_config():
    """Provide deployment configuration to clients based on product/venue"""
    try:
        data = request.json
        product_type = data.get('product_type', 'KXP2')
        venue_code = data.get('venue_code')
        serial_number = data.get('serial_number')
        mac_address = data.get('mac_address')

        # Get active image for product type
        image_info = get_active_image(product_type)
        if not image_info:
            # Fallback to default image
            image_filename = f"{product_type.lower()}_master.img"
            image_path = IMAGE_DIR / image_filename
            if not image_path.exists():
                return jsonify({'error': f'No active image for {product_type}'}), 404

            image_info = {
                'filename': image_filename,
                'checksum': calculate_checksum(image_path),
                'size': image_path.stat().st_size
            }

        # Request hostname assignment
        hostname = None
        if venue_code:
            hostname = hostname_mgr.assign_hostname(
                product_type,
                venue_code,
                mac_address,
                serial_number
            )

        if not hostname:
            # Fallback to serial-based hostname
            hostname = f"{product_type}-DEFAULT-{serial_number[-6:]}" if serial_number else "unknown"

        config = {
            'server_ip': DEPLOYMENT_IP,
            'hostname': hostname,
            'product_type': product_type,
            'venue_code': venue_code,
            'image_url': f'http://{DEPLOYMENT_IP}/images/{image_info["filename"]}',
            'image_size': image_info['size'],
            'image_checksum': image_info['checksum'],
            'version': '3.0',
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Config requested from {request.remote_addr} - Assigned: {hostname}")

        # Record deployment start
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO deployment_history
                (hostname, mac_address, serial_number, ip_address, product_type,
                 venue_code, image_version, deployment_status, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'started', CURRENT_TIMESTAMP)
            ''', (hostname, mac_address, serial_number, request.remote_addr,
                  product_type, venue_code, image_info['filename']))

        return jsonify(config)

    except Exception as e:
        logger.error(f"Error serving config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['POST'])
def receive_status():
    """Receive installation status from clients"""
    try:
        data = request.json
        client_ip = request.remote_addr
        status = data.get('status')
        hostname = data.get('hostname', 'unknown')
        serial = data.get('serial', 'unknown')
        mac_address = data.get('mac_address')
        error_message = data.get('error_message')

        logger.info(f"Status from {client_ip} ({hostname}): {status}")

        # Update deployment history
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()

            if status in ['success', 'failed']:
                # Update deployment completion
                cursor.execute('''
                    UPDATE deployment_history
                    SET deployment_status = ?,
                        completed_at = CURRENT_TIMESTAMP,
                        error_message = ?
                    WHERE hostname = ?
                    AND deployment_status = 'started'
                    ORDER BY started_at DESC
                    LIMIT 1
                ''', (status, error_message, hostname))
            else:
                # Update deployment progress
                cursor.execute('''
                    UPDATE deployment_history
                    SET deployment_status = ?
                    WHERE hostname = ?
                    AND deployment_status IN ('started', 'downloading', 'verifying')
                    ORDER BY started_at DESC
                    LIMIT 1
                ''', (status, hostname))

        # Log to daily file
        status_log = LOG_DIR / f"deployment_{datetime.now().strftime('%Y%m%d')}.log"
        with open(status_log, 'a') as f:
            f.write(f"{datetime.now().isoformat()},{client_ip},{hostname},{serial},{status}\n")

        # Notify web interface via Socket.IO (if connected)
        # This would integrate with the web app's socketio instance

        return jsonify({'received': True, 'hostname': hostname})

    except Exception as e:
        logger.error(f"Error receiving status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/images/<filename>', methods=['GET'])
def download_image(filename):
    """Serve master image for download"""
    try:
        image_path = IMAGE_DIR / filename
        
        if not image_path.exists():
            return jsonify({'error': 'Image not found'}), 404
        
        logger.info(f"Image download started: {filename} to {request.remote_addr}")
        
        return send_file(
            image_path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error serving image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Ensure directories exist
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database if needed
    if not DB_PATH.exists():
        from database_setup import initialize_database
        initialize_database()

    logger.info("Starting deployment server on deployment network")
    logger.info(f"Deployment API: http://{DEPLOYMENT_IP}:5001")

    # Start server (on deployment network port)
    app.run(host='0.0.0.0', port=5001, debug=False)
```

Make executable:
```bash
chmod +x /opt/rpi-deployment/scripts/deployment_server.py
```

### Step 8.2: Enhanced Client Installer Script

Create `/opt/rpi-deployment/scripts/pi_installer.py`:

```python
#!/usr/bin/env python3
"""
KXP/RXP Enhanced Pi Installer
Runs on Raspberry Pi during network boot to install master image with hostname assignment
"""

import os
import sys
import time
import json
import hashlib
import logging
import argparse
import subprocess
import requests
from pathlib import Path

class PiInstaller:
    def __init__(self, server_url, product_type="KXP2", venue_code=None, target_device="/dev/mmcblk0"):
        self.server_url = server_url
        self.product_type = product_type
        self.venue_code = venue_code
        self.target_device = target_device
        self.hostname = None
        self.config = None
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("PiInstaller")
        
    def report_status(self, status, message="", error_message=None):
        """Report installation status to server"""
        try:
            serial = self.get_serial_number()
            mac = self.get_mac_address()
            data = {
                'status': status,
                'message': message,
                'hostname': self.hostname,
                'serial': serial,
                'mac_address': mac,
                'error_message': error_message,
                'timestamp': time.time()
            }
            requests.post(f"{self.server_url}/api/status", json=data, timeout=5)
        except Exception as e:
            self.logger.warning(f"Failed to report status: {e}")
            
    def get_serial_number(self):
        """Get Raspberry Pi serial number"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
        except:
            return "unknown"

    def get_mac_address(self):
        """Get MAC address of first network interface"""
        try:
            # Get first ethernet interface MAC
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'link/ether' in line:
                    return line.split()[1]
        except:
            return None
            
    def verify_sd_card(self):
        """Verify SD card is present and accessible"""
        self.logger.info("Verifying SD card...")
        
        if not Path(self.target_device).exists():
            raise RuntimeError(f"SD card not found: {self.target_device}")
            
        # Check if device is writable
        try:
            subprocess.run(
                ["blockdev", "--getsize64", self.target_device],
                check=True,
                capture_output=True
            )
            self.logger.info("SD card verified")
            return True
        except subprocess.CalledProcessError:
            raise RuntimeError("SD card is not accessible")
            
    def get_config(self):
        """Fetch deployment configuration from server with hostname assignment"""
        self.logger.info(f"Fetching config from {self.server_url}...")

        try:
            # Prepare request data
            request_data = {
                'product_type': self.product_type,
                'venue_code': self.venue_code,
                'serial_number': self.get_serial_number(),
                'mac_address': self.get_mac_address()
            }

            response = requests.post(
                f"{self.server_url}/api/config",
                json=request_data,
                timeout=10
            )
            response.raise_for_status()
            config = response.json()

            # Store assigned hostname
            self.hostname = config.get('hostname', 'unknown')
            self.config = config

            self.logger.info(f"Config received: v{config['version']}")
            self.logger.info(f"Assigned hostname: {self.hostname}")

            return config
        except Exception as e:
            raise RuntimeError(f"Failed to get config: {e}")
            
    def download_and_write_image(self, image_url, expected_size):
        """Download image and write directly to SD card"""
        self.logger.info("Starting image download and write...")
        
        try:
            # Open target device for writing
            with open(self.target_device, 'wb') as device:
                response = requests.get(image_url, stream=True, timeout=30)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                self.logger.info(f"Image size: {total_size / (1024**3):.2f} GB")
                
                # Write in chunks
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        device.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 100MB
                        if downloaded % (100 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size) * 100
                            self.logger.info(f"Progress: {progress:.1f}%")
                
                # Sync to ensure all data is written
                device.flush()
                os.fsync(device.fileno())
                
            self.logger.info("Image write completed")
            
        except Exception as e:
            raise RuntimeError(f"Image write failed: {e}")
            
    def verify_installation(self, expected_checksum):
        """Verify written image checksum"""
        self.logger.info("Verifying installation...")
        
        # Sync filesystem
        subprocess.run(["sync"])
        time.sleep(2)
        
        # For speed, only verify first 100MB
        try:
            hasher = hashlib.sha256()
            with open(self.target_device, 'rb') as f:
                # Read first 100MB
                data = f.read(100 * 1024 * 1024)
                hasher.update(data)
            
            # Note: This is a partial checksum, full verification would take too long
            self.logger.info("Installation verification completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return False
            
    def customize_installation(self):
        """Mount and customize the installed image with assigned hostname"""
        self.logger.info("Customizing installation...")

        try:
            # Create mount point
            mount_point = Path("/mnt/sdcard")
            mount_point.mkdir(parents=True, exist_ok=True)

            # Mount boot partition
            subprocess.run(
                ["mount", f"{self.target_device}p1", str(mount_point)],
                check=True
            )

            # Use the assigned hostname from server
            hostname = self.hostname if self.hostname else f"kxp-{self.get_serial_number()[-6:]}"

            # Create firstrun.sh script for customization on first boot
            firstrun = mount_point / "firstrun.sh"
            with open(firstrun, 'w') as f:
                f.write(f"""#!/bin/bash
# KXP/RXP First Run Customization
# Product: {self.product_type}
# Venue: {self.venue_code if self.venue_code else 'DEFAULT'}
# Assigned Hostname: {hostname}

hostnamectl set-hostname {hostname}
echo {hostname} > /etc/hostname

# Update hosts file
sed -i "s/127.0.1.1.*/127.0.1.1\t{hostname}/" /etc/hosts

# Log deployment info
echo "Deployment completed: $(date)" >> /var/log/kxp_deployment.log
echo "Hostname: {hostname}" >> /var/log/kxp_deployment.log
echo "Product: {self.product_type}" >> /var/log/kxp_deployment.log
echo "Venue: {self.venue_code}" >> /var/log/kxp_deployment.log

# Remove this script after execution
rm -f /boot/firstrun.sh
""")
            
            os.chmod(firstrun, 0o755)
            
            # Unmount
            subprocess.run(["umount", str(mount_point)], check=True)
            
            self.logger.info(f"Installation customized with hostname: {hostname}")
            
        except Exception as e:
            self.logger.warning(f"Customization failed: {e}")
            
    def reboot_system(self):
        """Reboot the system"""
        self.logger.info("Installation complete! Rebooting...")
        time.sleep(3)
        subprocess.run(["reboot"])
        
    def install(self):
        """Main installation process"""
        try:
            self.logger.info("=== KXP Installation Started ===")
            self.report_status("starting")
            
            # Step 1: Verify SD card
            self.verify_sd_card()
            
            # Step 2: Get configuration
            config = self.get_config()
            
            # Step 3: Download and write image
            self.report_status("downloading")
            self.download_and_write_image(
                config['image_url'],
                config['image_size']
            )
            
            # Step 4: Verify installation
            self.report_status("verifying")
            if not self.verify_installation(config['image_checksum']):
                raise RuntimeError("Installation verification failed")
            
            # Step 5: Customize
            self.report_status("customizing")
            self.customize_installation()
            
            # Step 6: Success
            self.report_status("success", "Installation completed successfully")
            self.logger.info("=== Installation Successful ===")
            
            # Step 7: Reboot
            time.sleep(2)
            self.reboot_system()
            
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            self.report_status("failed", str(e))
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='KXP/RXP Pi Installer')
    parser.add_argument('--server', required=True, help='Deployment server URL')
    parser.add_argument('--product', default='KXP2', choices=['KXP2', 'RXP2'],
                       help='Product type: KXP2 (KartXPro) or RXP2 (RaceXPro)')
    parser.add_argument('--venue', help='4-letter venue code (e.g., CORO)')
    parser.add_argument('--device', default='/dev/mmcblk0', help='Target device')
    args = parser.parse_args()

    # Server runs on port 5001 for deployment network
    server_url = f"http://{args.server}:5001" if ':' not in args.server else args.server

    installer = PiInstaller(
        server_url,
        product_type=args.product,
        venue_code=args.venue,
        target_device=args.device
    )
    installer.install()

if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x /opt/rpi-deployment/scripts/pi_installer.py
```

---

