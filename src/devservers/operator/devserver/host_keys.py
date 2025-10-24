"""
SSH host key generation and management.
"""
import asyncio
import base64
import logging
import os
import tempfile
from typing import Dict, Any

from kubernetes import client


async def generate_host_keys() -> Dict[str, str]:
    """
    Generate SSH host keys in a temporary directory.

    Returns:
        A dictionary mapping key names to base64-encoded key contents.
        Keys include both private keys and public keys (.pub suffix).
    """
    # TODO: Consider using the `stringData` field in the Secret spec instead
    # of manually base64-encoding. Kubernetes will automatically encode
    # stringData values, avoiding potential double-encoding issues.
    
    with tempfile.TemporaryDirectory() as temp_dir:
        key_types = ["rsa", "ecdsa", "ed25519"]
        key_data = {}

        for key_type in key_types:
            private_key_path = os.path.join(temp_dir, f"ssh_host_{key_type}_key")
            public_key_path = f"{private_key_path}.pub"

            process = await asyncio.create_subprocess_exec(
                "ssh-keygen", "-t", key_type, "-f", private_key_path, "-N", "", "-q"
            )
            await process.wait()

            with open(private_key_path, "r") as f:
                key_data[f"ssh_host_{key_type}_key"] = base64.b64encode(
                    f.read().encode("utf-8")
                ).decode("utf-8")
            with open(public_key_path, "r") as f:
                key_data[f"ssh_host_{key_type}_key.pub"] = base64.b64encode(
                    f.read().encode("utf-8")
                ).decode("utf-8")

    return key_data


async def ensure_host_keys_secret(
    name: str,
    namespace: str,
    owner_meta: Dict[str, Any],
    logger: logging.Logger,
) -> None:
    """
    Ensure that a Secret containing SSH host keys exists.
    If it does not exist, generate keys and create the Secret.

    Args:
        name: Name of the DevServer (used to generate secret name)
        namespace: Namespace for the secret
        owner_meta: Metadata of the parent DevServer for owner reference
        logger: Logger instance
    """
    # TODO: This function should be called early in the reconciliation flow,
    # after all validation passes. Currently it's called after TTL validation
    # and flavor fetching, which means if key generation fails, we've already
    # done unnecessary work. Consider reordering operations.
    
    secret_name = f"{name}-host-keys"
    core_v1 = client.CoreV1Api()

    try:
        await asyncio.to_thread(
            core_v1.read_namespaced_secret, name=secret_name, namespace=namespace
        )
        logger.info(f"Host key Secret '{secret_name}' already exists.")
        return
    except client.ApiException as e:
        if e.status != 404:
            raise

    logger.info(f"Host key Secret '{secret_name}' not found. Generating keys...")

    key_data = await generate_host_keys()

    secret_body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": secret_name,
            "namespace": namespace,
            "ownerReferences": [
                {
                    "apiVersion": f"{owner_meta['apiVersion']}",
                    "kind": owner_meta["kind"],
                    "name": owner_meta["name"],
                    "uid": owner_meta["uid"],
                    "controller": True,
                    "blockOwnerDeletion": True,
                }
            ],
        },
        "type": "Opaque",
        "data": key_data,
    }

    await asyncio.to_thread(
        core_v1.create_namespaced_secret, namespace=namespace, body=secret_body
    )
    logger.info(f"Host key Secret '{secret_name}' created.")
