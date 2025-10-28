from kubernetes import client
from rich.console import Console
from typing import Optional

from ..ssh_config import remove_ssh_config_for_devserver
from ..config import Configuration
from ..utils import get_current_context
from ...crds.devserver import DevServer


def delete_devserver(
    configuration: Configuration, name: str, namespace: Optional[str] = None
) -> None:
    """Delete a DevServer."""
    console = Console()

    user, target_namespace = get_current_context()
    if namespace:
        target_namespace = namespace

    assert target_namespace is not None

    try:
        # Check if DevServer exists to provide a better error message
        devserver = DevServer.get(name=name, namespace=target_namespace)
        devserver.delete()

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
