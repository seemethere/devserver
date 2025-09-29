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

# Generate a unique test namespace for each test session
# This prevents conflicts between concurrent test runs
TEST_NAMESPACE = f"devserver-test-{uuid.uuid4().hex[:8]}"

# Allow override via environment variable for debugging
if os.getenv("DEVSERVER_TEST_NAMESPACE"):
    TEST_NAMESPACE = os.getenv("DEVSERVER_TEST_NAMESPACE")


@pytest.fixture(scope="session", autouse=True)
def apply_crds():
    """
    Pytest fixture to apply the CRDs to the cluster before any tests run,
    create a test namespace, and clean them up after the entire test session is complete.
    """
    config.load_kube_config()
    k8s_client = client.ApiClient()
    core_v1 = client.CoreV1Api()

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
                            print(f"⏳ Still waiting for {crd_name} deletion ({i+1}/30)...")
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
        utils.create_from_yaml(k8s_client, "crds/devserver.io_devservers.yaml", apply=True)
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
                    print(f"⏳ Still waiting for namespace deletion ({i+1}/30)...")
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
    import os
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
        print("ℹ️ Leaving CRDs in place for future test runs (set CLEANUP_CRDS=true to delete)")
    
    print("🏁 Cleanup completed")


@pytest.fixture(scope="session")
def operator_runner():
    """
    Pytest fixture to run the operator in the background during test session.
    """
    # Import the operator module to ensure handlers are registered
    import src.devserver_operator.operator  # noqa: F401
    
    # Set up the operator to run in a background thread with better shutdown handling
    operator_thread = None
    stop_event = threading.Event()
    
    def run_operator():
        """Run the operator in a separate event loop."""
        # Create a completely new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Configure logging to show operator activity
            import logging
            logging.basicConfig(level=logging.INFO)
            kopf_logger = logging.getLogger('kopf')
            kopf_logger.setLevel(logging.INFO)
            
            print(f"🚀 Starting operator in namespace: {TEST_NAMESPACE}")
            
            # Create an asyncio stop event and tie it to the threading event
            async_stop_event = asyncio.Event()
            
            def check_stop():
                if stop_event.is_set():
                    loop.call_soon_threadsafe(async_stop_event.set)
                else:
                    # Check again in 0.1 seconds
                    loop.call_later(0.1, check_stop)
            
            # Start checking for stop signal
            check_stop()
            
            # Run kopf with the stop event
            loop.run_until_complete(
                kopf.run(
                    registry=kopf.get_default_registry(),
                    stop_flag=async_stop_event,
                    priority=0,
                    namespaces=[TEST_NAMESPACE],  # Watch only the test namespace
                )
            )
        except Exception as e:
            # Log all errors to help debug, but suppress cancellation errors
            if "cancelled" not in str(e).lower() and "stop" not in str(e).lower():
                print(f"❌ Operator error: {e}")
                import traceback
                traceback.print_exc()
        finally:
            print("🛑 Operator stopped")
            try:
                loop.close()
            except:
                pass  # Ignore any errors during loop cleanup
    
    # Start the operator in a background thread
    operator_thread = threading.Thread(target=run_operator, daemon=True)
    operator_thread.start()
    
    # Give the operator a moment to start up
    print("⏳ Waiting for operator to start...")
    time.sleep(5)  # Increased startup time
    print("✅ Operator should be running!")
    
    yield

    # Cleanup: Let daemon threads handle cleanup automatically
    print("🏁 Test session ending - operator cleanup handled by daemon thread")


@pytest.fixture(scope="function")
def operator_running(operator_runner):
    """
    Function-scoped fixture that ensures the operator is running for a test.
    This fixture depends on the session-scoped operator_runner.
    """
    # Additional per-test setup can go here if needed
    yield
    # Per-test cleanup can go here if needed
