import asyncio
from typing import Any, Dict

from kubernetes import client

from ..crds.const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERFLAVOR


async def get_default_flavor() -> Dict[str, Any] | None:
    custom_objects_api = client.CustomObjectsApi()
    flavors = await asyncio.to_thread(
        custom_objects_api.list_cluster_custom_object,
        group=CRD_GROUP,
        version=CRD_VERSION,
        plural=CRD_PLURAL_DEVSERVERFLAVOR,
    )

    for flavor in flavors.get("items", []):
        if flavor.get("spec", {}).get("default", False):
            return flavor
    return None
