#!/usr/bin/env python3
"""
Database Setup Script for Raspberry Pi Deployment System

Creates SQLite database with schema for:
- hostname_pool: Available hostnames for assignment
- venues: Venue/location information
- deployment_history: Record of all deployments
- master_images: Available OS images for deployment
- deployment_batches: Batch deployment management with priority queue

Schema enforces data integrity through:
- CHECK constraints on product types and status values
- UNIQUE constraints on venue codes and hostname combinations
- Indexes for common queries

Author: Raspberry Pi Deployment System
Date: 2025-10-23
"""

import sqlite3
import logging
import os
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database(db_path: str = "/opt/rpi-deployment/database/deployment.db") -> bool:
    """
    Initialize SQLite database with required schema.

    Creates all tables, indexes, and constraints needed for the hostname
    management and deployment tracking system.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if successful, False otherwise

    Raises:
        sqlite3.Error: If database operations fail
    """
    try:
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, mode=0o755)
            logger.info(f"Created database directory: {db_dir}")

        # Connect to database (creates file if doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create hostname_pool table
        cursor.execute("""
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
        """)
        logger.info("Created hostname_pool table")

        # Create venues table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS venues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE CHECK(length(code) = 4),
                name TEXT NOT NULL,
                location TEXT,
                contact_email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Created venues table")

        # Create deployment_history table
        cursor.execute("""
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
        """)
        logger.info("Created deployment_history table")

        # Create master_images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                product_type TEXT NOT NULL CHECK(product_type IN ('KXP2', 'RXP2')),
                version TEXT NOT NULL,
                size_bytes INTEGER,
                checksum TEXT,
                description TEXT,
                is_active BOOLEAN DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Created master_images table")

        # Create deployment_batches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deployment_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venue_code TEXT NOT NULL,
                product_type TEXT NOT NULL CHECK(product_type IN ('KXP2', 'RXP2')),
                total_count INTEGER NOT NULL,
                remaining_count INTEGER NOT NULL,
                priority INTEGER DEFAULT 0,
                status TEXT NOT NULL CHECK(status IN ('pending', 'active', 'paused', 'completed', 'cancelled')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (venue_code) REFERENCES venues(code)
            )
        """)
        logger.info("Created deployment_batches table")

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hostname_status
            ON hostname_pool(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hostname_venue
            ON hostname_pool(venue_code)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deployment_date
            ON deployment_history(started_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_status
            ON deployment_batches(status, priority)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_venue
            ON deployment_batches(venue_code)
        """)
        logger.info("Created indexes")

        # Commit changes
        conn.commit()
        conn.close()

        logger.info(f"Database initialized successfully at {db_path}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        raise


def reset_database(db_path: str = "/opt/rpi-deployment/database/deployment.db") -> bool:
    """
    Reset database by dropping all tables and recreating schema.

    WARNING: This deletes all data! Use only for testing or fresh starts.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(db_path):
            logger.warning(f"Resetting database at {db_path}")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Drop all tables
            cursor.execute("DROP TABLE IF EXISTS deployment_batches")
            cursor.execute("DROP TABLE IF EXISTS hostname_pool")
            cursor.execute("DROP TABLE IF EXISTS venues")
            cursor.execute("DROP TABLE IF EXISTS deployment_history")
            cursor.execute("DROP TABLE IF EXISTS master_images")

            conn.commit()
            conn.close()
            logger.info("Dropped all tables")

        # Recreate schema
        return initialize_database(db_path)

    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False


def verify_schema(db_path: str = "/opt/rpi-deployment/database/deployment.db") -> bool:
    """
    Verify that database schema is correct.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if schema is valid, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check all required tables exist
        required_tables = ['hostname_pool', 'venues', 'deployment_history', 'master_images', 'deployment_batches']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            if table not in existing_tables:
                logger.error(f"Missing required table: {table}")
                return False

        # Check indexes exist
        required_indexes = ['idx_hostname_status', 'idx_hostname_venue', 'idx_deployment_date', 'idx_batch_status', 'idx_batch_venue']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = [row[0] for row in cursor.fetchall()]

        for index in required_indexes:
            if index not in existing_indexes:
                logger.error(f"Missing required index: {index}")
                return False

        conn.close()
        logger.info("Schema verification passed")
        return True

    except sqlite3.Error as e:
        logger.error(f"Schema verification failed: {e}")
        return False


if __name__ == '__main__':
    """
    Run database initialization when executed as script.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Initialize deployment database')
    parser.add_argument(
        '--db-path',
        default='/opt/rpi-deployment/database/deployment.db',
        help='Path to database file'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database (WARNING: deletes all data)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify database schema'
    )

    args = parser.parse_args()

    if args.reset:
        if reset_database(args.db_path):
            print(f"Database reset successfully: {args.db_path}")
        else:
            print("Database reset failed")
            exit(1)
    elif args.verify:
        if verify_schema(args.db_path):
            print("Database schema is valid")
        else:
            print("Database schema verification failed")
            exit(1)
    else:
        if initialize_database(args.db_path):
            print(f"Database initialized successfully: {args.db_path}")
        else:
            print("Database initialization failed")
            exit(1)
