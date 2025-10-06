from kubernetes import client, config
from rich.console import Console


def delete_devserver(name: str, namespace: str = "default") -> None:
    """Deletes a DevServer resource."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    try:
        custom_objects_api.delete_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
            name=name,
        )
        console.print(f"DevServer '{name}' deleted.")
    except client.ApiException as e:
        if e.status == 404:
            console.print(f"Error: DevServer '{name}' not found.")
        else:
            console.print(f"Error deleting DevServer: {e.reason}")
