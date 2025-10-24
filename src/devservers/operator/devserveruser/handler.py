import logging
from typing import Any, Dict

import kopf

from .reconciler import DevServerUserReconciler
from ...crds.const import (
    CRD_GROUP,
    CRD_VERSION,
    CRD_PLURAL_DEVSERVERUSER,
)


@kopf.on.create(CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERUSER)
@kopf.on.update(CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERUSER)
async def reconcile_devserver_user(
    spec: Dict[str, Any],
    meta: Dict[str, Any],
    logger: logging.Logger,
    patch: Dict[str, Any],
    **kwargs: Any,
) -> None:
    """Reconcile DevServerUser updates idempotently."""

    reconciler = DevServerUserReconciler(spec=spec, metadata=meta)
    result = await reconciler.reconcile(logger)
    patch.setdefault("status", {})
    patch["status"].update(
        {
            "phase": "Ready",
            "message": result.message,
            "namespace": result.namespace,
        }
    )


@kopf.on.delete(CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERUSER)
async def delete_devserver_user(
    spec: Dict[str, Any],
    meta: Dict[str, Any],
    logger: logging.Logger,
    **kwargs: Any,
) -> None:
    """Handle cleanup when a DevServerUser is deleted."""

    reconciler = DevServerUserReconciler(spec=spec, metadata=meta)
    await reconciler.cleanup(logger)
