"""
This file contains shared fixtures for all tests.
"""

import asyncio
import threading
import time
import pytest
from kubernetes import client, config, utils
import kopf
import uuid
import os
from typing import cast
import subprocess
from typing import Any

# Generate a unique test namespace for each test session
# This prevents conflicts between concurrent test runs
TEST_NAMESPACE = f"devserver-test-{uuid.uuid4().hex[:8]}"

# Allow override via environment variable for debugging
if os.getenv("DEVSERVER_TEST_NAMESPACE"):
    TEST_NAMESPACE = cast(str, os.getenv("DEVSERVER_TEST_NAMESPACE"))


@pytest.fixture(scope="session")
def test_ssh_key_pair(tmp_path_factory: Any) -> dict[str, str]:
    """Creates a real SSH key pair for functional tests."""
    ssh_dir = tmp_path_factory.mktemp("ssh_keys")
    private_key_path = ssh_dir / "id_rsa"
    public_key_path = ssh_dir / "id_rsa.pub"

    subprocess.run(
        ["ssh-keygen", "-t", "rsa", "-f", str(private_key_path), "-N", "", "-q"],
        check=True,
    )

    return {
        "private": str(private_key_path),
        "public": str(public_key_path),
    }


@pytest.fixture(scope="session")
def test_ssh_public_key(tmp_path_factory):
    """Creates a dummy SSH public key file for tests."""
    # A minimal valid-looking public key
    key_content = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC"
    key_path = tmp_path_factory.mktemp("ssh") / "id_rsa.pub"
    key_path.write_text(key_content)
    return str(key_path)


@pytest.fixture(scope="session")
def k8s_clients():
    """
    Session-scoped fixture that provides Kubernetes API clients.
    Loads kubeconfig once and creates clients for all tests to use.
    """
    config.load_kube_config()
    return {
        "apps_v1": client.AppsV1Api(),
        "core_v1": client.CoreV1Api(),
        "custom_objects_api": client.CustomObjectsApi(),
    }


@pytest.fixture(scope="session", autouse=True)
def apply_crds():
    """
    Pytest fixture to apply the CRDs to the cluster before any tests run,
    create a test namespace, and clean them up after the entire test session is complete.
    """
    config.load_kube_config()
    k8s_client = client.ApiClient()
    core_v1 = client.CoreV1Api()

    # --- Early connection check ---
    try:
        # Make a simple, lightweight API call to check connectivity
        print("🔎 Attempting to connect to Kubernetes API...")
        core_v1.list_namespace(limit=1, _request_timeout=2)
        print("✅ Kubernetes API connection successful.")
    except Exception as e:
        pytest.fail(
            "❌ Could not connect to Kubernetes API. "
            "Please ensure your kubeconfig is correct and the cluster is running.\n"
            f"   Error: {e}",
            pytrace=False,
        )
    # --- End connection check ---

    # Create test namespace
    test_namespace = client.V1Namespace(
        metadata=client.V1ObjectMeta(name=TEST_NAMESPACE)
    )
    try:
        core_v1.create_namespace(test_namespace)
        print(f"✅ Created unique test namespace: {TEST_NAMESPACE}")
    except client.ApiException as e:
        if e.status == 409:  # Already exists
            print(f"ℹ️ Test namespace already exists: {TEST_NAMESPACE}")
        else:
            raise

    # Check for any existing CRDs and handle terminating state
    api_extensions_v1 = client.ApiextensionsV1Api()
    crd_names = ["devservers.devserver.io", "devserverflavors.devserver.io"]

    for crd_name in crd_names:
        print(f"⏳ Checking if CRD {crd_name} exists...")
        try:
            crd = api_extensions_v1.read_custom_resource_definition(name=crd_name)
            if crd.metadata.deletion_timestamp:
                print(f"⌛ CRD {crd_name} is terminating - waiting up to 30 seconds...")
                # Wait for the CRD to be fully deleted with timeout
                for i in range(30):  # Wait up to 30 seconds
                    try:
                        api_extensions_v1.read_custom_resource_definition(name=crd_name)
                        time.sleep(1)
                        if i % 10 == 0:  # Log every 10 seconds
                            print(
                                f"⏳ Still waiting for {crd_name} deletion ({i + 1}/30)..."
                            )
                    except client.ApiException as e:
                        if e.status == 404:
                            print(f"✅ CRD {crd_name} fully deleted")
                            break
                        raise
                else:
                    # If we reach here, the CRD is still terminating after 30 seconds
                    print(f"⚠️ CRD {crd_name} deletion timeout - proceeding anyway")
                    print("ℹ️ You may need to manually clean up the CRD or wait longer")
            else:
                print(f"✅ CRD {crd_name} exists and ready")
        except client.ApiException as e:
            if e.status == 404:
                print(f"✅ CRD {crd_name} does not exist - ready to create")
            else:
                print(f"⚠️ Unexpected error checking CRD {crd_name}: {e}")
                # Continue anyway - don't fail the entire test suite

    # Apply CRDs using server-side apply for idempotency
    print("🔧 Applying DevServer CRDs...")
    try:
        utils.create_from_yaml(
            k8s_client, "crds/devserver.io_devservers.yaml", apply=True
        )
        utils.create_from_yaml(
            k8s_client, "crds/devserver.io_devserverflavors.yaml", apply=True
        )
        print("✅ CRDs applied successfully")
    except Exception as e:
        print(f"⚠️ CRD application failed: {e}")
        print("ℹ️ This might be due to terminating CRDs - continuing anyway")
        # Don't fail the entire test session due to CRD issues

    yield

    # Teardown: Delete test namespace and CRDs after all tests in the session are done
    print("🧹 Cleaning up test resources...")

    # Delete test namespace first (this will delete all namespaced resources)
    try:
        core_v1.delete_namespace(name=TEST_NAMESPACE)
        print(f"✅ Deleted test namespace: {TEST_NAMESPACE}")

        # Wait for namespace to be fully deleted with timeout
        print("⏳ Waiting for namespace deletion to complete...")
        for i in range(30):  # Wait up to 30 seconds
            try:
                core_v1.read_namespace(name=TEST_NAMESPACE)
                time.sleep(1)
                if i % 10 == 0:  # Log every 10 seconds
                    print(f"⏳ Still waiting for namespace deletion ({i + 1}/30)...")
            except client.ApiException as e:
                if e.status == 404:
                    print("✅ Namespace fully deleted")
                    break
                raise
        else:
            print("⚠️ Namespace deletion timeout - proceeding anyway")

    except client.ApiException as e:
        if e.status != 404:
            raise

    # Optionally delete CRDs (cluster-scoped resources)
    # We'll leave CRDs in place to avoid termination issues between test runs
    if os.getenv("CLEANUP_CRDS", "false").lower() == "true":
        print("🧹 Deleting CRDs (CLEANUP_CRDS=true)...")
        api_extensions_v1 = client.ApiextensionsV1Api()
        for crd_name in ["devservers.devserver.io", "devserverflavors.devserver.io"]:
            try:
                api_extensions_v1.delete_custom_resource_definition(name=crd_name)
                print(f"✅ Deleted CRD: {crd_name}")
            except client.ApiException as e:
                if e.status != 404:
                    print(f"⚠️ Failed to delete CRD {crd_name}: {e}")
    else:
        print(
            "ℹ️ Leaving CRDs in place for future test runs (set CLEANUP_CRDS=true to delete)"
        )

    print("🏁 Cleanup completed")


@pytest.fixture(scope="session")
def operator_runner():
    """
    Pytest fixture to run the operator in the background during test session.
    Runs as a daemon thread that will be terminated when tests complete.
    """
    # Set a short expiration interval for tests
    os.environ["DEVSERVER_EXPIRATION_INTERVAL"] = "5"

    # Import the operator module to ensure handlers are registered
    import devserver.operator.operator  # noqa: F401

    def run_operator():
        """Run the operator in a separate event loop."""
        # Load kubeconfig within the thread to ensure it's available in this context
        config.load_kube_config()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            print(f"🚀 Starting operator in namespace: {TEST_NAMESPACE}")
            loop.run_until_complete(
                kopf.run(
                    registry=kopf.get_default_registry(),
                    priority=0,
                    namespaces=[TEST_NAMESPACE],
                )
            )
        except Exception:
            pass  # Suppress errors during shutdown
        finally:
            try:
                loop.close()
            except Exception:
                pass

    # Start the operator in a daemon thread (will be killed when main process exits)
    operator_thread = threading.Thread(target=run_operator, daemon=True)
    operator_thread.start()

    # Give the operator a moment to start up
    print("⏳ Waiting for operator to start...")
    time.sleep(5)
    print("✅ Operator running!")

    yield

    # Daemon thread will be terminated automatically when tests complete
    print("🏁 Test session ending, tearing down operator...")


@pytest.fixture(scope="function")
def operator_running(operator_runner):
    """
    Function-scoped fixture that ensures the operator is running for a test.
    This fixture depends on the session-scoped operator_runner.
    """
    # Additional per-test setup can go here if needed
    yield
    # Per-test cleanup can go here if needed


# --- Constants for Tests ---
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_FLAVOR = "devserverflavors"
TEST_FLAVOR_NAME = "test-flavor"


@pytest.fixture(scope="function")
def test_flavor(request):
    """Creates a test DevServerFlavor for a single test function."""
    custom_objects_api = client.CustomObjectsApi()

    flavor_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServerFlavor",
        "metadata": {"name": TEST_FLAVOR_NAME},
        "spec": {
            "resources": {
                "requests": {"cpu": "100m", "memory": "128Mi"},
                "limits": {"cpu": "500m", "memory": "512Mi"},
            }
        },
    }

    print(f"🔧 Creating test_flavor: {TEST_FLAVOR_NAME}")
    custom_objects_api.create_cluster_custom_object(
        group=CRD_GROUP,
        version=CRD_VERSION,
        plural=CRD_PLURAL_FLAVOR,
        body=flavor_manifest,
    )

    # Use request.addfinalizer for robust cleanup
    def cleanup():
        print(f"🧹 Cleaning up test_flavor: {TEST_FLAVOR_NAME}")
        try:
            custom_objects_api.delete_cluster_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                plural=CRD_PLURAL_FLAVOR,
                name=TEST_FLAVOR_NAME,
            )
        except client.ApiException as e:
            if e.status != 404:
                print(f"⚠️ Error cleaning up flavor: {e}")

    request.addfinalizer(cleanup)

    return TEST_FLAVOR_NAME
