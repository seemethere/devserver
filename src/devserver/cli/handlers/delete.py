from kubernetes import client
from rich.console import Console
from typing import Optional

from ..ssh_config import remove_ssh_config_for_devserver
from ..config import Configuration
from ..utils import get_current_context


def delete_devserver(
    configuration: Configuration, name: str, namespace: Optional[str] = None
) -> None:
    """Delete a DevServer."""
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    user, target_namespace = get_current_context()
    if namespace:
        target_namespace = namespace

    try:
        # Check if DevServer exists to provide a better error message
        custom_objects_api.get_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=target_namespace,
            plural="devservers",
            name=name,
        )

        custom_objects_api.delete_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=target_namespace,
            plural="devservers",
            name=name,
        )

        remove_ssh_config_for_devserver(
            configuration.ssh_config_dir, name, user=user
        )

        console.print(f"DevServer '{name}' in namespace '{target_namespace}' deleted.")
    except client.ApiException as e:
        if e.status == 404:
            console.print(
                f"Error: DevServer '{name}' not found in namespace '{target_namespace}'."
            )
        else:
            console.print(f"An error occurred: {e.reason}")
