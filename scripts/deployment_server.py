#!/usr/bin/env python3
"""
Deployment Server Application (Deployment Network API)

Serves configuration and images to Raspberry Pi clients with hostname management.
Runs on port 5001 on deployment network (192.168.151.1).

Key Features:
- Hostname assignment via HostnameManager integration
- Master image serving with checksum verification
- Deployment history tracking in SQLite database
- Status reporting from clients
- Batch deployment support
- Health check endpoint

API Endpoints:
- POST /api/config - Provide deployment configuration with hostname assignment
- POST /api/status - Receive installation status reports from clients
- GET /images/<filename> - Serve master image files
- GET /health - Health check endpoint

Author: Raspberry Pi Deployment System
Date: 2025-10-23
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
from typing import Optional, Dict, Any

# Add scripts directory to path
sys.path.insert(0, '/opt/rpi-deployment/scripts')
from hostname_manager import HostnameManager

# Initialize Flask application
app = Flask('deployment_server')

# Configuration
DEPLOYMENT_IP = "192.168.151.1"  # Deployment network
IMAGE_DIR = Path("/opt/rpi-deployment/images")
LOG_DIR = Path("/opt/rpi-deployment/logs")
DB_PATH = Path("/opt/rpi-deployment/database/deployment.db")

# Initialize hostname manager
hostname_mgr = HostnameManager(str(DB_PATH))

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


def calculate_checksum(file_path: str) -> str:
    """
    Calculate SHA256 checksum of file.

    Args:
        file_path: Path to file

    Returns:
        Hex string of SHA256 checksum
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_active_image(product_type: str) -> Optional[Dict[str, Any]]:
    """
    Get the active master image for a product type.

    Args:
        product_type: 'KXP2' or 'RXP2'

    Returns:
        Dictionary with filename, checksum, size or None if no active image
    """
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
    """
    Provide deployment configuration to clients based on product/venue.

    Request JSON:
    {
        'product_type': 'KXP2' or 'RXP2',
        'venue_code': '4-letter venue code',
        'serial_number': 'Pi serial number',
        'mac_address': 'MAC address'
    }

    Response JSON:
    {
        'server_ip': '192.168.151.1',
        'hostname': 'Assigned hostname',
        'product_type': 'KXP2' or 'RXP2',
        'venue_code': 'Venue code',
        'image_url': 'HTTP URL to image',
        'image_size': Size in bytes,
        'image_checksum': 'SHA256 checksum',
        'version': 'API version',
        'timestamp': 'ISO timestamp'
    }

    Returns:
        JSON configuration or error (404 if no image, 500 on error)
    """
    try:
        data = request.json or {}
        product_type = data.get('product_type', 'KXP2')
        venue_code = data.get('venue_code')
        serial_number = data.get('serial_number')
        mac_address = data.get('mac_address')

        # Check for active batch first
        active_batch = hostname_mgr.get_active_batch()
        hostname = None

        if active_batch:
            # Assign from batch
            try:
                hostname = hostname_mgr.assign_from_batch(
                    active_batch['id'],
                    mac_address or 'unknown',
                    serial_number or 'unknown'
                )
                venue_code = active_batch['venue_code']
                product_type = active_batch['product_type']
                logger.info(f"Assigned from batch {active_batch['id']}: {hostname}")
            except Exception as e:
                logger.warning(f"Failed to assign from batch: {e}")
                # Fall through to regular assignment

        # If no batch assignment, use regular assignment
        if not hostname and venue_code:
            hostname = hostname_mgr.assign_hostname(
                product_type,
                venue_code,
                mac_address,
                serial_number
            )

        # Fallback hostname if assignment failed
        if not hostname:
            hostname = f"{product_type}-DEFAULT-{serial_number[-6:]}" if serial_number else "unknown"

        # Get active image for product type
        image_info = get_active_image(product_type)
        if not image_info:
            # Fallback to default image
            image_filename = f"{product_type.lower()}_master.img"
            image_path = IMAGE_DIR / image_filename
            if not image_path.exists():
                logger.error(f"No active image for {product_type}")
                return jsonify({'error': f'No active image for {product_type}'}), 404

            image_info = {
                'filename': image_filename,
                'checksum': calculate_checksum(str(image_path)),
                'size': image_path.stat().st_size
            }

        config = {
            'server_ip': DEPLOYMENT_IP,
            'hostname': hostname,
            'product_type': product_type,
            'venue_code': venue_code,
            'image_url': f'http://{DEPLOYMENT_IP}:8888/images/{image_info["filename"]}',
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
    """
    Receive installation status from clients.

    Request JSON:
    {
        'status': 'starting' | 'downloading' | 'verifying' | 'customizing' | 'success' | 'failed',
        'hostname': 'Assigned hostname',
        'serial': 'Pi serial number',
        'mac_address': 'MAC address',
        'message': 'Optional status message',
        'error_message': 'Error message if failed',
        'timestamp': Unix timestamp
    }

    Response JSON:
    {
        'received': true,
        'hostname': 'Hostname'
    }

    Returns:
        JSON acknowledgment or error (500 on error)
    """
    try:
        data = request.json or {}
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
                    AND deployment_status != 'success'
                    AND deployment_status != 'failed'
                    ORDER BY started_at DESC
                    LIMIT 1
                ''', (status, error_message, hostname))
            else:
                # Update deployment progress
                cursor.execute('''
                    UPDATE deployment_history
                    SET deployment_status = ?
                    WHERE hostname = ?
                    AND deployment_status NOT IN ('success', 'failed')
                    ORDER BY started_at DESC
                    LIMIT 1
                ''', (status, hostname))

        # Log to daily file
        status_log = LOG_DIR / f"deployment_{datetime.now().strftime('%Y%m%d')}.log"
        with open(status_log, 'a') as f:
            f.write(f"{datetime.now().isoformat()},{client_ip},{hostname},{serial},{status}\n")

        return jsonify({'received': True, 'hostname': hostname})

    except Exception as e:
        logger.error(f"Error receiving status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/images/<filename>', methods=['GET'])
def download_image(filename: str):
    """
    Serve master image for download.

    Args:
        filename: Image filename (e.g., 'kxp2_master.img')

    Returns:
        Binary file download or error (404 if not found, 500 on error)
    """
    try:
        image_path = IMAGE_DIR / filename

        if not image_path.exists():
            logger.warning(f"Image not found: {filename}")
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
    """
    Health check endpoint.

    Returns:
        JSON with status and timestamp
    """
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
        initialize_database(str(DB_PATH))
        logger.info("Database initialized")

    logger.info("Starting deployment server on deployment network")
    logger.info(f"Deployment API: http://{DEPLOYMENT_IP}:5001")

    # Start server (on deployment network port)
    app.run(host='0.0.0.0', port=5001, debug=False)
