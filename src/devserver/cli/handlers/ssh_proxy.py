import sys
import socket
import select
from typing import Optional, cast
import io

from kubernetes import client, config

from ...utils.network import kubernetes_port_forward
from ..utils import get_current_context


def ssh_proxy_devserver(
    name: str,
    namespace: Optional[str] = None,
) -> None:
    """Proxy SSH connection to a DevServer."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()

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
            pod_name=pod_name, namespace=target_namespace, pod_port=22, silent=True
        ) as local_port:
            # Proxy mode shuttles data for SSH ProxyCommand
            # Validate that stdin/stdout have buffer attributes
            if not hasattr(sys.stdin, "buffer") or not hasattr(sys.stdout, "buffer"):
                sys.exit(1)  # Silent failure for SSH ProxyCommand
            
            stdin_buffer = cast(io.BufferedIOBase, sys.stdin.buffer)
            stdout_buffer = cast(io.BufferedIOBase, sys.stdout.buffer)
            
            try:
                with socket.create_connection(("localhost", local_port)) as sock:
                    while True:
                        # Monitor both readable and exceptional conditions with timeout
                        r, _, x = select.select(
                            [sys.stdin, sock], [], [sys.stdin, sock], 1.0
                        )
                        
                        # Handle exceptional conditions
                        if x:
                            return
                        
                        for readable in r:
                            if readable is sys.stdin:
                                data = stdin_buffer.read1(4096)
                                if not data:
                                    return
                                sock.sendall(data)
                            elif readable is sock:
                                data = sock.recv(4096)
                                if not data:
                                    return
                                stdout_buffer.write(data)
                                stdout_buffer.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass  # Expected on disconnect - fail silently for SSH ProxyCommand
    except Exception:
        sys.exit(1)