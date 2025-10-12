import pytest
from kubernetes import client
from tests.conftest import TEST_NAMESPACE
from tests.helpers import (
    wait_for_statefulset_to_exist,
    wait_for_statefulset_to_be_deleted,
    wait_for_devserver_status,
    wait_for_devserver_to_be_deleted,
    cleanup_devserver,
)
import uuid
from devserver.operator.devserver import lifecycle
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
import logging
import asyncio

# Constants from the main test file
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_DEVSERVER = "devservers"
NAMESPACE = TEST_NAMESPACE
TEST_DEVSERVER_NAME = "test-devserver"


@pytest.mark.asyncio
async def test_devserver_creates_statefulset(test_flavor, operator_running, k8s_clients):
    """
    Tests if creating a DevServer resource leads to the creation of a
    corresponding StatefulSet. This is the core reconciliation test with
    the actual operator running.
    """
    apps_v1 = k8s_clients["apps_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]

    print(f"🧪 Starting test_devserver_creates_statefulset in namespace: {NAMESPACE}")

    # 1. Create a DevServer custom resource
    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "metadata": {"name": TEST_DEVSERVER_NAME, "namespace": NAMESPACE},
        "spec": {
            "flavor": test_flavor,
            "image": "ubuntu:22.04",
            "ssh": {"publicKey": "ssh-rsa AAAA..."},
            "lifecycle": {"timeToLive": "1h"},
        },
    }

    try:
        print(
            f"📝 Creating DevServer '{TEST_DEVSERVER_NAME}' in namespace '{NAMESPACE}'"
        )
        await asyncio.to_thread(
            custom_objects_api.create_namespaced_custom_object,
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )
        print(f"✅ DevServer '{TEST_DEVSERVER_NAME}' created successfully")

        # 2. Wait and check for the corresponding StatefulSet
        statefulset = await wait_for_statefulset_to_exist(
            apps_v1, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
        )

        # 3. Assert that the statefulset was found and has correct properties
        assert statefulset is not None, (
            f"StatefulSet '{TEST_DEVSERVER_NAME}' not created by operator."
        )
        assert statefulset.spec.template.spec.containers[0].image == "ubuntu:22.04"

        container = statefulset.spec.template.spec.containers[0]
        assert container.resources.requests["cpu"] == "100m"
        assert "/devserver/startup.sh" in container.args[0]

        # 3a. Wait and check for the status update on the DevServer
        await wait_for_devserver_status(
            custom_objects_api,
            name=TEST_DEVSERVER_NAME,
            namespace=NAMESPACE,
            expected_status="Running",
        )

    finally:
        # Give operator time to catch up before deleting
        await asyncio.sleep(1)

        # 4. Cleanup and verify deletion
        await cleanup_devserver(custom_objects_api, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE)

        # 5. Wait and check for the corresponding StatefulSet to be deleted
        await wait_for_statefulset_to_be_deleted(
            apps_v1, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
        )


@pytest.mark.asyncio
async def test_multiple_devservers(test_flavor, operator_running, k8s_clients):
    """
    Tests that the operator can handle multiple DevServer resources simultaneously,
    and that creating a DevServer without specifying an image uses the default.
    """
    apps_v1 = k8s_clients["apps_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]

    devserver_names = ["test-multi-1", "test-multi-2-default-image"]

    try:
        manifests = [
            {
                "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
                "kind": "DevServer",
                "metadata": {"name": devserver_names[0], "namespace": NAMESPACE},
                "spec": {
                    "flavor": test_flavor,
                    "image": "fedora:38",
                    "ssh": {"publicKey": "ssh-rsa AAAA..."},
                    "lifecycle": {"timeToLive": "1h"},
                },
            },
            {
                "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
                "kind": "DevServer",
                "metadata": {"name": devserver_names[1], "namespace": NAMESPACE},
                "spec": {
                    "flavor": test_flavor,
                    # No image specified, should use default
                    "ssh": {"publicKey": "ssh-rsa AAAA..."},
                    "lifecycle": {"timeToLive": "1h"},
                },
            },
        ]

        for manifest in manifests:
            await asyncio.to_thread(
                custom_objects_api.create_namespaced_custom_object,
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                body=manifest,
            )

        # Wait for all statefulsets to be created and verify images
        for _ in range(30):
            await asyncio.sleep(1)
            try:
                sts1 = await asyncio.to_thread(
                    apps_v1.read_namespaced_stateful_set,
                    name=devserver_names[0],
                    namespace=NAMESPACE,
                )
                sts2 = await asyncio.to_thread(
                    apps_v1.read_namespaced_stateful_set,
                    name=devserver_names[1],
                    namespace=NAMESPACE,
                )

                # Once both are found, verify images and break
                assert sts1.spec.template.spec.containers[0].image == "fedora:38"
                assert (
                    sts2.spec.template.spec.containers[0].image == "ubuntu:latest"
                )  # Verify default
                break
            except client.ApiException as e:
                if e.status != 404:
                    raise
        else:
            pytest.fail("Not all StatefulSets were created and ready in time.")

    finally:
        # Cleanup all DevServers
        for name in devserver_names:
            await cleanup_devserver(custom_objects_api, name=name, namespace=NAMESPACE)


@pytest.mark.asyncio
async def test_devserver_expires_after_ttl(test_flavor, operator_running, k8s_clients):
    """
    Tests that a DevServer with a short TTL is automatically deleted
    by the operator's cleanup process.
    """
    apps_v1 = k8s_clients["apps_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]
    devserver_name = f"test-ttl-expiry-{uuid.uuid4().hex[:6]}"
    ttl_seconds = 10

    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "metadata": {"name": devserver_name, "namespace": NAMESPACE},
        "spec": {
            "flavor": test_flavor,
            "ssh": {"publicKey": "ssh-rsa AAAA..."},
            "lifecycle": {"timeToLive": f"{ttl_seconds}s"},
        },
    }

    try:
        print(f"📝 Creating DevServer '{devserver_name}' with a {ttl_seconds}s TTL...")
        await asyncio.to_thread(
            custom_objects_api.create_namespaced_custom_object,
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # 1. Verify StatefulSet is created
        await wait_for_statefulset_to_exist(apps_v1, name=devserver_name, namespace=NAMESPACE)

        # 2. Wait for the DevServer to be garbage collected
        await wait_for_devserver_to_be_deleted(
            custom_objects_api, name=devserver_name, namespace=NAMESPACE
        )

        # 3. Verify StatefulSet is also gone (garbage collected)
        await wait_for_statefulset_to_be_deleted(
            apps_v1, name=devserver_name, namespace=NAMESPACE
        )

    finally:
        # Cleanup in case the test failed before auto-deletion
        await cleanup_devserver(custom_objects_api, name=devserver_name, namespace=NAMESPACE)


@pytest.mark.asyncio
async def test_cleanup_expired_devservers_unit():
    """
    Unit test for the cleanup_expired_devservers background task.
    This test uses mocks to simulate the Kubernetes API and time.
    """
    custom_objects_api = MagicMock()
    # The method is now called via to_thread, so we mock the underlying sync method
    custom_objects_api.list_cluster_custom_object = MagicMock()
    custom_objects_api.delete_namespaced_custom_object = MagicMock()
    logger = logging.getLogger(__name__)

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    devservers = {
        "items": [
            # Expired DevServer (created 1h ago with 30m TTL)
            {
                "metadata": {
                    "name": "expired-server",
                    "namespace": "default",
                    "creationTimestamp": one_hour_ago.isoformat(),
                },
                "spec": {"lifecycle": {"timeToLive": "30m"}},
            },
            # Active DevServer (created now with 1h TTL)
            {
                "metadata": {
                    "name": "active-server",
                    "namespace": "default",
                    "creationTimestamp": now.isoformat(),
                },
                "spec": {"lifecycle": {"timeToLive": "1h"}},
            },
        ]
    }
    custom_objects_api.list_cluster_custom_object.return_value = devservers

    # Patch asyncio.sleep to break the infinite loop after one iteration.
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # We use a side effect to raise an exception that breaks the loop.
        mock_sleep.side_effect = asyncio.CancelledError

        # We also need to mock to_thread to call our sync mocks
        async def to_thread_mock(func, *args, **kwargs):
            return func(*args, **kwargs)

        with patch("asyncio.to_thread", to_thread_mock):
            # The function will now exit with CancelledError after one loop.
            with pytest.raises(asyncio.CancelledError):
                await lifecycle.cleanup_expired_devservers(custom_objects_api, logger, 0)

    # Assert that delete was called ONLY for the expired server
    custom_objects_api.delete_namespaced_custom_object.assert_called_once_with(
        group=lifecycle.CRD_GROUP,
        version=lifecycle.CRD_VERSION,
        plural="devservers",
        name="expired-server",
        namespace="default",
        body=client.V1DeleteOptions(),
    )