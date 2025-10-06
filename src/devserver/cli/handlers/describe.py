from kubernetes import client, config
from rich.console import Console
from rich.pretty import Pretty


def describe_devserver(name: str, namespace: str = "default") -> None:
    """Describes a DevServer resource."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    try:
        devserver = custom_objects_api.get_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
            name=name,
        )
        console.print(Pretty(devserver))
    except client.ApiException as e:
        if e.status == 404:
            console.print(f"Error: DevServer '{name}' not found.")
        else:
            console.print(f"Error describing DevServer: {e.reason}")
