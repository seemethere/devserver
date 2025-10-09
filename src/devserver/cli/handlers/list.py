from kubernetes import client, config
from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table

from ..utils import get_user_namespace

def list_devservers(all_namespaces: bool = False) -> None:
    """Lists all DevServers."""
    console = Console()
    api = client.CustomObjectsApi()

    namespace = get_user_namespace() if not all_namespaces else None

    try:
        if namespace:
            devservers = api.list_namespaced_custom_object(
                group="devserver.io",
                version="v1",
                plural="devservers",
                namespace=namespace,
            )["items"]
        else:
            devservers = api.list_cluster_custom_object(
                group="devserver.io",
                version="v1",
                plural="devservers",
            )["items"]
    except client.ApiException as e:
        if e.status == 404:
            console.print("DevServer CRD not found. Is the operator installed?")
            return
        else:
            console.print(f"[red]Error listing devservers: {e}[/red]")
            return

    if not devservers:
        if all_namespaces:
            console.print("No DevServers found in any namespace.")
        else:
            console.print(f"No DevServers found in namespace '{namespace}'.")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("NAME", style="dim", width=20)
    table.add_column("NAMESPACE", style="dim", width=20)
    table.add_column("STATUS")

    for ds in devservers:
        name = ds["metadata"]["name"]
        ns = ds["metadata"]["namespace"]
        status = ds.get("status", {}).get("phase", "Unknown")
        table.add_row(name, ns, status)

    console.print(table)


def list_flavors() -> None:
    """Lists all DevServerFlavors."""
    config.load_kube_config()
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
