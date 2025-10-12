"""
Validation and normalization for DevServer resources.
"""
import logging
from datetime import timedelta

import kopf

from devserver.utils.time import parse_duration


def validate_and_normalize_ttl(
    ttl_str: str | None,
    logger: logging.Logger,
) -> None:
    """
    Validate the TTL string and normalize it to a consistent format.
    Raises a PermanentError if the TTL is invalid.
    """
    if not ttl_str:
        return

    try:
        duration = parse_duration(ttl_str)
        if duration <= timedelta(minutes=0):
            raise ValueError("TTL must be a positive duration.")
        if duration > timedelta(days=7):
            raise ValueError("TTL cannot exceed 7 days.")

    except ValueError as e:
        logger.error(f"Invalid timeToLive value '{ttl_str}': {e}")
        raise kopf.PermanentError(f"Invalid timeToLive: {e}")
