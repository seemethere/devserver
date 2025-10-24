"""Utility helpers for DevServer user resources."""

from __future__ import annotations

from typing import Final

USERNAME_REGEX: Final[str] = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"


def compute_user_namespace(username: str, cluster_prefix: str = "dev") -> str:
    """Return the namespace name derived from a username and optional prefix."""

    safe_username = username.lower()
    return f"{cluster_prefix}-{safe_username}"
