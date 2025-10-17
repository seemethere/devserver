import yaml
from kubernetes import client
from rich.console import Console
from typing import Optional

from ..utils import get_current_context
from ...crds.const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVER


def describe_devserver(name: str, namespace: Optional[str] = None) -> None:
    """Gets and displays the details of a DevServer."""
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    _, target_namespace = get_current_context()
    if namespace:
        target_namespace = namespace

    try:
        devserver = custom_objects_api.get_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=target_namespace,
            plural=CRD_PLURAL_DEVSERVER,
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
