import sys
import socket
import select
from typing import Optional, cast
import io

from kubernetes import client, config
from rich.console import Console

from ...utils.network import PortForwardError, kubernetes_port_forward
from ..utils import get_current_context


def ssh_proxy_devserver(
    name: str,
    namespace: Optional[str] = None,
) -> None:
    """Proxy SSH connection to a DevServer."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()

    _, target_namespace = get_current_context()
    if namespace:
        target_namespace = namespace

    try:
        # Check if DevServer exists
        custom_objects_api.get_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=target_namespace,
            plural="devservers",
            name=name,
        )

        # TODO: The pod name should be dynamically retrieved
        pod_name = f"{name}-0"

        with kubernetes_port_forward(
            pod_name=pod_name, namespace=target_namespace, pod_port=22
        ) as local_port:
            # Proxy mode shuttles data for SSH ProxyCommand
            try:
                with socket.create_connection(("localhost", local_port)) as sock:
                    while True:
                        r, _, _ = select.select([sys.stdin, sock], [], [])
                        for readable in r:
                            if readable is sys.stdin:
                                if hasattr(sys.stdin, "buffer"):
                                    # Use cast to inform the type checker
                                    stdin_buffer = cast(io.BufferedIOBase, sys.stdin.buffer)
                                    data = stdin_buffer.read1(4096)
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
                pass  # Expected on client disconnect
            except Exception as e:
                console.print(f"[red]Proxy error: {e}[/red]")
            finally:
                return
    except client.ApiException as e:
        if e.status == 404:
            # Don't print anything here, as it might interfere with the SSH client
            pass
        else:
            console.print(f"Error connecting to Kubernetes: {e.reason}")
        sys.exit(1)
    except PortForwardError as e:
        console.print(f"[red]Error: Could not start port-forwarding: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        sys.exit(1)
