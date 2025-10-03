"""
This module contains the handler functions for the CLI commands.
"""
from typing import Optional
from pathlib import Path
import sys

from kubernetes import client, config
from rich.console import Console
from rich.table import Table
from rich.pretty import Pretty

def list_devservers(namespace: str = "default") -> None:
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

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("NAME", style="dim", width=20)
        table.add_column("STATUS")

        for ds in devservers["items"]:
            name = ds["metadata"]["name"]
            status = ds.get("status", {}).get("phase", "Unknown")
            table.add_row(name, status)

        console.print(table)

    except client.ApiException as e:
        if e.status == 404:
            print("DevServer CRD not found. Is the operator installed?")
        else:
            print(f"Error connecting to Kubernetes: {e}")


def create_devserver(
    name: str,
    flavor: str,
    image: Optional[str] = None,
    ssh_public_key_file: str = "~/.ssh/id_rsa.pub",
    namespace: str = "default",
    time_to_live: str = "4h",
) -> None:
    """Creates a new DevServer resource."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

    try:
        key_path = Path(ssh_public_key_file).expanduser()
        with open(key_path, "r") as f:
            ssh_public_key = f.read().strip()
    except FileNotFoundError:
        print(f"Error: SSH public key file not found at '{key_path}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading SSH public key file: {e}")
        sys.exit(1)

    # Construct the DevServer manifest
    manifest = {
        "apiVersion": "devserver.io/v1",
        "kind": "DevServer",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "flavor": flavor,
            "image": image or "ubuntu:22.04",  # Default image
            "ssh": {"publicKey": ssh_public_key},
            "lifecycle": {"timeToLive": time_to_live},
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


def delete_devserver(name: str, namespace: str = "default") -> None:
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


def list_flavors() -> None:
    """Lists all DevServerFlavors."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

    try:
        flavors = custom_objects_api.list_cluster_custom_object(
            group="devserver.io",
            version="v1",
            plural="devserverflavors",
        )
        console = Console()
        table = Table(
            show_header=True, header_style="bold magenta"
        )
        table.add_column("NAME", style="dim", width=20)
        table.add_column("RESOURCES", width=80)

        for flavor in flavors["items"]:
            name = flavor["metadata"]["name"]
            resources = flavor["spec"]["resources"]
            table.add_row(name, Pretty(resources))

        console.print(table)
    except client.ApiException as e:
        print(f"Error listing DevServerFlavors: {e.reason}")