from __future__ import annotations
import logging
from typing import Any, Dict, List
from kubernetes import client
from ...crds.const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVERFLAVOR


class DevServerFlavorReconciler:
    """
    Reconciles DevServerFlavor CRDs to update their schedulability status.
    This is not a Kopf handler, but a class that is called by the handlers.
    """

    def __init__(self, logger: logging.Logger, custom_objects_api: client.CustomObjectsApi | None = None, core_v1_api: client.CoreV1Api | None = None) -> None:
        self.logger = logger
        self.custom_objects_api = custom_objects_api if custom_objects_api is not None else client.CustomObjectsApi()
        self.core_v1_api = core_v1_api if core_v1_api is not None else client.CoreV1Api()

    async def reconcile_all_flavors(self) -> None:
        """
        Lists all DevServerFlavors and updates their schedulability status.
        This is useful when there is a change in nodes or nodepools.
        """
        self.logger.info("Reconciling all DevServerFlavors due to a change in cluster resources.")
        try:
            flavors = self.custom_objects_api.list_cluster_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                plural=CRD_PLURAL_DEVSERVERFLAVOR,
            )

            nodepools = self._get_nodepools()
            nodes = self.core_v1_api.list_node().items

            for flavor in flavors.get("items", []):
                await self.reconcile_flavor(flavor, nodepools, nodes)

        except client.ApiException as e:
            self.logger.error(f"Error listing DevServerFlavors during full reconciliation: {e}")

    async def reconcile_flavor(self, flavor: Dict[str, Any], nodepools: List[Dict[str, Any]] | None = None, nodes: List[client.V1Node] | None = None) -> None:
        """
        Reconciles a single DevServerFlavor to update its schedulability status.
        """
        flavor_name = flavor["metadata"]["name"]
        self.logger.info(f"Reconciling DevServerFlavor: {flavor_name}")

        if nodepools is None:
            nodepools = self._get_nodepools()
        if nodes is None:
            nodes = self.core_v1_api.list_node().items

        schedulability = self._get_flavor_schedulability(flavor, nodepools, nodes)

        status_patch = {"status": {"schedulable": schedulability}}

        try:
            self.custom_objects_api.patch_cluster_custom_object_status(
                group=CRD_GROUP,
                version=CRD_VERSION,
                plural=CRD_PLURAL_DEVSERVERFLAVOR,
                name=flavor_name,
                body=status_patch,
            )
            self.logger.info(f"Successfully patched status for DevServerFlavor '{flavor_name}' with '{schedulability}'")
        except client.ApiException as e:
            if e.status == 404:
                self.logger.warning(f"DevServerFlavor '{flavor_name}' not found for status patch.")
            else:
                self.logger.error(f"Error patching DevServerFlavor '{flavor_name}': {e}")

    def _get_nodepools(self) -> List[Dict[str, Any]]:
        try:
            return self.custom_objects_api.list_cluster_custom_object(
                group="karpenter.sh",
                version="v1",
                plural="nodepools",
            ).get("items", [])
        except client.ApiException:
            self.logger.info("Karpenter NodePools not found, assuming no autoscaling.")
            return []

    def _get_flavor_schedulability(
        self, flavor: Dict[str, Any], nodepools: List[Dict[str, Any]], nodes: List[client.V1Node]
    ) -> str:
        """Determine if a flavor is schedulable."""
        node_selector = flavor.get("spec", {}).get("nodeSelector", {})

        # Check against Karpenter NodePools first
        for pool in nodepools:
            requirements = pool.get("spec", {}).get("template", {}).get("spec", {}).get("requirements", [])
            pool_selector = {req["key"]: req["values"][0] for req in requirements if req.get("values")}

            matches = all(item in pool_selector.items() for item in node_selector.items())

            if matches:
                for condition in pool.get("status", {}).get("conditions", []):
                    if condition.get("type") == "Ready" and condition.get("status") == "True":
                        return "AUTOSCALED"

        # Check against existing nodes if no autoscaling pool matches
        for node in nodes:
            if self._node_selector_matches(node_selector, node.metadata.labels):
                # This is a simplified check. A full check would involve taints/tolerations and resource parsing.
                return "Yes"

        return "No"

    def _node_selector_matches(self, selector: Dict[str, str], labels: Dict[str, str] | None) -> bool:
        """Check if a node's labels match a node selector."""
        if not selector:
            return True
        if not labels:
            return False
        return all(item in labels.items() for item in selector.items())
