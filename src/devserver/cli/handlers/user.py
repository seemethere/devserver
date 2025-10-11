from kubernetes import client, config
from rich.console import Console
from rich.table import Table


def create_user(username: str) -> None:
    """Creates a new DevServerUser resource."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    manifest = {
        "apiVersion": "devserver.io/v1",
        "kind": "DevServerUser",
        "metadata": {"name": username},
        "spec": {"username": username},
    }

    try:
        custom_objects_api.create_cluster_custom_object(
            group="devserver.io",
            version="v1",
            plural="devserverusers",
            body=manifest,
        )
        console.print(f"✅ User '{username}' created successfully.")
    except client.ApiException as e:
        if e.status == 409:
            console.print(f"Error: User '{username}' already exists.")
        else:
            console.print(f"Error creating user: {e.reason}")


def delete_user(username: str) -> None:
    """Deletes a DevServerUser resource."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    try:
        custom_objects_api.delete_cluster_custom_object(
            group="devserver.io",
            version="v1",
            plural="devserverusers",
            name=username,
        )
        console.print(f"✅ User '{username}' deleted successfully.")
    except client.ApiException as e:
        if e.status == 404:
            console.print(f"Error: User '{username}' not found.")
        else:
            console.print(f"Error deleting user: {e.reason}")


def list_users() -> None:
    """Lists all DevServerUser resources."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    try:
        users = custom_objects_api.list_cluster_custom_object(
            group="devserver.io",
            version="v1",
            plural="devserverusers",
        )

        table = Table(title="DevServer Users")
        table.add_column("Name", style="cyan")
        table.add_column("Username", style="magenta")
        table.add_column("Namespace", style="green")
        table.add_column("Status", style="yellow")

        for user in users["items"]:
            status = user.get("status", {})
            table.add_row(
                user["metadata"]["name"],
                user["spec"]["username"],
                status.get("namespace", "N/A"),
                status.get("phase", "Unknown"),
            )

        if not users["items"]:
            console.print("No users found.")
        else:
            console.print(table)

    except client.ApiException as e:
        console.print(f"Error listing users: {e.reason}")
