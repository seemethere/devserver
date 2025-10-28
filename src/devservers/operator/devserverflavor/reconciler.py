from __future__ import annotations
import logging
from typing import Any, Dict, List
from collections import defaultdict
from kubernetes import client
from kubernetes.client import V1Pod
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
            pods = self.core_v1_api.list_pod_for_all_namespaces().items

            for flavor in flavors.get("items", []):
                await self.reconcile_flavor(flavor, nodepools, nodes, pods)

        except client.ApiException as e:
            self.logger.error(f"Error listing DevServerFlavors during full reconciliation: {e}")

    async def reconcile_flavor(self, flavor: Dict[str, Any], nodepools: List[Dict[str, Any]] | None = None, nodes: List[client.V1Node] | None = None, pods: List[V1Pod] | None = None) -> None:
        """
        Reconciles a single DevServerFlavor to update its schedulability status.
        """
        flavor_name = flavor["metadata"]["name"]
        self.logger.info(f"Reconciling DevServerFlavor: {flavor_name}")

        if nodepools is None:
            nodepools = self._get_nodepools()
        if nodes is None:
            nodes = self.core_v1_api.list_node().items
        if pods is None:
            pods = self.core_v1_api.list_pod_for_all_namespaces().items

        schedulability = self._get_flavor_schedulability(flavor, nodepools, nodes, pods)

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
        self, flavor: Dict[str, Any], nodepools: List[Dict[str, Any]], nodes: List[client.V1Node], pods: List[V1Pod]
    ) -> str:
        """Determine if a flavor is schedulable."""
        node_selector = flavor.get("spec", {}).get("nodeSelector", {})

        # Pre-calculate used resources for all nodes
        used_resources_by_node: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for pod in pods:
            if pod.spec.node_name and pod.status.phase in ["Running", "Pending"]:
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        for res_key, res_val in container.resources.requests.items():
                            parsed_val = self._parse_resource(res_val)
                            used_resources_by_node[pod.spec.node_name][res_key] += parsed_val

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
        flavor_requests = flavor.get("spec", {}).get("resources", {}).get("requests", {})
        if not flavor_requests:
            # If no resources are requested, it's schedulable on any node that matches selector.
            for node in nodes:
                if self._node_selector_matches(node_selector, node.metadata.labels):
                    return "Yes"
            return "No"

        parsed_flavor_requests = {k: self._parse_resource(v) for k, v in flavor_requests.items()}

        for node in nodes:
            if self._node_selector_matches(node_selector, node.metadata.labels):
                # Check for taints and tolerations
                tolerations = flavor.get("spec", {}).get("tolerations", [])
                if not self._tolerates_all_taints(tolerations, node.spec.taints or []):
                    continue

                # Check for resource availability
                allocatable = {k: self._parse_resource(v) for k, v in node.status.allocatable.items()}

                # Get pre-calculated used resources for the node
                used_resources = used_resources_by_node.get(node.metadata.name, {})

                # Check if flavor can be scheduled
                can_schedule = True
                for res_key, res_val in parsed_flavor_requests.items():
                    available = allocatable.get(res_key, 0.0) - used_resources.get(res_key, 0.0)
                    if res_val > available:
                        can_schedule = False
                        self.logger.debug(f"Node {node.metadata.name} does not have enough {res_key}. "
                                        f"Requested: {res_val}, Available: {available}")
                        break

                if can_schedule:
                    return "Yes"

        return "No"

    def _node_selector_matches(self, selector: Dict[str, str], labels: Dict[str, str] | None) -> bool:
        """Check if a node's labels match a node selector."""
        if not selector:
            return True
        if not labels:
            return False
        return all(item in labels.items() for item in selector.items())

    def _parse_resource(self, resource_str: str) -> float:
        """Parse a Kubernetes resource string like '500m', '1Gi', '10' into a numerical value."""
        if isinstance(resource_str, (int, float)):
            return float(resource_str)

        resource_str = str(resource_str)

        # Handle CPU millicores
        if resource_str.endswith("m"):
            return float(resource_str[:-1]) / 1000.0

        # Handle memory suffixes
        suffixes = {"k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12, "P": 10**15, "E": 10**18}
        isuffixes = {"Ki": 1024**1, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4, "Pi": 1024**5, "Ei": 1024**6}

        for suffix, multiplier in isuffixes.items():
            if resource_str.endswith(suffix):
                return float(resource_str[: -len(suffix)]) * multiplier

        for suffix, multiplier in suffixes.items():
            if resource_str.endswith(suffix):
                return float(resource_str[: -len(suffix)]) * multiplier

        try:
            return float(resource_str)
        except ValueError:
            self.logger.warning(f"Could not parse resource string: {resource_str}")
            return 0.0

    def _tolerates_all_taints(self, tolerations: List[Dict[str, str]], taints: List[client.V1Taint]) -> bool:
        """Checks if the given tolerations can tolerate all taints with NoSchedule effect."""
        if not taints:
            return True
        if not tolerations:
            tolerations = []

        for taint in taints:
            if taint.effect != "NoSchedule":
                continue

            tolerated = False
            for toleration in tolerations:
                # An empty key with Exists operator tolerates all keys, values and effects.
                if toleration.get("key") is None and toleration.get("operator") == "Exists":
                    tolerated = True
                    break

                # Effect must match, or toleration has no effect (matches all effects).
                if toleration.get("effect") and toleration.get("effect") != taint.effect:
                    continue

                # Key must match.
                if toleration.get("key") != taint.key:
                    continue

                # Operator logic
                operator = toleration.get("operator", "Equal")
                if operator == "Exists":
                    tolerated = True
                    break
                if operator == "Equal" and toleration.get("value") == taint.value:
                    tolerated = True
                    break

            if not tolerated:
                return False

        return True
