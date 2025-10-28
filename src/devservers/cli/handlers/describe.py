import yaml
from kubernetes import client
from rich.console import Console
from typing import Optional

from ..utils import get_current_context
from ...crds.devserver import DevServer


def describe_devserver(name: str, namespace: Optional[str] = None) -> None:
    """Gets and displays the details of a DevServer."""
    console = Console()

    _, target_namespace = get_current_context()
    if namespace:
        target_namespace = namespace

    assert target_namespace is not None

    try:
        devserver = DevServer.get(name=name, namespace=target_namespace)
        console.print(yaml.dump(devserver.to_dict()))
    except client.ApiException as e:
        if e.status == 404:
            console.print(
                f"Error: DevServer '{name}' not found in namespace '{target_namespace}'."
            )
        else:
            console.print(f"An error occurred: {e.reason}")
