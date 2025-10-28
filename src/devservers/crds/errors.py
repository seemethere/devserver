"""
Custom exception types for the DevServer client library.
"""

class DevServerClientException(Exception):
    """Base exception for all devserver client errors."""
    pass

class KubeConfigError(DevServerClientException):
    """Raised when the Kubernetes configuration cannot be loaded."""
    pass
