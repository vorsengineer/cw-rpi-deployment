"""Configuration for Flask web management interface."""

import os
import secrets


class Config:
    """Base configuration class."""

    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = False
    TESTING = False

    # Database configuration
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or '/opt/rpi-deployment/database/deployment.db'

    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100

    # File upload configuration
    UPLOAD_FOLDER = '/opt/rpi-deployment/web/static/uploads'
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024 * 1024  # 8GB max file size
    ALLOWED_EXTENSIONS = {'img', 'gz'}

    # WebSocket configuration
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    SOCKETIO_PING_TIMEOUT = 60
    SOCKETIO_PING_INTERVAL = 25

    # API configuration
    API_RATE_LIMIT = "1000 per hour"

    # Service names to monitor
    MONITORED_SERVICES = ['dnsmasq', 'nginx', 'rpi-deployment', 'rpi-web']

    # Network interfaces to monitor
    NETWORK_INTERFACES = ['eth0', 'eth1']

    # Management network
    MANAGEMENT_IP = '192.168.101.146'
    MANAGEMENT_PORT = 5000

    # Deployment network
    DEPLOYMENT_IP = '192.168.151.1'
    DEPLOYMENT_PORT = 5001


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SECRET_KEY = 'dev-secret-key-do-not-use-in-production'


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key-do-not-use-in-production'
    # DATABASE_PATH will be overridden by test fixtures


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    # Use environment variable or generate a warning
    SECRET_KEY = os.environ.get('SECRET_KEY', None)

    def __init__(self):
        """Initialize production config and validate SECRET_KEY."""
        super().__init__()
        if not self.SECRET_KEY:
            import warnings
            warnings.warn("SECRET_KEY environment variable not set - using default (INSECURE!)",
                        RuntimeWarning)
            self.SECRET_KEY = Config.SECRET_KEY


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """
    Get configuration object by name.

    Args:
        config_name: Name of configuration ('development', 'testing', 'production')
                    If None, uses FLASK_ENV environment variable or 'default'

    Returns:
        Config: Configuration object instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    config_class = config.get(config_name, config['default'])
    return config_class()  # Instantiate the class to call __init__
