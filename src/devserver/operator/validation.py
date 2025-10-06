"""
Validation and normalization for DevServer resources.
"""
import logging
from datetime import timedelta

import kopf

from ..utils.time import parse_duration


def validate_and_normalize_ttl(
    ttl_str: str, logger: logging.Logger
) -> timedelta:
    """
    Validate and normalize a TTL string.

    Args:
        ttl_str: The TTL string to validate (e.g., "1h", "30m", "23h")
        logger: Logger instance

    Returns:
        The validated TTL as a timedelta

    Raises:
        kopf.PermanentError: If the TTL format is invalid, non-positive, or exceeds 24h
    """
    if not ttl_str:
        # TODO: This check is redundant if the CRD marks timeToLive as required.
        # Verify the CRD schema and remove this if unnecessary.
        raise kopf.PermanentError("spec.lifecycle.timeToLive is required.")

    try:
        ttl = parse_duration(ttl_str)
        if ttl.total_seconds() <= 0:
            raise ValueError("Duration must be positive.")
        
        if ttl > timedelta(hours=24):
            raise kopf.PermanentError(
                f"timeToLive '{ttl_str}' exceeds maximum allowed duration of 24h. "
                f"Please specify a duration of 24h or less."
            )
        
        return ttl
    except ValueError as e:
        raise kopf.PermanentError(f"Invalid timeToLive format: {e}")
