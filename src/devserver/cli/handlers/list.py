import yaml
from pathlib import Path

from kubernetes import client, config
from rich.console import Console
from rich.table import Table
from typing import Optional

from ..utils import get_current_context

# Determine the project root by looking for a sentinel file/directory
# This is a bit of a hack, but it's a common pattern.
def find_project_root(start_path: Path, sentinel: str = ".git") -> Path:
    """Find the project root by walking up from start_path until sentinel is found."""
    current = start_path.resolve()
    while current != current.parent:
        if (current / sentinel).exists():
            return current
        current = current.parent
    raise FileNotFoundError(f"Could not find project root with sentinel '{sentinel}' from '{start_path}'")

def list_devservers(namespace: Optional[str] = None) -> None:
    """Lists all DevServers in a given namespace."""
    config.load_kube_config()
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
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("NAME", width=20)
    table.add_column("TYPE", style="dim", width=10)
    table.add_column("RESOURCES", width=80)

    builtin_flavor_names = []
    # List builtin flavors
    try:
        # This assumes the script is run from a location where it can determine the project root.
        script_path = Path(__file__).parent
        project_root = find_project_root(script_path)
        flavors_dir = project_root / "examples" / "flavors"
        
        for flavor_file in flavors_dir.glob("*.yaml"):
            with open(flavor_file, "r") as f:
                flavor_doc = yaml.safe_load(f)
                name = flavor_doc["metadata"]["name"]
                resources = flavor_doc["spec"]["resources"]
                table.add_row(f"[green]{name}[/green]", "builtin", yaml.dump(resources))
                builtin_flavor_names.append(name)
    except (FileNotFoundError, Exception) as e:
        console.print(f"[yellow]Could not load builtin flavors: {e}[/yellow]")

    # List custom flavors from the cluster
    try:
        config.load_kube_config()
        custom_objects_api = client.CustomObjectsApi()
        cluster_flavors = custom_objects_api.list_cluster_custom_object(
            group="devserver.io",
            version="v1",
            plural="devserverflavors",
        )

        for flavor in cluster_flavors["items"]:
            name = flavor["metadata"]["name"]
            # Avoid listing builtin flavors if they are also in the cluster
            if name in builtin_flavor_names:
                continue
            resources = flavor["spec"]["resources"]
            table.add_row(f"[cyan]{name}[/cyan]", "custom", yaml.dump(resources))

    except Exception as e:
        console.print(f"[yellow]Could not load custom flavors from cluster: {e}[/yellow]")

    console.print(table)
