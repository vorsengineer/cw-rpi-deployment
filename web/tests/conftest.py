"""Pytest configuration and fixtures for Flask application tests."""

import os
import sys
import tempfile
import sqlite3
from typing import Generator

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, '/opt/rpi-deployment/scripts')

from hostname_manager import HostnameManager


@pytest.fixture
def test_db_path() -> Generator[str, None, None]:
    """
    Create a temporary test database.

    Yields:
        str: Path to temporary test database file

    Cleanup:
        Removes temporary database file after test completes
    """
    # Create temporary file for test database
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Initialize database schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create venues table
    cursor.execute("""
        CREATE TABLE venues (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            contact_email TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create hostname_pool table (matches production schema)
    cursor.execute("""
        CREATE TABLE hostname_pool (
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
            UNIQUE(product_type, venue_code, identifier),
            FOREIGN KEY (venue_code) REFERENCES venues(code)
        )
    """)

    # Create deployment_history table
    cursor.execute("""
        CREATE TABLE deployment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            mac_address TEXT NOT NULL,
            serial_number TEXT,
            product_type TEXT NOT NULL,
            venue_code TEXT NOT NULL,
            ip_address TEXT,
            status TEXT NOT NULL,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            error_message TEXT,
            installer_version TEXT
        )
    """)

    # Create master_images table
    cursor.execute("""
        CREATE TABLE master_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_type TEXT NOT NULL,
            version TEXT NOT NULL,
            filename TEXT NOT NULL,
            checksum TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            uploaded_date TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            UNIQUE(product_type, version)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX idx_hostname_pool_venue ON hostname_pool(venue_code)")
    cursor.execute("CREATE INDEX idx_hostname_pool_status ON hostname_pool(status)")
    cursor.execute("CREATE INDEX idx_deployment_history_started ON deployment_history(started_at)")

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup: remove temporary database
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def hostname_manager(test_db_path: str) -> HostnameManager:
    """
    Create a HostnameManager instance with test database.

    Args:
        test_db_path: Path to test database

    Returns:
        HostnameManager: Configured hostname manager for testing
    """
    return HostnameManager(test_db_path)


@pytest.fixture
def sample_venues(hostname_manager: HostnameManager) -> list:
    """
    Create sample venues in test database.

    Args:
        hostname_manager: HostnameManager instance

    Returns:
        list: List of created venue codes
    """
    venues = [
        ('CORO', 'Corona Karting', 'California', 'contact@corona.com'),
        ('ARIA', 'Arizona Motorsports', 'Phoenix', 'info@ariamotorsports.com'),
        ('TEST', 'Test Venue', 'Test Location', 'test@test.com')
    ]

    for code, name, location, email in venues:
        hostname_manager.create_venue(code, name, location, email)

    return [v[0] for v in venues]


@pytest.fixture
def sample_kart_numbers(hostname_manager: HostnameManager, sample_venues: list) -> dict:
    """
    Import sample kart numbers for test venues.

    Args:
        hostname_manager: HostnameManager instance
        sample_venues: List of venue codes

    Returns:
        dict: Mapping of venue codes to imported kart numbers
    """
    kart_data = {
        'CORO': ['001', '002', '003', '004', '005'],
        'ARIA': ['101', '102', '103'],
        'TEST': ['999']
    }

    for venue_code in sample_venues:
        if venue_code in kart_data:
            hostname_manager.bulk_import_kart_numbers(venue_code, kart_data[venue_code])

    return kart_data


@pytest.fixture
def app_config(test_db_path: str) -> dict:
    """
    Create test application configuration.

    Args:
        test_db_path: Path to test database

    Returns:
        dict: Configuration dictionary for Flask app
    """
    return {
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-do-not-use-in-production',
        'DATABASE_PATH': test_db_path,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'ITEMS_PER_PAGE': 20,
        'MAX_ITEMS_PER_PAGE': 100
    }


@pytest.fixture
def app(app_config: dict):
    """
    Create Flask application for testing.

    Args:
        app_config: Application configuration dictionary

    Returns:
        Flask: Configured Flask application

    Note:
        This fixture will be implemented after app.py is created.
        For now, it's a placeholder that tests will expect.
    """
    # Import app module (will be created later)
    try:
        sys.path.insert(0, '/opt/rpi-deployment/web')
        from app import create_app
        flask_app = create_app(app_config)
        return flask_app
    except ImportError:
        # App not yet created - tests will fail as expected in TDD RED phase
        pytest.skip("Flask app not yet implemented")


@pytest.fixture
def client(app):
    """
    Create Flask test client.

    Args:
        app: Flask application

    Returns:
        FlaskClient: Test client for making requests
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Create Flask CLI test runner.

    Args:
        app: Flask application

    Returns:
        FlaskCliRunner: CLI runner for testing commands
    """
    return app.test_cli_runner()


@pytest.fixture
def socketio(app):
    """
    Get SocketIO instance from Flask application.

    Args:
        app: Flask application

    Returns:
        SocketIO: SocketIO instance for testing

    Note:
        This fixture retrieves the socketio instance that should be
        created when the Flask app is initialized.
    """
    try:
        from app import socketio as socketio_instance
        return socketio_instance
    except (ImportError, AttributeError):
        pytest.skip("SocketIO not yet implemented")


@pytest.fixture
def socketio_client(app, socketio):
    """
    Create a SocketIO test client for WebSocket testing.

    Args:
        app: Flask application
        socketio: SocketIO instance

    Returns:
        SocketIOTestClient: Test client for WebSocket communication

    Cleanup:
        Automatically disconnects after test completes
    """
    client = socketio.test_client(app, namespace='/')
    yield client
    if client.is_connected():
        client.disconnect()


@pytest.fixture
def multiple_socketio_clients(app, socketio):
    """
    Create multiple SocketIO test clients for broadcast testing.

    Args:
        app: Flask application
        socketio: SocketIO instance

    Returns:
        list: List of 3 connected SocketIO test clients

    Cleanup:
        Disconnects all clients after test completes
    """
    clients = []
    for i in range(3):
        client = socketio.test_client(app, namespace='/')
        clients.append(client)

    yield clients

    # Cleanup: disconnect all clients
    for client in clients:
        if client.is_connected():
            client.disconnect()
