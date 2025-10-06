import re
import subprocess
import sys
import time
from pathlib import Path

from kubernetes import client, config
from rich.console import Console


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

    port_forward_proc = None
    try:
        # Start port forwarding in the background.
        port_forward_cmd = [
            "kubectl",
            "port-forward",
            f"pod/{pod_name}",
            ":22",  # Let kubectl pick a random local port
            f"--namespace={namespace}",
        ]
        port_forward_proc = subprocess.Popen(
            port_forward_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # The readline will block until kubectl prints the forwarding info or exits.
        line = port_forward_proc.stdout.readline()

        local_port = None
        if "Forwarding from" in line:
            match = re.search(r":(\d+)\s*->", line)
            if match:
                local_port = match.group(1)

        # Give it a moment to stabilize
        time.sleep(1)

        if not local_port or port_forward_proc.poll() is not None:
            if port_forward_proc:
                port_forward_proc.terminate()
            stderr_output = port_forward_proc.stderr.read()
            console.print(
                f"Error: Could not start port-forwarding for DevServer '{name}'. Pod may not be ready."
            )
            if stderr_output:
                console.print(f"[red]kubectl error: {stderr_output.strip()}[/red]")
            sys.exit(1)

        console.print(
            f"Connecting to devserver '{name}' via port-forward on localhost:{local_port}..."
        )

        key_path = Path(ssh_private_key_file).expanduser()
        if not key_path.is_file():
            console.print(f"[red]Error: SSH private key file not found at '{key_path}'[/red]")
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

    except FileNotFoundError:
        console.print(
            "[red]Error: 'kubectl' command not found. Please ensure it is installed and in your PATH.[/red]"
            "Error: 'kubectl' command not found. Please ensure it is installed and in your PATH."
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        sys.exit(1)
    finally:
        if port_forward_proc and port_forward_proc.poll() is None:
            console.print("\n[green]SSH session ended. Closing port-forward.[/green]")
            port_forward_proc.terminate()
            port_forward_proc.wait()
