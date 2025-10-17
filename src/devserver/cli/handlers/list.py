from kubernetes import client
from rich.console import Console
from rich.table import Table
from rich.pretty import Pretty
from typing import Optional

from ..utils import get_current_context


def list_devservers(namespace: Optional[str] = None) -> None:
    """Lists all DevServers in a given namespace."""
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    _, target_namespace = get_current_context()
    if namespace:
        target_namespace = namespace

    try:
        devservers = custom_objects_api.list_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=target_namespace,
            plural="devservers",
        )

        table = Table(title=f"DevServers in namespace [bold]{target_namespace}[/bold]")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Image", style="magenta")
        table.add_column("Flavor", style="yellow")
        table.add_column("TTL", style="red")

        if not devservers["items"]:
            console.print(f"No DevServers found in namespace '{target_namespace}'.")
            return

        for devserver in devservers["items"]:
            status = devserver.get("status", {})
            table.add_row(
                devserver["metadata"]["name"],
                status.get("phase", "Unknown"),
                devserver["spec"].get("image", "default"),
                devserver["spec"]["flavor"],
                devserver["spec"]["lifecycle"]["timeToLive"],
            )
        console.print(table)

    except client.ApiException as e:
        console.print(f"An error occurred: {e.reason}")


def list_flavors() -> None:
    """Lists all DevServerFlavors."""
    custom_objects_api = client.CustomObjectsApi()
    console = Console()
    try:
        flavors = custom_objects_api.list_cluster_custom_object(
            group="devserver.io",
            version="v1",
            plural="devserverflavors",
        )
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("NAME", style="dim", width=20)
        table.add_column("RESOURCES", width=80)

        for flavor in flavors["items"]:
            name = flavor["metadata"]["name"]
            resources = flavor["spec"]["resources"]
            table.add_row(name, Pretty(resources))

        console.print(table)
    except client.ApiException as e:
        console.print(f"Error listing DevServerFlavors: {e.reason}")
