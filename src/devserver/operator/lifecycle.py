"""
DevServer lifecycle management, including TTL expiration handling.
"""
import asyncio
import logging
from datetime import datetime, timezone

from kubernetes import client

from .validation import validate_and_normalize_ttl


# Constants
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"


async def cleanup_expired_devservers(
    custom_objects_api: client.CustomObjectsApi,
    logger: logging.Logger,
    interval_seconds: int = 60,
) -> None:
    """
    Periodically scan for and delete expired DevServers.

    This is a long-running background task that runs on a fixed interval.

    Args:
        custom_objects_api: Kubernetes custom objects API client
        logger: Logger instance
        interval_seconds: How often to run expiration checks (default: 60s)
    """
    # TODO: This polling-based approach lists ALL DevServers cluster-wide every
    # 60 seconds. This doesn't scale well. Consider alternatives:
    #   1. Per-namespace scoping if your cluster has namespace boundaries
    #   2. Using Kubernetes Job/CronJob pattern instead
    #   3. Implementing per-object timers with asyncio (more complex)
    #   4. Using a watch with periodic sweeps
    #
    # For small to medium clusters (<100 DevServers), this is acceptable.

    # TODO: Add metrics/observability:
    #   - Counter: devservers_expired_total
    #   - Histogram: expiration_check_duration_seconds
    #   - Gauge: active_devservers
    #   - Counter: expiration_check_errors_total
    
    while True:
        try:
            logger.info("Running expiration check for DevServers...")
            devservers = custom_objects_api.list_cluster_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                plural="devservers",
            )

            now = datetime.now(timezone.utc)
            expired_count = 0
            
            for ds in devservers["items"]:
                if _should_expire_devserver(ds, now, logger):
                    await _delete_devserver(ds, custom_objects_api, logger)
                    expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Expired {expired_count} DevServer(s) in this check.")

        except client.ApiException as e:
            logger.error(f"API error during expiration check: {e}")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during expiration check: {e}",
                exc_info=True,
            )

        await asyncio.sleep(interval_seconds)


def _should_expire_devserver(
    ds: dict, now: datetime, logger: logging.Logger
) -> bool:
    """
    Check if a DevServer should be expired.

    Args:
        ds: The DevServer custom object
        now: Current timestamp
        logger: Logger instance

    Returns:
        True if the DevServer should be deleted, False otherwise
    """
    try:
        spec = ds.get("spec", {})
        ttl_str = spec.get("lifecycle", {}).get("timeToLive")
        if not ttl_str:
            return False

        # Reuse the validation logic to ensure consistency
        ttl = validate_and_normalize_ttl(ttl_str, logger)

        meta = ds.get("metadata", {})
        creation_timestamp_str = meta["creationTimestamp"]
        creation_timestamp = datetime.fromisoformat(
            creation_timestamp_str.replace("Z", "+00:00")
        )
        expiration_ts = creation_timestamp + ttl

        return now >= expiration_ts

    except (ValueError, TypeError) as e:
        name = ds.get("metadata", {}).get("name", "unknown")
        logger.error(f"Error processing expiration for DevServer '{name}': {e}")
        return False


async def _delete_devserver(
    ds: dict, custom_objects_api: client.CustomObjectsApi, logger: logging.Logger
) -> None:
    """
    Delete an expired DevServer.

    Args:
        ds: The DevServer custom object
        custom_objects_api: Kubernetes custom objects API client
        logger: Logger instance
    """
    # TODO: Consider updating the DevServer status to "Expiring" before deletion
    # to give users visibility into why it was deleted. Could also emit a
    # Kubernetes Event for audit trail.
    
    # TODO: Add graceful deletion options:
    #   - Allow users to configure grace periods
    #   - Send notifications before expiration
    #   - Allow "snooze" via annotation to extend TTL
    
    meta = ds.get("metadata", {})
    name = meta["name"]
    namespace = meta["namespace"]
    
    logger.info(
        f"DevServer '{name}' in namespace '{namespace}' has expired. Deleting."
    )
    
    try:
        await custom_objects_api.delete_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            plural="devservers",
            name=name,
            namespace=namespace,
            body=client.V1DeleteOptions(),
        )
    except client.ApiException as e:
        if e.status == 404:
            logger.warning(f"DevServer '{name}' already deleted.")
        else:
            raise
