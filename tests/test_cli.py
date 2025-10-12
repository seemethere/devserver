import pytest
from unittest.mock import patch
import io
import sys
import yaml
import os
import tempfile

from click.testing import CliRunner
from devserver.cli import main as cli_main
from devserver.cli import handlers
from tests.conftest import TEST_NAMESPACE
from kubernetes import client
from typing import Any, Dict
from tests.helpers import (
    wait_for_devserver_status,
    cleanup_devserver,
    wait_for_cluster_custom_object_to_be_deleted,
    wait_for_devserveruser_status,
)
from devserver.cli.config import Configuration


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
        self,
        k8s_clients: Dict[str, Any],
        test_ssh_public_key: str,
        test_config: Configuration,
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
            cleanup_devserver(
                custom_objects_api, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
            )

    def test_create_command(
        self,
        k8s_clients: Dict[str, Any],
        test_ssh_public_key: str,
        test_config: Configuration,
    ) -> None:
        """Tests that the 'create' command successfully creates a DevServer."""
        custom_objects_api = k8s_clients["custom_objects_api"]

        try:
            # Call the handler to create the DevServer
            handlers.create_devserver(
                configuration=test_config,
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
            cleanup_devserver(
                custom_objects_api, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
            )

    def test_delete_command(
        self,
        k8s_clients: Dict[str, Any],
        test_ssh_public_key: str,
        test_config: Configuration,
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
        handlers.delete_devserver(
            configuration=test_config, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
        )

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

    def test_describe_command(
        self,
        k8s_clients: Dict[str, Any],
        test_ssh_public_key: str,
        test_config: Configuration,
    ) -> None:
        """Tests that the 'describe' command can see a created DevServer."""
        custom_objects_api = k8s_clients["custom_objects_api"]

        # Create a DevServer for the describe command to find
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

            handlers.describe_devserver(name=TEST_DEVSERVER_NAME, namespace=NAMESPACE)

            sys.stdout = sys.__stdout__  # Restore stdout

            output = captured_output.getvalue()
            assert TEST_DEVSERVER_NAME in output
            assert "any-flavor" in output

        finally:
            # Cleanup
            cleanup_devserver(
                custom_objects_api, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
            )


class TestCliParser:
    """
    Unit tests for the Click CLI parser.
    These tests do not interact with Kubernetes.
    """

    def test_create_command_parsing(self, test_config: Configuration) -> None:
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
            assert isinstance(call_kwargs["configuration"], Configuration)
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

    def test_delete_command_parsing(self, test_config: Configuration) -> None:
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
            assert isinstance(call_kwargs["configuration"], Configuration)
            assert call_kwargs["name"] == "my-server"

    def test_describe_command_parsing(self) -> None:
        """Tests that 'describe' command arguments are parsed correctly."""
        runner = CliRunner()

        # Mock the handler to avoid actual Kubernetes interaction
        with patch("devserver.cli.handlers.describe_devserver") as mock_describe:
            result = runner.invoke(cli_main.main, ["describe", "my-server"])

            # Check that the command succeeded
            assert result.exit_code == 0

            # Verify the handler was called with correct arguments
            mock_describe.assert_called_once()
            call_kwargs = mock_describe.call_args.kwargs
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


class TestUserCliIntegration:
    """Integration tests for the 'user' subcommand."""

    TEST_USERNAME = "test-cli-user"

    def test_user_create_list_delete(
        self, k8s_clients: Dict[str, Any], operator_running: Any
    ) -> None:
        """Tests the full lifecycle (create, list, delete) of a user via the CLI."""
        custom_objects_api = k8s_clients["custom_objects_api"]
        runner = CliRunner()

        try:
            # 1. Create user
            result = runner.invoke(
                cli_main.main, ["admin", "user", "create", self.TEST_USERNAME]
            )
            assert result.exit_code == 0
            assert f"User '{self.TEST_USERNAME}' created successfully" in result.output

            # Wait for operator to set status
            wait_for_devserveruser_status(
                custom_objects_api, name=self.TEST_USERNAME
            )

            user_obj = custom_objects_api.get_cluster_custom_object(
                group="devserver.io",
                version="v1",
                plural="devserverusers",
                name=self.TEST_USERNAME,
            )
            assert user_obj["spec"]["username"] == self.TEST_USERNAME
            assert user_obj["status"]["namespace"] == f"dev-{self.TEST_USERNAME}"

            # 2. List users and check for the new user and namespace
            result = runner.invoke(cli_main.main, ["admin", "user", "list"])
            assert result.exit_code == 0
            assert self.TEST_USERNAME in result.output
            assert f"dev-{self.TEST_USERNAME}" in result.output

            # 3. Delete user
            result = runner.invoke(
                cli_main.main, ["admin", "user", "delete", self.TEST_USERNAME]
            )
            assert result.exit_code == 0
            assert f"User '{self.TEST_USERNAME}' deleted successfully" in result.output

            # Verify resource was deleted by waiting for it to disappear
            wait_for_cluster_custom_object_to_be_deleted(
                custom_objects_api,
                group="devserver.io",
                version="v1",
                plural="devserverusers",
                name=self.TEST_USERNAME,
            )

        finally:
            # Cleanup in case of failure
            try:
                # This will gracefully handle a 404 if already deleted
                handlers.delete_user(username=self.TEST_USERNAME)
            except client.ApiException as e:
                if e.status != 404:
                    raise

    def test_user_kubeconfig_command(
        self, k8s_clients: Dict[str, Any], operator_running: Any
    ) -> None:
        """Tests that the 'user kubeconfig' command generates a valid config."""
        runner = CliRunner()
        username = "test-kubeconfig-user"

        try:
            # 1. Create a user for the test
            runner.invoke(cli_main.main, ["admin", "user", "create", username])
            # Wait for the operator to be ready
            wait_for_devserveruser_status(
                k8s_clients["custom_objects_api"], name=username
            )

            # 2. Generate kubeconfig
            result = runner.invoke(
                cli_main.main, ["admin", "user", "kubeconfig", username]
            )
            assert result.exit_code == 0
            kubeconfig_data = yaml.safe_load(result.output)
            assert kubeconfig_data["current-context"] == username
            assert "token" in kubeconfig_data["users"][0]["user"]

            # 3. Write to a temp file and use it to list devservers
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_kubeconfig:
                temp_kubeconfig.write(result.output)
                kubeconfig_path = temp_kubeconfig.name

            # Use the generated kubeconfig to run a command
            runner_with_kubeconfig = CliRunner(
                env={"KUBECONFIG": kubeconfig_path}
            )
            list_result = runner_with_kubeconfig.invoke(cli_main.main, ["list"])
            assert list_result.exit_code == 0
            assert f"No DevServers found in namespace 'dev-{username}'." in list_result.output

        finally:
            # Cleanup
            runner.invoke(cli_main.main, ["admin", "user", "delete", username])
            if "kubeconfig_path" in locals() and os.path.exists(kubeconfig_path):
                os.remove(kubeconfig_path)


def test_create_and_list_with_operator(
    operator_running: Any,
    k8s_clients: Dict[str, Any],
    test_ssh_public_key: str,
    test_config: Configuration,
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
        devserver_name = "cli-test-server"
        handlers.create_devserver(
            configuration=test_config,
            name=devserver_name,
            flavor="cli-test-flavor",
            image="alpine:latest",
            namespace=NAMESPACE,
            ssh_public_key_file=test_ssh_public_key,
        )

        # Give the operator time to process and set the status to Running
        wait_for_devserver_status(
            custom_objects_api, name=devserver_name, namespace=NAMESPACE
        )

        # Verify it appears in the list command
        captured_output = io.StringIO()
        sys.stdout = captured_output
        handlers.list_devservers(namespace=NAMESPACE)
        sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        assert devserver_name in output

        # If operator is working, we should see Running status eventually
        # Note: This might show "Unknown" initially before operator processes it

    finally:
        # Cleanup
        try:
            handlers.delete_devserver(
                configuration=test_config, name="cli-test-server", namespace=NAMESPACE
            )
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
