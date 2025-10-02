import time
import pytest
from kubernetes import client
from tests.conftest import TEST_NAMESPACE

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
        statefulset = None
        print(
            f"⏳ Waiting for statefulset '{TEST_DEVSERVER_NAME}' to be created by operator..."
        )
        for i in range(30):
            time.sleep(0.5)
            try:
                statefulset = apps_v1.read_namespaced_stateful_set(
                    name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
                )
                print(f"✅ StatefulSet found after {i + 1} attempts!")
                break
            except client.ApiException as e:
                if e.status == 404:
                    if i % 10 == 0:
                        print(
                            f"⏳ Still waiting for statefulset (attempt {i + 1}/30)..."
                        )
                    continue
                raise

        # 3. Assert that the statefulset was found and has correct properties
        assert statefulset is not None, (
            f"StatefulSet '{TEST_DEVSERVER_NAME}' not created by operator."
        )
        assert statefulset.spec.template.spec.containers[0].image == "ubuntu:22.04"

        container = statefulset.spec.template.spec.containers[0]
        assert container.resources.requests["cpu"] == "100m"
        assert "sleep infinity" in container.args[0]

        # 3a. Wait and check for the status update on the DevServer
        devserver_status = None
        for _ in range(20):
            time.sleep(0.5)
            ds = custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=TEST_DEVSERVER_NAME,
            )
            if "status" in ds and "phase" in ds["status"]:
                devserver_status = ds["status"]["phase"]
                break

        assert devserver_status == "Running"

    finally:
        # 4. Cleanup and verify deletion
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

        # 5. Wait and check for the corresponding StatefulSet to be deleted
        statefulset_deleted = False
        for _ in range(60):
            time.sleep(1)
            try:
                apps_v1.read_namespaced_stateful_set(
                    name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
                )
            except client.ApiException as e:
                if e.status == 404:
                    statefulset_deleted = True
                    break

        assert statefulset_deleted, (
            f"StatefulSet '{TEST_DEVSERVER_NAME}' not deleted after DevServer cleanup."
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
        statefulset = None
        for _ in range(30):
            time.sleep(0.5)
            try:
                statefulset = apps_v1.read_namespaced_stateful_set(
                    name=devserver_name, namespace=NAMESPACE
                )
                break
            except client.ApiException as e:
                if e.status == 404:
                    continue
                raise

        # Verify the default image was used
        assert statefulset is not None
        container = statefulset.spec.template.spec.containers[0]
        assert container.image == "ubuntu:latest"

    finally:
        # Cleanup
        try:
            custom_objects_api.delete_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=devserver_name,
            )
        except client.ApiException as e:
            if e.status != 404:
                raise


def test_multiple_devservers(test_flavor, operator_running, k8s_clients):
    """
    Tests that the operator can handle multiple DevServer resources simultaneously.
    """
    apps_v1 = k8s_clients["apps_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]

    devserver_names = ["test-multi-1", "test-multi-2"]

    try:
        images = ["nginx:alpine", "alpine:latest"]
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
            try:
                custom_objects_api.delete_namespaced_custom_object(
                    group=CRD_GROUP,
                    version=CRD_VERSION,
                    namespace=NAMESPACE,
                    plural=CRD_PLURAL_DEVSERVER,
                    name=name,
                )
            except client.ApiException as e:
                if e.status != 404:
                    raise


def test_devserver_expires_after_ttl(test_flavor, operator_running, k8s_clients):
    """
    Tests that a DevServer is automatically deleted after its timeToLive expires.
    """
    custom_objects_api = k8s_clients["custom_objects_api"]
    devserver_name = "test-expiry"

    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "metadata": {"name": devserver_name, "namespace": NAMESPACE},
        "spec": {
            "flavor": test_flavor,
            "ssh": {"publicKey": "ssh-rsa AAAA..."},
            "lifecycle": {"timeToLive": "1s"},
        },
    }

    try:
        # Create the DevServer
        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # Wait a bit longer than the TTL for the operator to delete it
        print("⏳ Waiting for DevServer to expire and be deleted...")
        for _ in range(15):  # Wait up to 15 seconds
            time.sleep(1)
            try:
                obj = custom_objects_api.get_namespaced_custom_object(
                    group=CRD_GROUP,
                    version=CRD_VERSION,
                    namespace=NAMESPACE,
                    plural=CRD_PLURAL_DEVSERVER,
                    name=devserver_name,
                )
                if obj.get("metadata", {}).get("deletionTimestamp"):
                    print(
                        "✅ DevServer has deletion timestamp. Assuming deletion is in progress."
                    )
                    break
            except client.ApiException as e:
                if e.status == 404:
                    print("✅ DevServer successfully deleted.")
                    break
                raise
        else:
            pytest.fail(
                "DevServer was not deleted after expiration within the time limit."
            )

        print("✅ DevServer was deleted successfully after expiration.")

    finally:
        # Cleanup in case the test fails before deletion
        try:
            custom_objects_api.delete_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name=devserver_name,
            )
        except client.ApiException as e:
            if e.status != 404:
                raise
