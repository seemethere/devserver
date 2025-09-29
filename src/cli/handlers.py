"""
This module contains the handler functions for the CLI commands.
"""

from kubernetes import client, config


def list_devservers(namespace="default"):
    """Lists all DevServers in a given namespace."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

    try:
        devservers = custom_objects_api.list_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
        )

        if not devservers["items"]:
            print(f"No DevServers found in namespace '{namespace}'.")
            return

        # Simple print for now. We can make this a nice table later.
        print(f"{'NAME':<20} {'STATUS':<15}")
        print("-" * 35)
        for ds in devservers["items"]:
            name = ds["metadata"]["name"]
            status = ds.get("status", {}).get("phase", "Unknown")
            print(f"{name:<20} {status:<15}")

    except client.ApiException as e:
        if e.status == 404:
            print("DevServer CRD not found. Is the operator installed?")
        else:
            print(f"Error connecting to Kubernetes: {e}")


def create_devserver(name, flavor, image=None, namespace="default"):
    """Creates a new DevServer resource."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

    # Construct the DevServer manifest
    manifest = {
        "apiVersion": "devserver.io/v1",
        "kind": "DevServer",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "flavor": flavor,
            "image": image or "ubuntu:22.04",  # Default image
        },
    }

    try:
        custom_objects_api.create_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
            body=manifest,
        )
        print(f"DevServer '{name}' created successfully.")
    except client.ApiException as e:
        if e.status == 409:  # Conflict
            print(f"Error: DevServer '{name}' already exists.")
        else:
            print(f"Error creating DevServer: {e.reason}")


def delete_devserver(name, namespace="default"):
    """Deletes a DevServer resource."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

    try:
        custom_objects_api.delete_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
            name=name,
        )
        print(f"DevServer '{name}' deleted.")
    except client.ApiException as e:
        if e.status == 404:
            print(f"Error: DevServer '{name}' not found.")
        else:
            print(f"Error deleting DevServer: {e.reason}")
