from kubernetes import client, config
from rich.console import Console

from ..ssh_config import remove_ssh_config_for_devserver
from ..config import Configuration


def delete_devserver(configuration: Configuration, name: str, namespace: str = "default") -> None:
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
        
        remove_ssh_config_for_devserver(configuration.ssh_config_dir, name)

        console.print(f"DevServer '{name}' deleted.")
    except client.ApiException as e:
        if e.status == 404:
            console.print(f"Error: DevServer '{name}' not found.")
        else:
            console.print(f"An error occurred: {e.reason}")
