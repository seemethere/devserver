import logging
from typing import Any, Dict

import kopf

from ...crds.const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERFLAVOR
from ...utils.flavors import get_default_flavor


@kopf.on.create(CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERFLAVOR)
@kopf.on.update(CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERFLAVOR)
async def ensure_single_default_flavor(
    spec: Dict[str, Any],
    name: str,
    logger: logging.Logger,
    **kwargs: Any,
) -> None:
    if not spec.get("default", False):
        return

    logger.info(f"DevServerFlavor '{name}' is marked as default, checking for conflicts...")

    default_flavor = await get_default_flavor()
    if default_flavor and default_flavor["metadata"]["name"] != name:
        raise kopf.PermanentError(
            f"Another DevServerFlavor '{default_flavor['metadata']['name']}' is already set as the default. "
            "Please unset the other default flavor before setting a new one."
        )

    logger.info(f"DevServerFlavor '{name}' is the only default flavor.")
