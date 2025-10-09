import pytest
from unittest.mock import patch
from click.testing import CliRunner

from devserver.cli.main import main as cli_main
from tests.helpers import cleanup_devserver

# Constants
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_DEVSERVER = "devservers"
TEST_DEVSERVER_NAME = "test-cli-devserver"


@pytest.mark.usefixtures("operator_running")
class TestCliIntegration:
    """
    Integration tests for the CLI that interact with a Kubernetes cluster
    with the operator running.
    """

    def test_create_list_describe_delete_cycle(self, k8s_clients, test_user, test_flavor):
        """
        Tests the full lifecycle of a DevServer via the CLI:
        create -> list -> describe -> delete
        """
        runner = CliRunner()
        custom_objects_api = k8s_clients["custom_objects_api"]
        user_namespace = test_user["namespace"]

        # Mock get_user_namespace to return our test user's namespace
        with patch("devserver.cli.handlers.get_user_namespace", return_value=user_namespace):
            try:
                # 1. CREATE
                create_result = runner.invoke(
                    cli_main,
                    [
                        "create",
                        "--name",
                        TEST_DEVSERVER_NAME,
                        "--flavor",
                        test_flavor,
                        "--image",
                        "ubuntu:22.04",
                        "--wait",  # Wait for the operator to be ready
                    ],
                )
                assert create_result.exit_code == 0
                assert f"DevServer '{TEST_DEVSERVER_NAME}' is ready" in create_result.output

                # Verify the resource was created in the correct namespace
                ds = custom_objects_api.get_namespaced_custom_object(
                    group=CRD_GROUP,
                    version=CRD_VERSION,
                    namespace=user_namespace,
                    plural=CRD_PLURAL_DEVSERVER,
                    name=TEST_DEVSERVER_NAME,
                )
                assert ds["metadata"]["namespace"] == user_namespace

                # 2. LIST
                list_result = runner.invoke(cli_main, ["list"])
                assert list_result.exit_code == 0
                assert TEST_DEVSERVER_NAME in list_result.output
                assert user_namespace in list_result.output

                # Test --all-namespaces
                list_all_result = runner.invoke(cli_main, ["list", "--all-namespaces"])
                assert list_all_result.exit_code == 0
                assert TEST_DEVSERVER_NAME in list_all_result.output

                # 3. DESCRIBE
                describe_result = runner.invoke(cli_main, ["describe", TEST_DEVSERVER_NAME])
                assert describe_result.exit_code == 0
                assert f"name: {TEST_DEVSERVER_NAME}" in describe_result.output
                assert f"namespace: {user_namespace}" in describe_result.output

                # 4. DELETE
                delete_result = runner.invoke(
                    cli_main, ["delete", TEST_DEVSERVER_NAME], input="y\n"
                )
                assert delete_result.exit_code == 0
                assert f"DevServer '{TEST_DEVSERVER_NAME}' deleted" in delete_result.output

            finally:
                # Ensure cleanup even if asserts fail
                cleanup_devserver(
                    custom_objects_api,
                    name=TEST_DEVSERVER_NAME,
                    namespace=user_namespace,
                )


class TestCliParser:
    """
    Unit tests for the Click CLI parser.
    These tests do not interact with Kubernetes.
    """

    def test_create_command_parsing(self):
        """Tests that 'create' command arguments are parsed correctly."""
        runner = CliRunner()
        with patch("devserver.cli.handlers.create_devserver") as mock_create:
            result = runner.invoke(
                cli_main,
                [
                    "create",
                    "--name",
                    "my-server",
                    "--flavor",
                    "cpu-small",
                    "--image",
                    "ubuntu:22.04",
                ],
            )
            assert result.exit_code == 0
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["name"] == "my-server"
            assert call_kwargs["flavor"] == "cpu-small"
            assert call_kwargs["image"] == "ubuntu:22.04"

    def test_list_command_parsing(self):
        """Tests that 'list' command is recognized."""
        runner = CliRunner()
        with patch("devserver.cli.handlers.list_devservers") as mock_list:
            result = runner.invoke(cli_main, ["list"])
            assert result.exit_code == 0
            mock_list.assert_called_once()

    def test_delete_command_parsing(self):
        """Tests that 'delete' command arguments are parsed correctly."""
        runner = CliRunner()
        with patch("devserver.cli.handlers.delete_devserver") as mock_delete:
            result = runner.invoke(cli_main, ["delete", "my-server"])
            assert result.exit_code == 0
            mock_delete.assert_called_once()
            call_kwargs = mock_delete.call_args.kwargs
            assert call_kwargs["name"] == "my-server"

    def test_describe_command_parsing(self):
        """Tests that 'describe' command arguments are parsed correctly."""
        runner = CliRunner()
        with patch("devserver.cli.handlers.describe_devserver") as mock_describe:
            result = runner.invoke(cli_main, ["describe", "my-server"])
            assert result.exit_code == 0
            mock_describe.assert_called_once()
            call_kwargs = mock_describe.call_args.kwargs
            assert call_kwargs["name"] == "my-server"

    def test_create_command_missing_flavor(self):
        """Tests that 'create' command fails without a required flavor."""
        runner = CliRunner()
        result = runner.invoke(cli_main, ["create", "--name", "my-server"])
        assert result.exit_code != 0
        assert "flavor" in result.output.lower()
