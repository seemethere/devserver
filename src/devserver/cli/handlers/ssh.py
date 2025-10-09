import subprocess
import sys
from pathlib import Path
import socket
import select
from typing import Optional

from kubernetes import client, config
from rich.console import Console

from ..ssh_config import (
    create_ssh_config_for_devserver,
    remove_ssh_config_for_devserver,
)
from ...utils.network import PortForwardError, kubernetes_port_forward
from ..config import Configuration


def ssh_devserver(
    configuration: Configuration,
    name: str,
    ssh_private_key_file: Optional[str],
    proxy_mode: bool,
    remote_command: tuple[str, ...],
    assume_yes: bool = False,
    namespace: str = "default",
) -> None:
    """SSH into a DevServer."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

    console = Console()

    key_path_str = ssh_private_key_file or configuration.ssh_private_key_file

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
            console.print(f"[yellow]DevServer '{name}' not found. It may have expired.[/yellow]")
            console.print(f"Cleaning up stale SSH configuration for '{name}'...")
            remove_ssh_config_for_devserver(configuration.ssh_config_dir, name)
        else:
            console.print(f"Error connecting to Kubernetes: {e.reason}")
        sys.exit(1)

    # TODO: The pod name should be dynamically retrieved from the DevServer's status field instead of being hardcoded.
    pod_name = f"{name}-0"

    if not proxy_mode:
        _, use_include = create_ssh_config_for_devserver(
            configuration.ssh_config_dir,
            name,
            key_path_str,
            assume_yes=assume_yes,
        )
        if use_include:
            console.print(f"Connecting to devserver '{name}' via SSH config...")
            ssh_command = ["ssh", name]
            if remote_command:
                ssh_command.extend(remote_command)
            subprocess.run(ssh_command, check=False)
            return
        else:
            console.print("SSH Include not enabled. Using port-forward to connect.")
            console.print("Run 'devctl config ssh-include enable' to simplify this.")

    try:
        with kubernetes_port_forward(
            pod_name=pod_name, namespace=namespace, pod_port=22
        ) as local_port:
            if proxy_mode:
                # In proxy mode, we shuttle data between stdin/stdout and the forwarded port.
                try:
                    with socket.create_connection(("localhost", local_port)) as sock:
                        # Now, shuttle data between stdin/stdout and the socket
                        # This is a simplified version. A more robust implementation
                        # would use select() or asyncio to handle bidirectional data flow.
                        while True:
                            r, _, _ = select.select([sys.stdin, sock], [], [])
                            for readable in r:
                                if readable is sys.stdin:
                                    data = sys.stdin.buffer.read1(4096)
                                    if not data:
                                        return
                                    sock.sendall(data)
                                elif readable is sock:
                                    data = sock.recv(4096)
                                    if not data:
                                        return
                                    sys.stdout.buffer.write(data)
                                    sys.stdout.buffer.flush()
                except (BrokenPipeError, ConnectionResetError):
                    # These errors are expected when the SSH client disconnects
                    pass
                except Exception as e:
                    console.print(f"[red]Proxy error: {e}[/red]")
                finally:
                    return

            console.print(
                f"Connecting to devserver '{name}' via port-forward on localhost:{local_port}..."
            )

            key_path = Path(key_path_str).expanduser()
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
