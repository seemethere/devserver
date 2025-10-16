import contextlib
import select
import socket
import threading
from typing import Iterator

from kubernetes import client
from kubernetes.stream import portforward
from kubernetes.stream.ws_client import PortForward
from rich.console import Console


class PortForwardError(Exception):
    """Custom exception for port forwarding errors."""


def _forward_sockets(
    client_sock: socket.socket, pod_sock: socket.socket, stop_event: threading.Event
) -> None:
    """Helper function to forward traffic between two sockets."""
    sockets = [client_sock, pod_sock]
    while not stop_event.is_set():
        readable, _, exceptional = select.select(sockets, [], sockets, 0.5)
        if exceptional:
            break
        for sock in readable:
            try:
                data = sock.recv(4096)
                if not data:
                    stop_event.set()
                    break
                other_sock = pod_sock if sock is client_sock else client_sock
                other_sock.sendall(data)
            except Exception:
                stop_event.set()
                break


@contextlib.contextmanager
def kubernetes_port_forward(
    pod_name: str, namespace: str, pod_port: int, silent: bool = False
) -> Iterator[int]:
    """
    A context manager to handle port forwarding to a Kubernetes pod.

    Args:
        pod_name: The name of the pod to forward to.
        namespace: The namespace of the pod.
        pod_port: The port on the pod to forward to.
        silent: If True, do not print debug messages to the console.

    Yields:
        The local port number that is being forwarded.

    Raises:
        PortForwardError: If the port forwarding fails to start.
    """
    v1 = client.CoreV1Api()
    stop_forwarding = threading.Event()
    forwarding_error: list[str] = []
    local_port = 0

    def forward_traffic(pf: PortForward) -> None:
        try:
            # Get the socket to the pod
            pod_sock = pf.socket(pod_port)

            # Accept incoming connection from the local client
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as local_server:
                local_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                local_server.bind(("127.0.0.1", 0))
                nonlocal local_port
                local_port = local_server.getsockname()[1]
                local_server.listen(1)

                # Signal that the local port is ready
                setup_finished.set()

                local_server.settimeout(10)
                try:
                    client_sock, _ = local_server.accept()
                except socket.timeout:
                    forwarding_error.append("Timeout waiting for local connection")
                    return

                _forward_sockets(client_sock, pod_sock, stop_forwarding)

                client_sock.close()
                pod_sock.close()
        except Exception as e:
            forwarding_error.append(str(e))
        finally:
            setup_finished.set()

    pf: PortForward = portforward(
        v1.connect_get_namespaced_pod_portforward,
        pod_name,
        namespace,
        ports=str(pod_port),
    )
    if not silent:
        console = Console()
        console.print(f"[bold red]DEBUG: PortForward call args: name={pod_name}, namespace={namespace}, ports={pod_port}[/bold red]")

    setup_finished = threading.Event()
    forward_thread = threading.Thread(
        target=forward_traffic, args=(pf,), daemon=True
    )
    forward_thread.start()

    # Wait for the thread to set up the local port
    setup_finished.wait(timeout=10)

    if forwarding_error:
        raise PortForwardError(
            f"Could not start port-forward: {forwarding_error[0]}"
        )
    if local_port == 0:
        raise PortForwardError("Port forwarding thread failed to start in time.")

    try:
        yield local_port
    finally:
        stop_forwarding.set()
        forward_thread.join(timeout=2)
