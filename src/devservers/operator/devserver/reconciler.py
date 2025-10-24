"""
Kubernetes resource reconciliation for DevServer resources.
"""
import asyncio
import logging
import os
from typing import Any, Dict

import kopf
from kubernetes import client

from .resources.configmap import build_configmap, build_startup_configmap, build_login_configmap
from .resources.services import build_headless_service, build_ssh_service
from .resources.statefulset import build_statefulset


class DevServerReconciler:
    """
    Handles the creation and management of Kubernetes resources for DevServer.
    """

    def __init__(self, name: str, namespace: str, spec: Dict[str, Any], flavor: Dict[str, Any]):
        self.name = name
        self.namespace = namespace
        self.spec = spec
        self.flavor = flavor
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def build_resources(self) -> Dict[str, Any]:
        """
        Build all Kubernetes resources required for the DevServer.

        Returns:
            Dictionary of resource objects keyed by resource type.
        """
        # Build services
        headless_service = build_headless_service(self.name, self.namespace)
        ssh_service = build_ssh_service(self.name, self.namespace)

        # Build StatefulSet
        statefulset = build_statefulset(self.name, self.namespace, self.spec, self.flavor)

        # Build ConfigMaps
        sshd_configmap = build_configmap(self.name, self.namespace)
        
        script_path = os.path.join(os.path.dirname(__file__), "resources", "startup.sh")
        with open(script_path, "r") as f:
            startup_script_content = f.read()
        startup_script_configmap = build_startup_configmap(
            self.name, self.namespace, startup_script_content
        )
        script_path = os.path.join(os.path.dirname(__file__), "resources", "user_login.sh")
        with open(script_path, "r") as f:
            user_login_script_content = f.read()
        user_login_script_configmap = build_login_configmap(
            self.name, self.namespace, user_login_script_content
        )
        return {
            "headless_service": headless_service,
            "ssh_service": ssh_service,
            "statefulset": statefulset,
            "sshd_configmap": sshd_configmap,
            "startup_script_configmap": startup_script_configmap,
            "user_login_script_configmap": user_login_script_configmap,
        }

    def adopt_resources(self, resources: Dict[str, Any]) -> None:
        """
        Set owner references on all resources using kopf.adopt.

        Args:
            resources: Dictionary of resource objects from build_resources()
        """
        for resource in resources.values():
            kopf.adopt(resource)

    async def create_resources(self, resources: Dict[str, Any], logger: logging.Logger) -> None:
        """
        Create all Kubernetes resources.

        Args:
            resources: Dictionary of resource objects from build_resources()
            logger: Logger instance
        """
        # TODO: The current error handling silently ignores 409 (Conflict) errors,
        # which means if a resource exists with different specs, we won't update it.
        # This makes the operator non-idempotent. Consider:
        #   1. Implementing proper "create or update" semantics
        #   2. Comparing existing resources and updating if different
        #   3. At minimum, logging when we skip due to existing resource
        #
        # This is especially problematic for partial failures - if creation fails
        # halfway through, retrying won't fix the issue.

        # Create ConfigMaps
        await self._create_configmap(resources["sshd_configmap"], logger)
        await self._create_configmap(resources["startup_script_configmap"], logger)
        await self._create_configmap(resources["user_login_script_configmap"], logger)

        # Create Services
        await self._create_service(resources["headless_service"], logger)
        
        if self.spec.get("enableSSH", False):
            await self._create_service(resources["ssh_service"], logger)

        # Create StatefulSet
        await self._create_statefulset(resources["statefulset"], logger)

    async def _create_configmap(self, configmap: Dict[str, Any], logger: logging.Logger) -> None:
        """Create a ConfigMap, ignoring if it already exists."""
        try:
            await asyncio.to_thread(
                self.core_v1.create_namespaced_config_map,
                namespace=self.namespace,
                body=configmap,
            )
            logger.info(f"ConfigMap '{configmap['metadata']['name']}' created.")
        except client.ApiException as e:
            if e.status == 409:
                logger.info(
                    f"ConfigMap '{configmap['metadata']['name']}' already exists, skipping."
                )
            else:
                raise

    async def _create_service(self, service: Dict[str, Any], logger: logging.Logger) -> None:
        """Create a Service, ignoring if it already exists."""
        try:
            await asyncio.to_thread(
                self.core_v1.create_namespaced_service,
                namespace=self.namespace,
                body=service,
            )
            logger.info(f"Service '{service['metadata']['name']}' created.")
        except client.ApiException as e:
            if e.status == 409:
                logger.info(
                    f"Service '{service['metadata']['name']}' already exists, skipping."
                )
            else:
                raise

    async def _create_statefulset(self, statefulset: Dict[str, Any], logger: logging.Logger) -> None:
        """Create a StatefulSet, ignoring if it already exists."""
        try:
            await asyncio.to_thread(
                self.apps_v1.create_namespaced_stateful_set,
                body=statefulset,
                namespace=self.namespace,
            )
            logger.info(f"StatefulSet '{self.name}' created for DevServer.")
        except client.ApiException as e:
            if e.status == 409:
                logger.info(f"StatefulSet '{self.name}' already exists, skipping.")
            else:
                raise


async def reconcile_devserver(
    name: str,
    namespace: str,
    spec: Dict[str, Any],
    flavor: Dict[str, Any],
    logger: logging.Logger,
) -> str:
    """
    Reconcile all Kubernetes resources for a DevServer.

    Args:
        name: Name of the DevServer
        namespace: Namespace of the DevServer
        spec: DevServer spec
        flavor: DevServerFlavor object
        logger: Logger instance

    Returns:
        Status message indicating success
    """
    reconciler = DevServerReconciler(name, namespace, spec, flavor)
    
    # Build all resources
    resources = reconciler.build_resources()
    
    # Set owner references
    reconciler.adopt_resources(resources)
    
    # Create resources
    await reconciler.create_resources(resources, logger)
    
    return f"StatefulSet '{name}' created successfully."
