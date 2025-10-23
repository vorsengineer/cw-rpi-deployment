"""Flask web management interface for RPi5 Network Deployment System.

This application provides a web-based interface for managing venues, kart numbers,
and monitoring deployments for the Raspberry Pi mass deployment system.
"""

import os
import sys
import subprocess
import sqlite3
import re
import threading
import time
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from wtforms import Form, StringField, TextAreaField, SelectField, validators
from wtforms.validators import ValidationError

# Add scripts directory to path for HostnameManager import
sys.path.insert(0, '/opt/rpi-deployment/scripts')
from hostname_manager import HostnameManager

# Import configuration
from config import get_config

# Configure logging
LOG_DIR = Path("/opt/rpi-deployment/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "web_app.log"),
        logging.StreamHandler()  # Also to stdout for systemd journal
    ]
)

logger = logging.getLogger("WebApp")

# Global SocketIO instance (initialized in create_app)
socketio = None


def create_app(config_dict: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Create and configure Flask application with WebSocket support.

    Args:
        config_dict: Optional configuration dictionary (used for testing)

    Returns:
        Flask: Configured Flask application instance with SocketIO initialized
    """
    global socketio

    app = Flask(__name__)

    # Load configuration
    if config_dict:
        app.config.update(config_dict)
    else:
        config_obj = get_config()
        app.config.from_object(config_obj)

    # Initialize extensions
    CORS(app)

    # Initialize SocketIO with app
    cors_origins = app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '*')
    socketio = SocketIO(app, cors_allowed_origins=cors_origins, async_mode='threading')

    # Initialize HostnameManager and store in app context
    db_path = app.config['DATABASE_PATH']
    app.hostname_manager = HostnameManager(db_path)

    # Register error handlers
    register_error_handlers(app)

    # Register routes
    register_routes(app)

    # Register WebSocket event handlers
    register_websocket_handlers(app, socketio)

    # Start background thread for periodic stats updates
    start_background_thread(app, socketio)

    return app


def register_error_handlers(app: Flask) -> None:
    """
    Register error handlers for the application.

    Args:
        app: Flask application instance
    """
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('500.html'), 500


def register_routes(app: Flask) -> None:
    """
    Register all application routes.

    Args:
        app: Flask application instance
    """
    # Dashboard routes
    @app.route('/')
    def dashboard():
        """Display main dashboard with statistics and recent deployments."""
        manager = current_app.hostname_manager

        # Get overall statistics
        stats = get_dashboard_stats(manager)

        # Get recent deployments
        recent_deployments = get_recent_deployments(manager, limit=10)

        # Get system status
        system_status = get_system_status()

        return render_template('dashboard.html',
                             stats=stats,
                             recent_deployments=recent_deployments,
                             system_status=system_status)

    # Venue management routes
    @app.route('/venues')
    def venues_list():
        """Display list of all venues."""
        manager = current_app.hostname_manager
        venues = manager.list_venues()
        return render_template('venues.html', venues=venues)

    @app.route('/venues/<code>')
    def venue_detail(code: str):
        """
        Display venue detail page with statistics.

        Args:
            code: Venue code (4-letter uppercase)
        """
        manager = current_app.hostname_manager

        # Check if venue exists
        venues = manager.list_venues()
        venue = None
        for v in venues:
            if v['code'] == code:
                venue = v
                break

        if not venue:
            flash(f'Venue "{code}" not found.', 'error')
            return render_template('404.html'), 404

        # Get venue statistics
        stats = manager.get_venue_statistics(code)

        return render_template('venue_detail.html', venue=venue, stats=stats)

    @app.route('/venues/create', methods=['GET', 'POST'])
    def venue_create():
        """Create new venue."""
        form = VenueForm(request.form)

        if request.method == 'POST' and form.validate():
            manager = current_app.hostname_manager
            code = form.code.data.upper().strip()
            name = form.name.data.strip()
            location = form.location.data.strip() if form.location.data else ''
            contact_email = form.contact_email.data.strip() if form.contact_email.data else ''

            try:
                manager.create_venue(code, name, location, contact_email)
                flash(f'Venue "{code}" created successfully!', 'success')
                return redirect(url_for('venues_list'))
            except ValueError as e:
                flash(f'Error creating venue: {str(e)}', 'error')
            except sqlite3.IntegrityError:
                flash(f'Venue code "{code}" already exists.', 'error')

        return render_template('venue_form.html', form=form, action='create')

    @app.route('/venues/<code>/edit', methods=['GET', 'POST'])
    def venue_edit(code: str):
        """
        Edit existing venue.

        Args:
            code: Venue code
        """
        manager = current_app.hostname_manager

        # Check if venue exists
        venues = manager.list_venues()
        venue = None
        for v in venues:
            if v['code'] == code:
                venue = v
                break

        if not venue:
            flash(f'Venue "{code}" not found.', 'error')
            return render_template('404.html'), 404

        if request.method == 'POST':
            form = VenueEditForm(request.form)
            if form.validate():
                name = form.name.data.strip()
                location = form.location.data.strip() if form.location.data else ''
                contact_email = form.contact_email.data.strip() if form.contact_email.data else ''

                try:
                    conn = manager._get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE venues
                        SET name = ?, location = ?, contact_email = ?
                        WHERE code = ?
                    """, (name, location, contact_email, code))
                    conn.commit()

                    flash(f'Venue "{code}" updated successfully!', 'success')
                    return redirect(url_for('venue_detail', code=code))
                except Exception as e:
                    flash(f'Error updating venue: {str(e)}', 'error')
        else:
            # Pre-populate form with existing data
            form = VenueEditForm(data=venue)

        return render_template('venue_form.html', form=form, action='edit', venue_code=code)

    # Kart number management routes
    @app.route('/kart-numbers')
    def kart_numbers_list():
        """Display list of kart numbers with optional venue filter."""
        manager = current_app.hostname_manager
        venue_filter = request.args.get('venue', '').strip().upper()

        # Get all venues for filter dropdown
        venues = manager.list_venues()

        # Get kart numbers
        conn = manager._get_connection()
        cursor = conn.cursor()

        if venue_filter:
            cursor.execute("""
                SELECT id, product_type, venue_code, identifier, status,
                       mac_address, assigned_date
                FROM hostname_pool
                WHERE venue_code = ?
                ORDER BY product_type, identifier
            """, (venue_filter,))
        else:
            cursor.execute("""
                SELECT id, product_type, venue_code, identifier, status,
                       mac_address, assigned_date
                FROM hostname_pool
                ORDER BY venue_code, product_type, identifier
            """)

        kart_numbers = []
        for row in cursor.fetchall():
            # Build hostname dynamically
            hostname = f"{row[1]}-{row[2]}-{row[3]}"  # product_type-venue_code-identifier
            kart_numbers.append({
                'id': row[0],
                'hostname': hostname,
                'venue_code': row[2],
                'product_type': row[1],
                'kart_number': row[3],  # identifier is the kart number
                'status': row[4],
                'mac_address': row[5],
                'assigned_date': row[6]
            })

        return render_template('kart_numbers.html',
                             kart_numbers=kart_numbers,
                             venues=venues,
                             venue_filter=venue_filter)

    @app.route('/kart-numbers/bulk-import', methods=['GET', 'POST'])
    def kart_numbers_bulk_import():
        """Bulk import kart numbers for a venue."""
        manager = current_app.hostname_manager
        venues = manager.list_venues()

        form = BulkImportForm(request.form)
        form.venue_code.choices = [('', 'Select Venue')] + [(v['code'], f"{v['code']} - {v['name']}") for v in venues]

        if request.method == 'POST' and form.validate():
            venue_code = form.venue_code.data
            kart_numbers_str = form.kart_numbers.data
            product_type = request.form.get('product_type', 'KXP2')  # Default to KXP2

            # Parse kart numbers (comma or newline separated)
            kart_numbers = re.split(r'[,\n]+', kart_numbers_str)
            kart_numbers = [num.strip() for num in kart_numbers if num.strip()]

            try:
                result = manager.bulk_import_kart_numbers(venue_code, kart_numbers, product_type=product_type)
                imported = result['imported']
                duplicates = result['duplicates']

                if imported > 0:
                    flash(f'Successfully imported {imported} kart numbers for venue {venue_code}.', 'success')
                if duplicates > 0:
                    flash(f'{duplicates} kart numbers were already in the pool (skipped duplicates).', 'warning')

                return redirect(url_for('kart_numbers_list', venue=venue_code))
            except ValueError as e:
                flash(f'Error importing kart numbers: {str(e)}', 'error')

        return render_template('bulk_import.html', form=form)

    @app.route('/kart-numbers/add', methods=['POST'])
    def kart_numbers_add():
        """Add a single kart number."""
        manager = current_app.hostname_manager
        venue_code = request.form.get('venue_code', '').strip().upper()
        kart_number = request.form.get('kart_number', '').strip()

        if not venue_code or not kart_number:
            flash('Venue code and kart number are required.', 'error')
            return redirect(url_for('kart_numbers_list'))

        try:
            result = manager.bulk_import_kart_numbers(venue_code, [kart_number])
            if result['imported'] > 0:
                flash(f'Kart number {kart_number} added successfully!', 'success')
            else:
                flash(f'Kart number {kart_number} already exists in the pool.', 'warning')
        except ValueError as e:
            flash(f'Error adding kart number: {str(e)}', 'error')

        return redirect(url_for('kart_numbers_list', venue=venue_code))

    @app.route('/kart-numbers/<hostname>/delete', methods=['POST'])
    def kart_numbers_delete(hostname: str):
        """
        Delete (release) a kart number.

        Args:
            hostname: Hostname to release
        """
        manager = current_app.hostname_manager

        try:
            success = manager.release_hostname(hostname)
            if success:
                flash(f'Hostname "{hostname}" released successfully.', 'success')
            else:
                flash(f'Hostname "{hostname}" not found or already released.', 'warning')
        except Exception as e:
            flash(f'Error releasing hostname: {str(e)}', 'error')

        return redirect(url_for('kart_numbers_list'))

    # Deployment monitoring routes
    @app.route('/deployments')
    def deployments_list():
        """Display deployment history with filters."""
        manager = current_app.hostname_manager

        # Get filter parameters
        venue_filter = request.args.get('venue', '').strip().upper()
        product_filter = request.args.get('product', '').strip().upper()
        status_filter = request.args.get('status', '').strip().lower()
        page = max(1, int(request.args.get('page', 1)))
        limit = current_app.config['ITEMS_PER_PAGE']
        offset = (page - 1) * limit

        # Build query
        query = """
            SELECT id, hostname, mac_address, serial_number, product_type, venue_code,
                   ip_address, deployment_status, started_at, completed_at, error_message
            FROM deployment_history
            WHERE 1=1
        """
        params = []

        if venue_filter:
            query += " AND venue_code = ?"
            params.append(venue_filter)
        if product_filter:
            query += " AND product_type = ?"
            params.append(product_filter)
        if status_filter:
            query += " AND deployment_status = ?"
            params.append(status_filter)

        query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Execute query
        conn = manager._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)

        deployments = []
        for row in cursor.fetchall():
            deployments.append({
                'id': row[0],
                'hostname': row[1],
                'mac_address': row[2],
                'serial_number': row[3],
                'product_type': row[4],
                'venue_code': row[5],
                'ip_address': row[6],
                'status': row[7],
                'started_at': row[8],
                'completed_at': row[9],
                'error_message': row[10]
            })

        # Get venues for filter dropdown
        venues = manager.list_venues()

        return render_template('deployments.html',
                             deployments=deployments,
                             venues=venues,
                             venue_filter=venue_filter,
                             product_filter=product_filter,
                             status_filter=status_filter,
                             page=page)

    # Deployment batch management routes
    @app.route('/batches')
    def batches_list():
        """Display list of all deployment batches."""
        manager = current_app.hostname_manager

        # Get filter parameters
        venue_filter = request.args.get('venue', '').strip().upper() if request.args.get('venue') else None
        status_filter = request.args.get('status', '').strip().lower() if request.args.get('status') else None

        # Get batches with filters
        batches = manager.get_all_batches(venue_code=venue_filter, status=status_filter)

        # Get venues for filter dropdown
        venues = manager.list_venues()

        return render_template('batches.html',
                             batches=batches,
                             venues=venues,
                             venue_filter=venue_filter or '',
                             status_filter=status_filter or '')

    @app.route('/batches/create', methods=['GET', 'POST'])
    def batch_create():
        """Create new deployment batch."""
        manager = current_app.hostname_manager
        venues = manager.list_venues()

        if request.method == 'POST':
            venue_code = request.form.get('venue_code', '').strip().upper()
            product_type = request.form.get('product_type', '').strip().upper()
            total_count = request.form.get('total_count', '').strip()
            priority = request.form.get('priority', '0').strip()

            try:
                total_count = int(total_count)
                priority = int(priority)

                batch_id = manager.create_deployment_batch(
                    venue_code=venue_code,
                    product_type=product_type,
                    total_count=total_count,
                    priority=priority
                )

                flash(f'Deployment batch created successfully (ID: {batch_id})!', 'success')
                return redirect(url_for('batches_list'))
            except ValueError as e:
                flash(f'Error creating batch: {str(e)}', 'error')
            except Exception as e:
                flash(f'Unexpected error: {str(e)}', 'error')

        return render_template('batch_create.html', venues=venues)

    @app.route('/batches/<int:batch_id>/start', methods=['POST'])
    def batch_start(batch_id: int):
        """Start a deployment batch."""
        manager = current_app.hostname_manager

        try:
            manager.start_batch(batch_id)
            flash(f'Batch {batch_id} started successfully.', 'success')
        except ValueError as e:
            flash(f'Error starting batch: {str(e)}', 'error')
        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'error')

        return redirect(url_for('batches_list'))

    @app.route('/batches/<int:batch_id>/pause', methods=['POST'])
    def batch_pause(batch_id: int):
        """Pause a deployment batch."""
        manager = current_app.hostname_manager

        try:
            manager.pause_batch(batch_id)
            flash(f'Batch {batch_id} paused successfully.', 'success')
        except ValueError as e:
            flash(f'Error pausing batch: {str(e)}', 'error')
        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'error')

        return redirect(url_for('batches_list'))

    @app.route('/batches/<int:batch_id>/priority', methods=['POST'])
    def batch_update_priority(batch_id: int):
        """Update batch priority."""
        manager = current_app.hostname_manager

        try:
            priority = int(request.form.get('priority', '0'))
            manager.update_batch_priority(batch_id, priority)
            flash(f'Batch {batch_id} priority updated to {priority}.', 'success')
        except ValueError as e:
            flash(f'Error updating priority: {str(e)}', 'error')
        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'error')

        return redirect(url_for('batches_list'))

    # System status routes
    @app.route('/system')
    def system_status():
        """Display system status and monitoring information."""
        status = get_system_status()
        return render_template('system.html', status=status)

    # API endpoints (JSON)
    @app.route('/api/stats')
    def api_stats():
        """Get dashboard statistics as JSON."""
        manager = current_app.hostname_manager
        stats = get_dashboard_stats(manager)
        return jsonify(stats)

    @app.route('/api/venues')
    def api_venues():
        """Get list of venues as JSON."""
        manager = current_app.hostname_manager
        venues = manager.list_venues()
        return jsonify(venues)

    @app.route('/api/venues/<code>/stats')
    def api_venue_stats(code: str):
        """
        Get venue statistics as JSON.

        Args:
            code: Venue code
        """
        manager = current_app.hostname_manager

        # Check if venue exists
        venues = manager.list_venues()
        if not any(v['code'] == code for v in venues):
            return jsonify({'error': 'Venue not found'}), 404

        stats = manager.get_venue_statistics(code)
        return jsonify(stats)

    @app.route('/api/deployments')
    def api_deployments():
        """Get recent deployments as JSON."""
        manager = current_app.hostname_manager
        limit = min(int(request.args.get('limit', 20)), current_app.config['MAX_ITEMS_PER_PAGE'])

        deployments = get_recent_deployments(manager, limit=limit)
        return jsonify(deployments)

    @app.route('/api/system/status')
    def api_system_status():
        """Get system status as JSON."""
        status = get_system_status()
        return jsonify(status)

    # Batch management API endpoints
    @app.route('/api/batches')
    def api_batches_list():
        """
        Get all deployment batches as JSON.

        Query params:
            venue: Filter by venue code (optional)
            status: Filter by status (optional)
        """
        manager = current_app.hostname_manager

        venue_filter = request.args.get('venue', '').strip().upper() if request.args.get('venue') else None
        status_filter = request.args.get('status', '').strip().lower() if request.args.get('status') else None

        batches = manager.get_all_batches(venue_code=venue_filter, status=status_filter)
        return jsonify(batches)

    @app.route('/api/batches/<int:batch_id>')
    def api_batch_detail(batch_id: int):
        """Get batch details by ID as JSON."""
        manager = current_app.hostname_manager

        batch = manager.get_batch_by_id(batch_id)
        if not batch:
            return jsonify({'error': 'Batch not found'}), 404

        return jsonify(batch)

    @app.route('/api/batches/active')
    def api_active_batch():
        """Get the highest priority active batch as JSON."""
        manager = current_app.hostname_manager

        batch = manager.get_active_batch()
        if not batch:
            return jsonify({'message': 'No active batches'}), 404

        return jsonify(batch)

    @app.route('/api/batches', methods=['POST'])
    def api_batch_create():
        """Create new deployment batch via API."""
        manager = current_app.hostname_manager

        try:
            data = request.get_json()

            venue_code = data.get('venue_code', '').strip().upper()
            product_type = data.get('product_type', '').strip().upper()
            total_count = int(data.get('total_count', 0))
            priority = int(data.get('priority', 0))

            batch_id = manager.create_deployment_batch(
                venue_code=venue_code,
                product_type=product_type,
                total_count=total_count,
                priority=priority
            )

            batch = manager.get_batch_by_id(batch_id)
            return jsonify(batch), 201
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

    @app.route('/api/batches/<int:batch_id>/start', methods=['POST'])
    def api_batch_start(batch_id: int):
        """Start a deployment batch via API."""
        manager = current_app.hostname_manager

        try:
            manager.start_batch(batch_id)
            batch = manager.get_batch_by_id(batch_id)
            return jsonify(batch)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

    @app.route('/api/batches/<int:batch_id>/pause', methods=['POST'])
    def api_batch_pause(batch_id: int):
        """Pause a deployment batch via API."""
        manager = current_app.hostname_manager

        try:
            manager.pause_batch(batch_id)
            batch = manager.get_batch_by_id(batch_id)
            return jsonify(batch)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

    @app.route('/api/batches/<int:batch_id>/priority', methods=['PUT'])
    def api_batch_update_priority(batch_id: int):
        """Update batch priority via API."""
        manager = current_app.hostname_manager

        try:
            data = request.get_json()
            priority = int(data.get('priority', 0))

            manager.update_batch_priority(batch_id, priority)
            batch = manager.get_batch_by_id(batch_id)
            return jsonify(batch)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


# Helper functions

def get_dashboard_stats(manager: HostnameManager) -> Dict[str, Any]:
    """
    Get dashboard statistics for WebSocket and dashboard display.

    Args:
        manager: HostnameManager instance

    Returns:
        dict: Dashboard statistics with product-specific breakdowns
    """
    conn = manager._get_connection()
    cursor = conn.cursor()

    # Count venues
    cursor.execute("SELECT COUNT(*) FROM venues")
    total_venues = cursor.fetchone()[0]

    # Count total hostnames
    cursor.execute("SELECT COUNT(*) FROM hostname_pool")
    total_hostnames = cursor.fetchone()[0]

    # Count available hostnames by product
    cursor.execute("""
        SELECT COUNT(*) FROM hostname_pool
        WHERE status = 'available' AND product_type = 'KXP2'
    """)
    available_kxp2 = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM hostname_pool
        WHERE status = 'available' AND product_type = 'RXP2'
    """)
    available_rxp2 = cursor.fetchone()[0]

    # Count assigned hostnames by product
    cursor.execute("""
        SELECT COUNT(*) FROM hostname_pool
        WHERE status = 'assigned' AND product_type = 'KXP2'
    """)
    assigned_kxp2 = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM hostname_pool
        WHERE status = 'assigned' AND product_type = 'RXP2'
    """)
    assigned_rxp2 = cursor.fetchone()[0]

    # Count all available and assigned (totals)
    available_hostnames = available_kxp2 + available_rxp2
    assigned_hostnames = assigned_kxp2 + assigned_rxp2

    # Count recent deployments (last 24 hours)
    cursor.execute("""
        SELECT COUNT(*) FROM deployment_history
        WHERE started_at >= datetime('now', '-1 day')
    """)
    recent_deployments_count = cursor.fetchone()[0]

    # Count successful deployments (last 24 hours)
    cursor.execute("""
        SELECT COUNT(*) FROM deployment_history
        WHERE started_at >= datetime('now', '-1 day')
        AND deployment_status = 'completed'
    """)
    successful_deployments = cursor.fetchone()[0]

    # Get recent deployments list (for WebSocket updates)
    cursor.execute("""
        SELECT hostname, deployment_status, started_at, completed_at
        FROM deployment_history
        ORDER BY started_at DESC
        LIMIT 10
    """)
    recent_deployments_list = []
    for row in cursor.fetchall():
        recent_deployments_list.append({
            'hostname': row[0],
            'status': row[1],
            'started_at': row[2],
            'completed_at': row[3]
        })

    return {
        'total_venues': total_venues,
        'total_hostnames': total_hostnames,
        'available_kxp2': available_kxp2,
        'available_rxp2': available_rxp2,
        'assigned_kxp2': assigned_kxp2,
        'assigned_rxp2': assigned_rxp2,
        'available_hostnames': available_hostnames,
        'assigned_hostnames': assigned_hostnames,
        'recent_deployments': recent_deployments_list,
        'recent_deployments_count': recent_deployments_count,
        'successful_deployments': successful_deployments,
        'timestamp': datetime.now().isoformat()
    }


def get_recent_deployments(manager: HostnameManager, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent deployments.

    Args:
        manager: HostnameManager instance
        limit: Maximum number of deployments to return

    Returns:
        list: List of recent deployment records
    """
    conn = manager._get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, hostname, mac_address, serial_number, product_type, venue_code,
               ip_address, deployment_status, started_at, completed_at, error_message
        FROM deployment_history
        ORDER BY started_at DESC
        LIMIT ?
    """, (limit,))

    deployments = []
    for row in cursor.fetchall():
        deployments.append({
            'id': row[0],
            'hostname': row[1],
            'mac_address': row[2],
            'serial_number': row[3],
            'product_type': row[4],
            'venue_code': row[5],
            'ip_address': row[6],
            'status': row[7],
            'started_at': row[8],
            'completed_at': row[9],
            'error_message': row[10]
        })

    return deployments


def check_service_status(service_name: str) -> Dict[str, Any]:
    """
    Check if a systemd service is running.

    Args:
        service_name: Name of the systemd service

    Returns:
        dict: Service status with 'running' (bool) and 'status' (str) keys
    """
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_running = result.returncode == 0
        status = result.stdout.strip() if result.stdout else 'unknown'

        return {
            'running': is_running,
            'status': status
        }
    except Exception as e:
        return {
            'running': False,
            'status': f'error: {str(e)}'
        }


def check_database_connectivity(db_path: str) -> Dict[str, Any]:
    """
    Check database connectivity and size.

    Args:
        db_path: Path to SQLite database file

    Returns:
        dict: Database status with 'accessible' (bool) and 'size_mb' (float) keys
    """
    try:
        # Check if file exists and is accessible
        if not os.path.exists(db_path):
            return {'accessible': False, 'size_mb': 0.0}

        # Try to connect
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master")
        cursor.fetchone()
        conn.close()

        # Get file size in MB
        size_bytes = os.path.getsize(db_path)
        size_mb = size_bytes / (1024 * 1024)

        return {
            'accessible': True,
            'size_mb': round(size_mb, 2)
        }
    except Exception as e:
        return {
            'accessible': False,
            'size_mb': 0.0,
            'error': str(e)
        }


def get_disk_usage(path: str = '/opt/rpi-deployment') -> Dict[str, Any]:
    """
    Get disk space usage for the deployment directory.

    Args:
        path: Path to check disk usage for

    Returns:
        dict: Disk usage with total_gb, used_gb, available_gb, percent_used keys
    """
    try:
        stat = shutil.disk_usage(path)
        total_gb = stat.total / (1024 ** 3)
        used_gb = stat.used / (1024 ** 3)
        free_gb = stat.free / (1024 ** 3)
        percent_used = (stat.used / stat.total) * 100 if stat.total > 0 else 0

        return {
            'total_gb': round(total_gb, 2),
            'used_gb': round(used_gb, 2),
            'available_gb': round(free_gb, 2),
            'percent_used': round(percent_used, 1)
        }
    except Exception as e:
        return {
            'total_gb': 0.0,
            'used_gb': 0.0,
            'available_gb': 0.0,
            'percent_used': 0.0,
            'error': str(e)
        }


def get_system_status(db_path: str = '/opt/rpi-deployment/database/deployment.db') -> Dict[str, Any]:
    """
    Get comprehensive system status for WebSocket broadcasts and API.

    Args:
        db_path: Path to database file for connectivity check

    Returns:
        dict: System status including service health, database, and disk space

    Note:
        For WebSocket use, call get_system_status_websocket()
        This function maintains backwards compatibility with existing templates/tests
    """
    # Get individual service statuses
    dnsmasq_status = check_service_status('dnsmasq')
    nginx_status = check_service_status('nginx')

    # Maintain backward compatibility with old structure
    services = {
        'dnsmasq': dnsmasq_status.get('status', 'unknown'),
        'nginx': nginx_status.get('status', 'unknown')
    }

    # Get disk space
    try:
        result = subprocess.run(
            ['df', '-h', '/opt/rpi-deployment'],
            capture_output=True,
            text=True,
            timeout=5
        )
        disk_output = result.stdout if result.returncode == 0 else ''
    except Exception:
        disk_output = ''

    # Get network info
    try:
        result = subprocess.run(
            ['ip', 'addr', 'show'],
            capture_output=True,
            text=True,
            timeout=5
        )
        network_output = result.stdout[:500] if result.returncode == 0 else ''
    except Exception:
        network_output = ''

    return {
        'services': services,
        'network': {
            'interfaces': 'ok' if network_output else 'unknown',
            'output': network_output
        },
        'disk': {
            'status': 'ok' if disk_output else 'unknown',
            'output': disk_output
        },
        'timestamp': datetime.now().isoformat()
    }


def get_system_status_websocket(db_path: str = '/opt/rpi-deployment/database/deployment.db') -> Dict[str, Any]:
    """
    Get system status formatted for WebSocket broadcasts.

    Args:
        db_path: Path to database file for connectivity check

    Returns:
        dict: System status with detailed service health, database, and disk space
    """
    return {
        'dnsmasq': check_service_status('dnsmasq'),
        'nginx': check_service_status('nginx'),
        'database': check_database_connectivity(db_path),
        'disk_space': get_disk_usage(),
        'timestamp': datetime.now().isoformat()
    }


def broadcast_deployment_update(socketio_instance, deployment_data: Dict[str, Any]) -> None:
    """
    Broadcast deployment status update to all connected clients.

    Args:
        socketio_instance: SocketIO instance for broadcasting
        deployment_data: Deployment information to broadcast

    Expected deployment_data keys:
        - deployment_id: int
        - hostname: str
        - mac_address: str
        - serial_number: str (optional)
        - status: str (starting, downloading, verifying, customizing, success, failed)
        - timestamp: str (ISO format)
    """
    if socketio_instance:
        socketio_instance.emit('deployment_update', deployment_data, namespace='/')


# WebSocket Event Handlers

def register_websocket_handlers(app: Flask, socketio_instance: SocketIO) -> None:
    """
    Register all WebSocket event handlers.

    Args:
        app: Flask application instance
        socketio_instance: SocketIO instance
    """

    @socketio_instance.on('connect')
    def handle_connect():
        """
        Handle client connection.

        Sends:
            - 'status' event with connection confirmation
            - 'stats_update' event with initial statistics
        """
        emit('status', {
            'message': 'Connected to deployment server',
            'timestamp': datetime.now().isoformat()
        })

        # Send initial stats immediately on connect
        try:
            stats = get_dashboard_stats(app.hostname_manager)
            emit('stats_update', stats)
        except Exception as e:
            emit('status', {
                'message': f'Error loading initial stats: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })

    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        pass  # Clean disconnect, no action needed

    @socketio_instance.on('request_stats')
    def handle_request_stats():
        """
        Handle manual stats request from client.

        Sends:
            - 'stats_update' event with current statistics (broadcast to all clients)

        Note:
            This broadcasts to all clients so everyone stays in sync
        """
        try:
            stats = get_dashboard_stats(app.hostname_manager)
            # Broadcast to all clients (not just the requester)
            socketio_instance.emit('stats_update', stats, namespace='/')
        except Exception as e:
            emit('status', {
                'message': f'Error retrieving stats: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })

    @socketio_instance.on('request_deployments')
    def handle_request_deployments():
        """
        Handle request for deployments list.

        Sends:
            - 'deployments_refresh' event with recent deployments
        """
        try:
            deployments = get_recent_deployments(app.hostname_manager, limit=50)
            emit('deployments_refresh', {'deployments': deployments})
        except Exception as e:
            emit('status', {
                'message': f'Error retrieving deployments: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })

    @socketio_instance.on('request_system_status')
    def handle_request_system_status():
        """
        Handle request for system status.

        Sends:
            - 'system_status' event with service health and disk space
        """
        try:
            db_path = app.config.get('DATABASE_PATH', '/opt/rpi-deployment/database/deployment.db')
            status = get_system_status_websocket(db_path)
            emit('system_status', status)
        except Exception as e:
            emit('status', {
                'message': f'Error retrieving system status: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })

    @socketio_instance.on('trigger_deployment_update')
    def handle_trigger_deployment_update(data):
        """
        Handle deployment status update trigger (for testing and actual deployments).

        This event is used both in tests and by the actual deployment system
        to broadcast status changes to all connected clients.

        Args:
            data: Deployment information dictionary

        Broadcasts:
            - 'deployment_update' event to all clients
        """
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()

        # Broadcast to all clients (don't use broadcast parameter, just emit to namespace)
        socketio_instance.emit('deployment_update', data, namespace='/')


# Background Tasks

# Flag to track if background thread is running
_background_thread = None
_background_thread_stop = False


def start_background_thread(app: Flask, socketio_instance: SocketIO) -> None:
    """
    Start background thread for periodic stats updates.

    Args:
        app: Flask application instance
        socketio_instance: SocketIO instance for broadcasts
    """
    global _background_thread, _background_thread_stop

    # Don't start background thread in testing mode
    if app.config.get('TESTING', False):
        return

    # Don't start if already running
    if _background_thread is not None:
        return

    _background_thread_stop = False

    def background_stats_updater():
        """Background thread that broadcasts stats every 5 seconds."""
        global _background_thread_stop

        while not _background_thread_stop:
            # Sleep first (so tests don't have to wait on first call)
            time.sleep(5)

            if _background_thread_stop:
                break

            try:
                with app.app_context():
                    stats = get_dashboard_stats(app.hostname_manager)
                    socketio_instance.emit('stats_update', stats, namespace='/')
            except Exception as e:
                # Log error but don't stop the thread
                print(f"Error in background stats updater: {e}")

    _background_thread = threading.Thread(target=background_stats_updater, daemon=True)
    _background_thread.start()


def stop_background_thread() -> None:
    """Stop the background stats update thread."""
    global _background_thread, _background_thread_stop
    _background_thread_stop = True
    if _background_thread:
        _background_thread.join(timeout=1)
        _background_thread = None


# Form classes

class VenueForm(Form):
    """Form for creating a new venue."""

    code = StringField('Venue Code', [
        validators.DataRequired(message='Venue code is required'),
        validators.Length(min=4, max=4, message='Venue code must be exactly 4 characters'),
        validators.Regexp(r'^[A-Za-z]{4}$', message='Venue code must contain only letters')
    ])
    name = StringField('Venue Name', [
        validators.DataRequired(message='Venue name is required'),
        validators.Length(min=1, max=100, message='Venue name must be 1-100 characters')
    ])
    location = StringField('Location', [
        validators.Optional(),
        validators.Length(max=100, message='Location must be less than 100 characters')
    ])
    contact_email = StringField('Contact Email', [
        validators.Optional(),
        validators.Email(message='Invalid email address')
    ])


class VenueEditForm(Form):
    """Form for editing an existing venue (cannot change code)."""

    name = StringField('Venue Name', [
        validators.DataRequired(message='Venue name is required'),
        validators.Length(min=1, max=100, message='Venue name must be 1-100 characters')
    ])
    location = StringField('Location', [
        validators.Optional(),
        validators.Length(max=100, message='Location must be less than 100 characters')
    ])
    contact_email = StringField('Contact Email', [
        validators.Optional(),
        validators.Email(message='Invalid email address')
    ])


class BulkImportForm(Form):
    """Form for bulk importing kart numbers."""

    venue_code = SelectField('Venue', [
        validators.DataRequired(message='Please select a venue')
    ])
    kart_numbers = TextAreaField('Kart Numbers', [
        validators.DataRequired(message='Please enter at least one kart number'),
        validators.Length(min=1, max=10000, message='Too many kart numbers')
    ], description='Enter kart numbers separated by commas or newlines (e.g., 001, 002, 003)')


# Application entry point

if __name__ == '__main__':
    # Create app with default configuration (SocketIO already initialized in create_app)
    app = create_app()

    # Run application
    host = '0.0.0.0'  # Listen on all interfaces
    port = app.config.get('MANAGEMENT_PORT', 5000)

    print(f"Starting Flask web management interface on {host}:{port}")
    print(f"Database: {app.config['DATABASE_PATH']}")
    print("WebSocket support enabled for real-time updates")

    # Use global socketio instance
    # allow_unsafe_werkzeug=True is for development/testing only
    # In production, use gunicorn or another WSGI server
    socketio.run(app, host=host, port=port, debug=app.config['DEBUG'], allow_unsafe_werkzeug=True)
