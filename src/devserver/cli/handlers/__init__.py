"""
This module contains the handler functions for the CLI commands.
"""
from .create import create_devserver
from .delete import delete_devserver
from .describe import describe_devserver
from .list import list_devservers, list_flavors
from .ssh import ssh_devserver

__all__ = [
    "create_devserver",
    "delete_devserver",
    "describe_devserver",
    "list_devservers",
    "list_flavors",
    "ssh_devserver",
]
