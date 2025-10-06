import subprocess
import sys
from pathlib import Path

from kubernetes import client, config
from rich.console import Console

from devserver.utils.network import PortForwardError, kubernetes_port_forward


def ssh_devserver(
    name: str,
    ssh_private_key_file: str = "~/.ssh/id_rsa",
    namespace: str = "default",
    remote_command: tuple[str, ...] = (),
) -> None:
    """SSH into a DevServer."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

    console = Console()

    try:
        # Check if DevServer exists
        custom_objects_api.get_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
            name=name,
        )
    except client.ApiException as e:
        if e.status == 404:
            console.print(f"Error: DevServer '{name}' not found.")
        else:
            console.print(f"Error connecting to Kubernetes: {e.reason}")
        sys.exit(1)

    pod_name = f"{name}-0"

    try:
        with kubernetes_port_forward(
            pod_name=pod_name, namespace=namespace, pod_port=22
        ) as local_port:
            console.print(
                f"Connecting to devserver '{name}' via port-forward on localhost:{local_port}..."
            )

            key_path = Path(ssh_private_key_file).expanduser()
            if not key_path.is_file():
                console.print(
                    f"[red]Error: SSH private key file not found at '{key_path}'[/red]"
                )
                sys.exit(1)

            # We need to add StrictHostKeyChecking=no and UserKnownHostsFile=/dev/null
            # because the host key of localhost:<port> will change for every connection.
            ssh_command = [
                "ssh",
                "-i",
                str(key_path),
                "-p",
                str(local_port),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "dev@localhost",
            ]
            if remote_command:
                ssh_command.extend(remote_command)

            subprocess.run(ssh_command, check=False)

    except PortForwardError as e:
        console.print(
            f"Error: Could not start port-forwarding for DevServer '{name}'. Pod may not be ready."
        )
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        sys.exit(1)
    finally:
        console.print("\n[green]SSH session ended. Closing port-forward.[/green]")
