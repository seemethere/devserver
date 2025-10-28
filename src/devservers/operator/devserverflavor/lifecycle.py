"""
DevServerFlavor lifecycle management.
"""
import asyncio
import logging

from kubernetes import client

from .reconciler import DevServerFlavorReconciler


async def reconcile_flavors_periodically(
    logger: logging.Logger,
    interval_seconds: int = 60,
) -> None:
    """
    Periodically reconcile all DevServerFlavors to keep their status up-to-date
    with the cluster state (nodes, nodepools, etc.).
    """
    reconciler = DevServerFlavorReconciler(logger)
    while True:
        try:
            await reconciler.reconcile_all_flavors()
        except client.ApiException as e:
            logger.error(f"API error during flavor reconciliation: {e}")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during flavor reconciliation: {e}",
                exc_info=True,
            )
        await asyncio.sleep(interval_seconds)
