"""
Kubernetes operator for DevServer custom resources.

This module contains the main Kopf handlers for the DevServer CRD.
The handlers are kept thin and delegate to specialized modules for:
- Validation (validation.py)
- Host key generation (host_keys.py)
- Resource reconciliation (reconciler.py)
- Lifecycle management (lifecycle.py)
"""
import asyncio
import logging
import os
import sys
from typing import Any, Dict

import kopf
from kubernetes import client, config

from .validation import validate_and_normalize_ttl
from .host_keys import ensure_host_keys_secret
from .reconciler import reconcile_devserver
from .user_reconciler import reconcile_user, on_user_delete
from .lifecycle import cleanup_expired_devservers

try:
    config.load_incluster_config()
except config.ConfigException:
    config.load_kube_config()

# Constants
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
FINALIZER = f"finalizer.{CRD_GROUP}"

# Operator settings
EXPIRATION_INTERVAL = int(os.environ.get("DEVSERVER_EXPIRATION_INTERVAL", 60))


@kopf.on.startup()
async def on_startup(
    settings: kopf.OperatorSettings, logger: logging.Logger, **kwargs: Any
) -> None:
    """
    Handle the startup of the operator.
    
    This sets operator-wide settings and starts background tasks.
    """
    logger.info("Operator started.")
    
    # Verify that required ClusterRoles exist
    rbac_api = client.RbacAuthorizationV1Api()
    required_cluster_roles = ["devserver-user", "devserver-admin"]
    for role_name in required_cluster_roles:
        try:
            rbac_api.read_cluster_role(name=role_name)
            logger.info(f"Found required ClusterRole: {role_name}")
        except client.ApiException as e:
            if e.status == 404:
                logger.fatal(
                    f"Required ClusterRole '{role_name}' not found. "
                    "Please apply the RBAC manifests from the rbac/ directory before running the operator."
                )
                sys.exit(1)
            else:
                logger.fatal(f"Error checking for ClusterRole '{role_name}': {e}")
                sys.exit(1)

    # The default worker limit is unbounded which means you can EASILY flood
    # your API server on restart unless you limit it. 1-5 are the generally
    # accepted common sense defaults. This is intentionally conservative and
    # can be tuned based on your cluster's capabilities.
    # TODO: Make this configurable via environment variable
    settings.batching.worker_limit = 1
    
    # All logs by default go to the k8s event api making api server flooding
    # even more likely. Disable event posting to reduce API load.
    settings.posting.enabled = False
    
    # Start the background cleanup task for TTL expiration
    loop = asyncio.get_running_loop()
    custom_objects_api = client.CustomObjectsApi()
    loop.create_task(
        cleanup_expired_devservers(
            custom_objects_api=custom_objects_api,
            logger=logger,
            interval_seconds=EXPIRATION_INTERVAL,
        )
    )


@kopf.on.create(CRD_GROUP, CRD_VERSION, "devservers")
def create_devserver(
    spec: Dict[str, Any],
    name: str,
    namespace: str,
    logger: logging.Logger,
    patch: Dict[str, Any],
    meta: Dict[str, Any],
    **kwargs: Any,
) -> None:
    """
    Handle the creation of a new DevServer resource.
    
    This handler orchestrates:
    1. TTL validation and normalization
    2. Flavor fetching
    3. SSH host key generation
    4. Kubernetes resource creation
    5. Status updates
    """
    logger.info(f"Creating DevServer '{name}' in namespace '{namespace}'...")

    # Step 1: Validate TTL
    ttl_str = spec.get("lifecycle", {}).get("timeToLive")
    validate_and_normalize_ttl(ttl_str, logger)

    # Step 2: Get the DevServerFlavor
    custom_objects_api = client.CustomObjectsApi()
    try:
        flavor = custom_objects_api.get_cluster_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            plural="devserverflavors",
            name=spec["flavor"],
        )
    except client.ApiException as e:
        if e.status == 404:
            logger.error(f"DevServerFlavor '{spec['flavor']}' not found.")
            raise kopf.PermanentError(f"Flavor '{spec['flavor']}' not found.")
        raise

    # Step 3: Ensure SSH host keys exist
    # Build owner reference metadata for proper garbage collection
    owner_meta = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "name": name,
        "uid": meta["uid"],
    }
    ensure_host_keys_secret(name, namespace, owner_meta, logger)

    # Step 4: Reconcile all Kubernetes resources
    status_message = reconcile_devserver(name, namespace, spec, flavor, logger)

    # Step 5: Update status
    patch["status"] = {
        "phase": "Running",
        "message": status_message,
    }


@kopf.on.delete(CRD_GROUP, CRD_VERSION, "devservers")
def delete_devserver(
    name: str, namespace: str, logger: logging.Logger, **kwargs: Any
) -> None:
    """
    Handle the deletion of a DevServer resource.
    
    The StatefulSet and Services are owned by the DevServer via owner
    references and will be garbage collected automatically.
    
    Note: PVCs from StatefulSets are NOT automatically deleted to prevent
    data loss. Administrators may need to clean them up manually.
    """
    logger.info(f"DevServer '{name}' in namespace '{namespace}' is being deleted.")
    logger.info("Associated StatefulSet and Services will be garbage collected.")
    logger.warning(
        f"PersistentVolumeClaim for '{name}' will NOT be deleted automatically."
    )


@kopf.on.create(CRD_GROUP, CRD_VERSION, "devserverusers")
@kopf.on.update(CRD_GROUP, CRD_VERSION, "devserverusers")
def user_reconciler_handler(spec: Dict[str, Any], name: str, uid: str, logger: logging.Logger, body: Dict[str, Any], **kwargs: Any) -> None:
    """
    Handle the creation and updates of a new User resource.
    """
    reconcile_user(spec=spec, name=name, uid=uid, logger=logger, body=body, **kwargs)


@kopf.on.delete(CRD_GROUP, CRD_VERSION, "devserverusers")
def on_user_delete_handler(spec: Dict[str, Any], name: str, logger: logging.Logger, body: Dict[str, Any], **kwargs: Any) -> None:
    """
    Handle the deletion of a User resource.
    """
    on_user_delete(spec=spec, name=name, logger=logger, body=body, **kwargs)