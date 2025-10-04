import pytest
from typing import Any, Dict
import uuid
import time
import io
import sys

from devserver.cli import handlers
from tests.conftest import TEST_NAMESPACE
from kubernetes import client


@pytest.mark.parametrize("image", ["ubuntu:latest", "fedora:latest"])
def test_ssh_command_functional_on_various_images(
    operator_running: Any,
    k8s_clients: Dict[str, Any],
    test_flavor: str,
    test_ssh_key_pair: dict[str, str],
    image: str,
) -> None:
    """
    Functional test for the 'ssh' command that verifies an actual SSH connection
    on different base images.
    """
    core_api = k8s_clients["core_v1"]
    # Sanitize image name for use in devserver name
    sanitized_image_name = image.replace(":", "-").replace("/", "-")
    devserver_name = f"ssh-test-{sanitized_image_name}-{uuid.uuid4().hex[:6]}"
    pod_name = f"{devserver_name}-0"

    try:
        # Create a DevServer for the test
        handlers.create_devserver(
            name=devserver_name,
            flavor=test_flavor,
            image=image,
            namespace=TEST_NAMESPACE,
            ssh_public_key_file=test_ssh_key_pair["public"],
        )

        # Wait for the pod to be running and ready
        for _ in range(120):  # Wait up to 120 seconds for image pull and pod readiness
            try:
                pod = core_api.read_namespaced_pod(
                    name=pod_name, namespace=TEST_NAMESPACE
                )
                if pod.status.phase == "Running" and pod.status.container_statuses:
                    if all(cs.ready for cs in pod.status.container_statuses):
                        # Additional short wait to ensure sshd is up
                        time.sleep(5)
                        break
            except client.ApiException as e:
                if e.status != 404:
                    raise
            time.sleep(1)
        else:
            pytest.fail(f"Pod {pod_name} did not become ready in time.")

        # Capture stdout to check the command output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        # Run 'whoami' command via devctl ssh to confirm user
        handlers.ssh_devserver(
            name=devserver_name,
            namespace=TEST_NAMESPACE,
            ssh_private_key_file=test_ssh_key_pair["private"],
            remote_command=("whoami",),
        )

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # The output should contain 'dev' indicating the correct user
        assert "dev" in output.strip()

    finally:
        # Cleanup
        try:
            handlers.delete_devserver(name=devserver_name, namespace=TEST_NAMESPACE)
        except Exception:
            pass
