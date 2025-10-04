import base64
import logging
import os
import subprocess
import tempfile
import time
from typing import Any, Dict
from datetime import datetime

import kopf
from kubernetes import client

from .resources.configmap import build_configmap, build_startup_configmap
from .resources.services import build_headless_service, build_ssh_service
from .resources.statefulset import build_statefulset
from ..utils.time import parse_duration

# Constants
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
FINALIZER = f"finalizer.{CRD_GROUP}"

# Operator settings
EXPIRATION_INTERVAL = int(os.environ.get("DEVSERVER_EXPIRATION_INTERVAL", 30))


def generate_and_ensure_host_keys(
    name: str, namespace: str, logger: logging.Logger
) -> None:
    """
    Checks for the existence of a Secret containing SSH host keys.
    If it does not exist, it generates them and creates the Secret.
    """
    secret_name = f"{name}-host-keys"
    core_v1 = client.CoreV1Api()

    try:
        core_v1.read_namespaced_secret(name=secret_name, namespace=namespace)
        logger.info(f"Host key Secret '{secret_name}' already exists.")
        return
    except client.ApiException as e:
        if e.status != 404:
            raise

    logger.info(f"Host key Secret '{secret_name}' not found. Generating keys...")

    # Generate keys in a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        key_types = ["rsa", "ecdsa", "ed25519"]
        key_data = {}

        for key_type in key_types:
            private_key_path = os.path.join(temp_dir, f"ssh_host_{key_type}_key")
            public_key_path = f"{private_key_path}.pub"

            subprocess.run(
                ["ssh-keygen", "-t", key_type, "-f", private_key_path, "-N", "", "-q"],
                check=True,
            )

            with open(private_key_path, "r") as f:
                key_data[f"ssh_host_{key_type}_key"] = base64.b64encode(
                    f.read().encode("utf-8")
                ).decode("utf-8")
            with open(public_key_path, "r") as f:
                key_data[f"ssh_host_{key_type}_key.pub"] = base64.b64encode(
                    f.read().encode("utf-8")
                ).decode("utf-8")

    secret_body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": secret_name, "namespace": namespace},
        "type": "Opaque",
        "data": key_data,
    }

    # Set owner reference for the new Secret
    # This requires being in the context of a Kopf handler.
    # We will call kopf.adopt on this object in the main handler.
    kopf.adopt(secret_body)

    core_v1.create_namespaced_secret(namespace=namespace, body=secret_body)
    logger.info(f"Host key Secret '{secret_name}' created.")


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

    # Ensure SSH host keys exist in a Secret
    generate_and_ensure_host_keys(name, namespace, logger)

    # Build the required Kubernetes objects
    headless_service = build_headless_service(name, namespace)
    ssh_service = build_ssh_service(name, namespace)
    statefulset = build_statefulset(name, namespace, spec, flavor)
    sshd_configmap = build_configmap(name, namespace)
    # Read and build the startup script ConfigMap
    script_path = os.path.join(os.path.dirname(__file__), "resources", "startup.sh")
    with open(script_path, "r") as f:
        startup_script_content = f.read()
    startup_script_configmap = build_startup_configmap(
        name, namespace, startup_script_content
    )

    # Set owner references
    kopf.adopt(headless_service)
    kopf.adopt(ssh_service)
    kopf.adopt(statefulset)
    kopf.adopt(sshd_configmap)
    kopf.adopt(startup_script_configmap)

    # Create the resources in Kubernetes
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    # Create ConfigMap for sshd
    try:
        core_v1.create_namespaced_config_map(namespace=namespace, body=sshd_configmap)
        logger.info(f"SSHD ConfigMap '{sshd_configmap['metadata']['name']}' created.")
    except client.ApiException as e:
        if e.status != 409:  # Ignore if it already exists
            raise

    # Create ConfigMap for startup script
    try:
        core_v1.create_namespaced_config_map(
            namespace=namespace, body=startup_script_configmap
        )
        logger.info(
            f"Startup script ConfigMap '{startup_script_configmap['metadata']['name']}' created."
        )
    except client.ApiException as e:
        if e.status != 409:  # Ignore if it already exists
            raise

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


@kopf.timer(CRD_GROUP, CRD_VERSION, "devservers", interval=EXPIRATION_INTERVAL, sharp=True)
def expire_devservers(body: Dict[str, Any], logger: logging.Logger, **kwargs: Any) -> None:
    """
    Handle the expiration of DevServers.
    """
    # Check if the resource is already marked for deletion
    if body.get("metadata", {}).get("deletionTimestamp"):
        return

    creation_timestamp_str: str = body["metadata"]["creationTimestamp"]
    creation_time = datetime.fromisoformat(creation_timestamp_str.replace("Z", "+00:00"))

    time_to_live_str: str = body["spec"]["lifecycle"]["timeToLive"]
    time_to_live_seconds = parse_duration(time_to_live_str)

    # TODO: Handle alerting users of expiration in 5 minute intervals starting at 15 minutes before expiration
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