import logging
from typing import Any, Dict

import kopf

from ...crds.const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERFLAVOR
from ...utils.flavors import get_default_flavor
from .reconciler import DevServerFlavorReconciler


@kopf.on.create(CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERFLAVOR)
@kopf.on.update(CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERFLAVOR)
async def reconcile_devserver_flavor(
    body: Dict[str, Any],
    spec: Dict[str, Any],
    name: str,
    logger: logging.Logger,
    **kwargs: Any,
) -> None:
    """
    Reconcile a DevServerFlavor on creation or update.

    This handler is responsible for:
    1. Ensuring there is only one default flavor.
    2. Updating the schedulability status.
    """
    # 1. Ensure there is only one default flavor
    if spec.get("default", False):
        logger.info(f"DevServerFlavor '{name}' is marked as default, checking for conflicts...")
        default_flavor = await get_default_flavor()
        if default_flavor and default_flavor["metadata"]["name"] != name:
            raise kopf.PermanentError(
                f"Another DevServerFlavor '{default_flavor['metadata']['name']}' is already set as the default. "
                "Please unset the other default flavor before setting a new one."
            )
        logger.info(f"DevServerFlavor '{name}' is the only default flavor.")

    # 2. Reconcile schedulability status
    reconciler = DevServerFlavorReconciler(logger)
    await reconciler.reconcile_flavor(flavor=body)
