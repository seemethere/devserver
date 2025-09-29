import unittest
from unittest.mock import patch
import io
import sys
from src.cli import main as cli_main
from src.cli import handlers
from tests.test_operator import (
    CRD_GROUP,
    CRD_VERSION,
    CRD_PLURAL_DEVSERVER,
    NAMESPACE,
    TEST_DEVSERVER_NAME,
    TEST_FLAVOR_NAME,
    custom_objects_api,
    test_flavor,  # We can reuse the flavor fixture
)
from kubernetes import client


class TestCliIntegration(unittest.TestCase):
    """
    Integration tests for the CLI that interact with a Kubernetes cluster.
    """

    def test_list_command(self):
        """Tests that the 'list' command can see a created DevServer."""
        # Create a DevServer for the list command to find
        devserver_manifest = {
            "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
            "kind": "DevServer",
            "metadata": {"name": TEST_DEVSERVER_NAME, "namespace": NAMESPACE},
            "spec": {
                "flavor": "any-flavor"
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
            self.assertIn(TEST_DEVSERVER_NAME, output)
            self.assertIn(
                "Unknown", output
            )  # Should be unknown as no operator is running

        finally:
            # Cleanup
            custom_objects_api.delete_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=TEST_DEVSERVER_NAME,
            )

    def test_create_command(self):
        """Tests that the 'create' command successfully creates a DevServer."""
        try:
            # Call the handler to create the DevServer
            handlers.create_devserver(
                name=TEST_DEVSERVER_NAME,
                flavor="test-flavor",
                image="nginx:latest",
                namespace=NAMESPACE,
            )

            # Verify the resource was created
            ds = custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=TEST_DEVSERVER_NAME,
            )

            self.assertEqual(ds["spec"]["flavor"], "test-flavor")
            self.assertEqual(ds["spec"]["image"], "nginx:latest")

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

    def test_delete_command(self):
        """Tests that the 'delete' command successfully deletes a DevServer."""
        # Create a resource to be deleted
        devserver_manifest = {
            "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
            "kind": "DevServer",
            "metadata": {"name": TEST_DEVSERVER_NAME, "namespace": NAMESPACE},
            "spec": {"flavor": "any-flavor"},
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
        with self.assertRaises(client.ApiException) as cm:
            custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=TEST_DEVSERVER_NAME,
            )
        self.assertEqual(cm.exception.status, 404)


class TestCliParser(unittest.TestCase):
    """
    Unit tests for the argparse CLI parser.
    These tests do not interact with Kubernetes.
    """

    def test_create_command_parsing(self):
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

    def test_list_command_parsing(self):
        """Tests that 'list' command is recognized."""
        test_args = ["devctl", "list"]
        with patch("sys.argv", test_args):
            # A successful parse should not exit.
            with patch("argparse.ArgumentParser.parse_args"):
                cli_main.main()

    def test_delete_command_parsing(self):
        """Tests that 'delete' command arguments are parsed correctly."""
        test_args = ["devctl", "delete", "my-server"]
        with patch("sys.argv", test_args):
            with patch("argparse.ArgumentParser.parse_args"):
                cli_main.main()

    def test_create_command_missing_flavor(self):
        """Tests that 'create' command fails without a required flavor."""
        test_args = ["devctl", "create", "my-server"]
        with patch("sys.argv", test_args):
            # argparse prints to stderr and exits on error.
            # We can assert that it exits with a non-zero status code.
            with self.assertRaises(SystemExit) as cm:
                cli_main.main()
            self.assertNotEqual(cm.exception.code, 0)
