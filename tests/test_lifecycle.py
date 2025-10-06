import time
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

# Constants from the main test file
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_DEVSERVER = "devservers"
NAMESPACE = TEST_NAMESPACE
TEST_DEVSERVER_NAME = "test-devserver"


def test_devserver_creates_statefulset(test_flavor, operator_running, k8s_clients):
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
        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )
        print(f"✅ DevServer '{TEST_DEVSERVER_NAME}' created successfully")

        # 2. Wait and check for the corresponding StatefulSet
        statefulset = wait_for_statefulset_to_exist(
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
        wait_for_devserver_status(
            custom_objects_api,
            name=TEST_DEVSERVER_NAME,
            namespace=NAMESPACE,
            expected_status="Running",
        )

    finally:
        # Give operator time to catch up before deleting
        time.sleep(1)

        # 4. Cleanup and verify deletion
        cleanup_devserver(custom_objects_api, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE)

        # 5. Wait and check for the corresponding StatefulSet to be deleted
        wait_for_statefulset_to_be_deleted(
            apps_v1, name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
        )


def test_devserver_with_default_image(test_flavor, operator_running, k8s_clients):
    """
    Tests that creating a DevServer without specifying an image
    uses the default image (ubuntu:latest).
    """
    apps_v1 = k8s_clients["apps_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]

    devserver_name = "test-default-image"
    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "metadata": {"name": devserver_name, "namespace": NAMESPACE},
        "spec": {
            "flavor": test_flavor,
            "ssh": {"publicKey": "ssh-rsa AAAA..."},
            "lifecycle": {"timeToLive": "1h"},
        },
    }

    try:
        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # Wait for statefulset to be created
        statefulset = wait_for_statefulset_to_exist(
            apps_v1, name=devserver_name, namespace=NAMESPACE
        )

        # Verify the default image was used
        assert statefulset is not None
        container = statefulset.spec.template.spec.containers[0]
        assert container.image == "ubuntu:latest"

    finally:
        # Cleanup
        cleanup_devserver(custom_objects_api, name=devserver_name, namespace=NAMESPACE)


def test_multiple_devservers(test_flavor, operator_running, k8s_clients):
    """
    Tests that the operator can handle multiple DevServer resources simultaneously.
    """
    apps_v1 = k8s_clients["apps_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]

    devserver_names = ["test-multi-1", "test-multi-2"]

    try:
        images = ["ubuntu:22.04", "fedora:38"]
        for i, name in enumerate(devserver_names):
            devserver_manifest = {
                "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
                "kind": "DevServer",
                "metadata": {"name": name, "namespace": NAMESPACE},
                "spec": {
                    "flavor": test_flavor,
                    "image": images[i],
                    "ssh": {"publicKey": "ssh-rsa AAAA..."},
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

        # Wait for all statefulsets to be created
        for _ in range(30):
            time.sleep(0.5)

            all_found = True
            try:
                for name in devserver_names:
                    apps_v1.read_namespaced_stateful_set(name=name, namespace=NAMESPACE)
            except client.ApiException as e:
                if e.status == 404:
                    all_found = False

            if all_found:
                break
        else:
            pytest.fail("Not all StatefulSets were created in time.")

    finally:
        # Cleanup all DevServers
        for name in devserver_names:
            cleanup_devserver(custom_objects_api, name=name, namespace=NAMESPACE)


def test_devserver_expires_after_ttl(test_flavor, operator_running, k8s_clients):
    """
    Tests that a DevServer with a short TTL is automatically deleted
    by the operator's cleanup process.
    """
    apps_v1 = k8s_clients["apps_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]
    devserver_name = "test-ttl-expiry"
    ttl_seconds = 5

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
        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # 1. Verify StatefulSet is created
        wait_for_statefulset_to_exist(apps_v1, name=devserver_name, namespace=NAMESPACE)

        # 2. Wait for the DevServer to be garbage collected
        wait_for_devserver_to_be_deleted(
            custom_objects_api, name=devserver_name, namespace=NAMESPACE
        )

        # 3. Verify StatefulSet is also gone (garbage collected)
        wait_for_statefulset_to_be_deleted(
            apps_v1, name=devserver_name, namespace=NAMESPACE
        )

    finally:
        # Cleanup in case the test failed before auto-deletion
        cleanup_devserver(custom_objects_api, name=devserver_name, namespace=NAMESPACE)