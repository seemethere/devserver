import yaml
from kubernetes import client, config
from rich.console import Console
from typing import Optional

from ..utils import get_current_context


def describe_devserver(name: str, namespace: Optional[str] = None) -> None:
    """Gets and displays the details of a DevServer."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    _, target_namespace = get_current_context()
    if namespace:
        target_namespace = namespace

    try:
        devserver = custom_objects_api.get_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=target_namespace,
            plural="devservers",
            name=name,
        )
        console.print(yaml.dump(devserver))
    except client.ApiException as e:
        if e.status == 404:
            console.print(
                f"Error: DevServer '{name}' not found in namespace '{target_namespace}'."
            )
        else:
            console.print(f"An error occurred: {e.reason}")
