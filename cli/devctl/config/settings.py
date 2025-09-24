"""Configuration and settings for devctl."""

import os

# Version and metadata
VERSION = "0.3.0-phase3"
CLI_NAME = "devctl"

# User context
def get_username() -> str:
    """Get current username."""
    return os.environ.get('USER', 'unknown')

def get_user_namespace() -> str:
    """Get user's development namespace."""
    return f"dev-{get_username()}"

def get_user_email() -> str:
    """Get user's email for DevServer ownership."""
    return f"{get_username()}@company.com"

# Environment detection
def is_bastion_environment() -> bool:
    """Check if running in bastion container."""
    return os.path.exists('/.bastion-marker')

# Default values for DevServer creation
DEFAULT_IMAGE = "ubuntu:22.04"
DEFAULT_HOME_SIZE = "10Gi"
DEFAULT_IDLE_TIMEOUT = 3600
DEFAULT_AUTO_SHUTDOWN = True
DEFAULT_ENABLE_SSH = True
