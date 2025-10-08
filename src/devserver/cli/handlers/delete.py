import sys
from pathlib import Path
from typing import Optional

from kubernetes import client, config
from rich.console import Console

from devserver.cli.ssh_config import remove_ssh_config_for_devserver


def delete_devserver(
    name: str, namespace: str = "default", config_dir_override: Optional[str] = None
) -> None:
    """Delete a DevServer."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

    console = Console()

    try:
        # Check if DevServer exists to provide a better error message
        custom_objects_api.get_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
            name=name,
        )

        custom_objects_api.delete_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
            name=name,
        )

        config_path = Path(config_dir_override) if config_dir_override else None
        remove_ssh_config_for_devserver(name, config_dir_override=config_path)

        console.print(f"DevServer '{name}' deleted.")
    except client.ApiException as e:
        if e.status == 404:
            console.print(f"Error: DevServer '{name}' not found.")
        else:
            console.print(f"Error connecting to Kubernetes: {e.reason}")
        sys.exit(1)
