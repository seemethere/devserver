import pytest
from unittest.mock import patch
import io
import sys

from click.testing import CliRunner
from devserver.cli import main as cli_main
from devserver.cli import handlers
from tests.conftest import TEST_NAMESPACE
from kubernetes import client
from typing import Any, Dict
import uuid
import time

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
                "lifecycle": {"timeToLive": "1h"},
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
                "lifecycle": {"timeToLive": "1h"},
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
    Unit tests for the Click CLI parser.
    These tests do not interact with Kubernetes.
    """

    def test_create_command_parsing(self) -> None:
        """Tests that 'create' command arguments are parsed correctly."""
        runner = CliRunner()
        
        # Mock the handler to avoid actual Kubernetes interaction
        with patch("devserver.cli.handlers.create_devserver") as mock_create:
            result = runner.invoke(
                cli_main.main,
                ["create", "--name", "my-server", "--flavor", "cpu-small", "--image", "ubuntu:22.04"]
            )
            
            # Check that the command succeeded
            assert result.exit_code == 0
            
            # Verify the handler was called with correct arguments
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["name"] == "my-server"
            assert call_kwargs["flavor"] == "cpu-small"
            assert call_kwargs["image"] == "ubuntu:22.04"

    def test_list_command_parsing(self) -> None:
        """Tests that 'list' command is recognized."""
        runner = CliRunner()
        
        # Mock the handler to avoid actual Kubernetes interaction
        with patch("devserver.cli.handlers.list_devservers") as mock_list:
            result = runner.invoke(cli_main.main, ["list"])
            
            # Check that the command succeeded
            assert result.exit_code == 0
            
            # Verify the handler was called
            mock_list.assert_called_once()

    def test_delete_command_parsing(self) -> None:
        """Tests that 'delete' command arguments are parsed correctly."""
        runner = CliRunner()
        
        # Mock the handler to avoid actual Kubernetes interaction
        with patch("devserver.cli.handlers.delete_devserver") as mock_delete:
            result = runner.invoke(cli_main.main, ["delete", "my-server"])
            
            # Check that the command succeeded
            assert result.exit_code == 0
            
            # Verify the handler was called with correct arguments
            mock_delete.assert_called_once()
            call_kwargs = mock_delete.call_args.kwargs
            assert call_kwargs["name"] == "my-server"

    def test_create_command_missing_flavor(self) -> None:
        """Tests that 'create' command fails without a required flavor."""
        runner = CliRunner()
        
        # Click exits with non-zero code when required option is missing
        result = runner.invoke(cli_main.main, ["create", "--name", "my-server"])
        
        # Check that the command failed
        assert result.exit_code != 0
        
        # Click should report the missing required option in the output
        assert "flavor" in result.output.lower() or "required" in result.output.lower()


    def test_ssh_command_parsing(self, tmp_path: Any) -> None:
        """Tests that 'ssh' command arguments are parsed and handled correctly."""
        runner = CliRunner()
        
        # Create a dummy private key file
        private_key_file = tmp_path / "id_rsa"
        private_key_file.touch()

        # We need to mock all interactions with the outside world
        with patch("devserver.cli.handlers.config.load_kube_config"), \
             patch("devserver.cli.handlers.client.CustomObjectsApi") as mock_custom_api, \
             patch("devserver.cli.handlers.subprocess.Popen") as mock_popen, \
             patch("devserver.cli.handlers.subprocess.run") as mock_run:

            # Mock the K8s API to return a dummy DevServer
            mock_custom_api.return_value.get_namespaced_custom_object.return_value = {}

            # Mock the port-forward process
            mock_proc = mock_popen.return_value
            mock_proc.stdout.readline.return_value = "Forwarding from 127.0.0.1:12345 -> 22"
            mock_proc.poll.return_value = None  # Indicate the process is running

            result = runner.invoke(
                cli_main.main,
                ["ssh", "my-server", "--ssh-private-key-file", str(private_key_file)]
            )

            # Check that the command succeeded
            assert result.exit_code == 0
            
            # Verify that port-forward was called correctly
            mock_popen.assert_called_once()
            popen_args = mock_popen.call_args[0][0]
            assert "kubectl" in popen_args
            assert "port-forward" in popen_args
            assert "pod/my-server-0" in popen_args
            
            # Verify that ssh was called correctly
            mock_run.assert_called_once()
            run_args = mock_run.call_args[0][0]
            assert "ssh" in run_args
            assert "dev@localhost" in run_args
            assert "-p" in run_args
            assert "12345" in run_args
            assert "-i" in run_args
            assert str(private_key_file) in run_args


def test_ssh_command_functional(
    operator_running: Any,
    k8s_clients: Dict[str, Any],
    test_flavor: str,
    test_ssh_key_pair: dict[str, str],
) -> None:
    """
    Functional test for the 'ssh' command that verifies an actual SSH connection.
    """
    core_api = k8s_clients["core_v1"]
    devserver_name = f"ssh-test-{uuid.uuid4().hex[:6]}"
    pod_name = f"{devserver_name}-0"

    try:
        # Create a DevServer for the test
        handlers.create_devserver(
            name=devserver_name,
            flavor=test_flavor,
            image="ubuntu:22.04",  # An image with a known shell
            namespace=NAMESPACE,
            ssh_public_key_file=test_ssh_key_pair["public"],
        )

        # Wait for the pod to be running and ready
        for _ in range(60):  # Wait up to 60 seconds
            try:
                pod = core_api.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
                if pod.status.phase == "Running" and all(
                    cs.ready for cs in pod.status.container_statuses
                ):
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

        # Run 'hostname' command via devctl ssh
        handlers.ssh_devserver(
            name=devserver_name,
            namespace=NAMESPACE,
            ssh_private_key_file=test_ssh_key_pair["private"],
            remote_command=("hostname",),
        )

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # The output from the handler contains connection info lines and the command output.
        # We just need to check that the hostname is in the output.
        assert pod_name in output

    finally:
        # Cleanup
        try:
            handlers.delete_devserver(name=devserver_name, namespace=NAMESPACE)
        except Exception:
            pass


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
