from kubernetes import client, config
from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table


def list_devservers(namespace: str = "default") -> None:
    """Lists all DevServers in a given namespace."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()
    try:
        devservers = custom_objects_api.list_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
        )

        if not devservers["items"]:
            console.print(f"No DevServers found in namespace '{namespace}'.")
            return

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("NAME", style="dim", width=20)
        table.add_column("STATUS")

        for ds in devservers["items"]:
            name = ds["metadata"]["name"]
            status = ds.get("status", {}).get("phase", "Unknown")
            table.add_row(name, status)

        console.print(table)

    except client.ApiException as e:
        if e.status == 404:
            console.print("DevServer CRD not found. Is the operator installed?")
        else:
            console.print(f"Error connecting to Kubernetes: {e}")


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
