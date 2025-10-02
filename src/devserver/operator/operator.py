import logging
import time
from typing import Any, Dict
from datetime import datetime

import kopf
from kubernetes import client

from .resources.services import build_headless_service, build_ssh_service
from .resources.statefulset import build_statefulset
from ..utils.time import parse_duration

# Constants
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
FINALIZER = f"finalizer.{CRD_GROUP}"


@kopf.on.create(CRD_GROUP, CRD_VERSION, "devservers")
def create_devserver(
    spec: Dict[str, Any],
    name: str,
    namespace: str,
    logger: logging.Logger,
    patch: Dict[str, Any],
    **kwargs: Any,
) -> None:
    """
    Handle the creation of a new DevServer resource.
    """
    logger.info(f"Creating DevServer '{name}' in namespace '{namespace}'...")

    # Get the DevServerFlavor to determine resources
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

    # Build the required Kubernetes objects
    headless_service = build_headless_service(name, namespace)
    ssh_service = build_ssh_service(name, namespace)
    statefulset = build_statefulset(name, namespace, spec, flavor)

    # Set owner references
    kopf.adopt(headless_service)
    kopf.adopt(ssh_service)
    kopf.adopt(statefulset)

    # Create the resources in Kubernetes
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    # Create Services
    try:
        core_v1.create_namespaced_service(namespace=namespace, body=headless_service)
        logger.info(
            f"Headless Service '{headless_service['metadata']['name']}' created."
        )
    except client.ApiException as e:
        if e.status != 409:  # Ignore if it already exists
            raise

    if spec.get("enableSSH", False):
        try:
            core_v1.create_namespaced_service(namespace=namespace, body=ssh_service)
            logger.info(f"SSH Service '{ssh_service['metadata']['name']}' created.")
        except client.ApiException as e:
            if e.status != 409:
                raise

    # Create StatefulSet
    try:
        apps_v1.create_namespaced_stateful_set(body=statefulset, namespace=namespace)
        logger.info(f"StatefulSet '{name}' created for DevServer.")
    except client.ApiException as e:
        if e.status != 409:  # Ignore if it already exists
            raise

    # Update the status
    patch["status"] = {
        "phase": "Running",
        "message": f"StatefulSet '{name}' created successfully.",
    }


@kopf.on.delete(CRD_GROUP, CRD_VERSION, "devservers")
def delete_devserver(
    name: str, namespace: str, logger: logging.Logger, **kwargs: Any
) -> None:
    """
    Handle the deletion of a DevServer resource.
    The StatefulSet and Services are owned by the DevServer and will be garbage collected.
    """
    logger.info(f"DevServer '{name}' in namespace '{namespace}' is being deleted.")

    # The owner reference handles cleanup of StatefulSet and Services.
    # PVCs from StatefulSets are not automatically deleted to prevent data loss.
    # An administrator may need to clean them up manually.
    logger.info("Associated StatefulSet and Services will be garbage collected.")
    logger.warning(
        f"PersistentVolumeClaim for '{name}' will NOT be deleted automatically."
    )


@kopf.timer(CRD_GROUP, CRD_VERSION, "devservers", interval=300, sharp=True)
def expire_devservers(body: Dict[str, Any], logger: logging.Logger, **kwargs: Any) -> None:
    """
    Handle the expiration of DevServers.
    """
    # Check if the resource is already marked for deletion
    if body.get("metadata", {}).get("deletionTimestamp"):
        return

    creation_timestamp_str = body["metadata"]["creationTimestamp"]
    creation_time = datetime.fromisoformat(creation_timestamp_str.replace("Z", "+00:00"))

    time_to_live_str = body["spec"]["lifecycle"]["timeToLive"]
    time_to_live_seconds = parse_duration(time_to_live_str)

    if creation_time.timestamp() + time_to_live_seconds < time.time():
        logger.info(f"DevServer '{body['metadata']['name']}' is expired.")
        try:
            client.CustomObjectsApi().delete_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                plural="devservers",
                name=body["metadata"]["name"],
                namespace=body["metadata"]["namespace"],
                body=client.V1DeleteOptions(),
            )
        except client.ApiException as e:
            if e.status == 404:
                logger.warning(
                    f"DevServer '{body['metadata']['name']}' not found for deletion, probably already deleted."
                )
            else:
                raise