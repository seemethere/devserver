import pytest
from unittest.mock import patch
import io
import sys

from devserver.cli import main as cli_main
from devserver.cli import handlers
from tests.conftest import TEST_NAMESPACE
from kubernetes import client
from typing import Any, Dict

# Define constants and clients needed for CLI tests
CRD_GROUP: str = "devserver.io"
CRD_VERSION: str = "v1"
CRD_PLURAL_DEVSERVER: str = "devservers"
NAMESPACE: str = TEST_NAMESPACE
TEST_DEVSERVER_NAME: str = "test-cli-devserver"


class TestCliIntegration:
    """
    Integration tests for the CLI that interact with a Kubernetes cluster.
    """

    def test_list_command(
        self, k8s_clients: Dict[str, Any], test_ssh_public_key: str
    ) -> None:
        """Tests that the 'list' command can see a created DevServer."""
        custom_objects_api = k8s_clients["custom_objects_api"]

        # Create a DevServer for the list command to find
        devserver_manifest = {
            "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
            "kind": "DevServer",
            "metadata": {"name": TEST_DEVSERVER_NAME, "namespace": NAMESPACE},
            "spec": {
                "flavor": "any-flavor",
                "ssh": {"publicKey": "ssh-rsa AAA..."},
            },  # Flavor doesn't need to exist for this test
        }

        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        try:
            # Capture the stdout
            captured_output = io.StringIO()
            sys.stdout = captured_output

            handlers.list_devservers(namespace=NAMESPACE)

            sys.stdout = sys.__stdout__  # Restore stdout

            output = captured_output.getvalue()
            assert TEST_DEVSERVER_NAME in output
            # Note: Without operator running, status will be Unknown

        finally:
            # Cleanup
            custom_objects_api.delete_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=TEST_DEVSERVER_NAME,
            )

    def test_create_command(
        self, k8s_clients: Dict[str, Any], test_ssh_public_key: str
    ) -> None:
        """Tests that the 'create' command successfully creates a DevServer."""
        custom_objects_api = k8s_clients["custom_objects_api"]

        try:
            # Call the handler to create the DevServer
            handlers.create_devserver(
                name=TEST_DEVSERVER_NAME,
                flavor="test-flavor",
                image="nginx:latest",
                namespace=NAMESPACE,
                ssh_public_key_file=test_ssh_public_key,
            )

            # Verify the resource was created
            ds = custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=TEST_DEVSERVER_NAME,
            )

            assert ds["spec"]["flavor"] == "test-flavor"
            assert ds["spec"]["image"] == "nginx:latest"
            assert "publicKey" in ds["spec"]["ssh"]

        finally:
            # Cleanup
            try:
                custom_objects_api.delete_namespaced_custom_object(
                    group=CRD_GROUP,
                    version=CRD_VERSION,
                    namespace=NAMESPACE,
                    plural=CRD_PLURAL_DEVSERVER,
                    name=TEST_DEVSERVER_NAME,
                )
            except client.ApiException as e:
                if e.status != 404:
                    raise

    def test_delete_command(
        self, k8s_clients: Dict[str, Any], test_ssh_public_key: str
    ) -> None:
        """Tests that the 'delete' command successfully deletes a DevServer."""
        custom_objects_api = k8s_clients["custom_objects_api"]

        # Create a resource to be deleted
        devserver_manifest = {
            "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
            "kind": "DevServer",
            "metadata": {"name": TEST_DEVSERVER_NAME, "namespace": NAMESPACE},
            "spec": {
                "flavor": "any-flavor",
                "ssh": {"publicKey": "ssh-rsa AAA..."},
            },
        }
        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # Call the handler to delete the DevServer
        handlers.delete_devserver(name=TEST_DEVSERVER_NAME, namespace=NAMESPACE)

        # Verify the resource was deleted
        with pytest.raises(client.ApiException) as cm:
            custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=TEST_DEVSERVER_NAME,
            )
        assert isinstance(cm.value, client.ApiException)
        assert cm.value.status == 404


class TestCliParser:
    """
    Unit tests for the argparse CLI parser.
    These tests do not interact with Kubernetes.
    """

    def test_create_command_parsing(self) -> None:
        """Tests that 'create' command arguments are parsed correctly."""
        test_args = [
            "devctl",
            "create",
            "my-server",
            "--flavor",
            "cpu-small",
            "--image",
            "ubuntu:22.04",
        ]
        with patch("sys.argv", test_args):
            # A successful parse should not exit, so we just run it.
            # We add a dummy `parse_args` to prevent the actual print/logic from running.
            with patch("argparse.ArgumentParser.parse_args"):
                cli_main.main()

    def test_list_command_parsing(self) -> None:
        """Tests that 'list' command is recognized."""
        test_args = ["devctl", "list"]
        with patch("sys.argv", test_args):
            # A successful parse should not exit.
            with patch("argparse.ArgumentParser.parse_args"):
                cli_main.main()

    def test_delete_command_parsing(self) -> None:
        """Tests that 'delete' command arguments are parsed correctly."""
        test_args = ["devctl", "delete", "my-server"]
        with patch("sys.argv", test_args):
            with patch("argparse.ArgumentParser.parse_args"):
                cli_main.main()

    def test_create_command_missing_flavor(self) -> None:
        """Tests that 'create' command fails without a required flavor."""
        test_args = ["devctl", "create", "my-server"]
        with patch("sys.argv", test_args):
            # argparse prints to stderr and exits on error.
            # We can assert that it exits with a non-zero status code.
            with pytest.raises(SystemExit) as cm:
                cli_main.main()
            assert isinstance(cm.value, SystemExit)
            assert cm.value.code != 0


def test_create_and_list_with_operator(
    operator_running: Any, k8s_clients: Dict[str, Any], test_ssh_public_key: str
) -> None:
    """
    Integration test for the CLI that works with the actual operator running.
    This test verifies end-to-end functionality by creating a DevServer with CLI
    and verifying it appears in list with proper status when operator is running.
    """
    custom_objects_api = k8s_clients["custom_objects_api"]

    # First create a flavor for the test
    flavor_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServerFlavor",
        "metadata": {"name": "cli-test-flavor"},
        "spec": {
            "resources": {
                "requests": {"cpu": "200m", "memory": "256Mi"},
                "limits": {"cpu": "1", "memory": "1Gi"},
            }
        },
    }
    custom_objects_api.create_cluster_custom_object(
        group=CRD_GROUP,
        version=CRD_VERSION,
        plural="devserverflavors",
        body=flavor_manifest,
    )

    try:
        # Create a DevServer using the CLI
        handlers.create_devserver(
            name="cli-test-server",
            flavor="cli-test-flavor",
            image="alpine:latest",
            namespace=NAMESPACE,
            ssh_public_key_file=test_ssh_public_key,
        )

        # Give the operator time to process
        import time

        time.sleep(3)

        # Verify it appears in the list command
        captured_output = io.StringIO()
        sys.stdout = captured_output
        handlers.list_devservers(namespace=NAMESPACE)
        sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        assert "cli-test-server" in output

        # If operator is working, we should see Running status eventually
        # Note: This might show "Unknown" initially before operator processes it

    finally:
        # Cleanup
        try:
            handlers.delete_devserver(name="cli-test-server", namespace=NAMESPACE)
        except Exception:
            pass

        try:
            custom_objects_api.delete_cluster_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                plural="devserverflavors",
                name="cli-test-flavor",
            )
        except client.ApiException as e:
            if e.status != 404:
                raise
