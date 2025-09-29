import time
import pytest
from kubernetes import client, config, utils

# Load Kubernetes configuration
config.load_kube_config()
k8s_client = client.ApiClient()
apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()
custom_objects_api = client.CustomObjectsApi()

# Define the custom resource group and version
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_DEVSERVER = "devservers"
CRD_PLURAL_FLAVOR = "devserverflavors"

NAMESPACE = "default"
TEST_FLAVOR_NAME = "test-flavor"
TEST_DEVSERVER_NAME = "test-devserver"


@pytest.fixture(scope="function")
def test_flavor():
    """Create a test DevServerFlavor for a single test function."""
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
    custom_objects_api.create_cluster_custom_object(
        group=CRD_GROUP,
        version=CRD_VERSION,
        plural=CRD_PLURAL_FLAVOR,
        body=flavor_manifest,
    )

    yield

    try:
        custom_objects_api.delete_cluster_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            plural=CRD_PLURAL_FLAVOR,
            name=TEST_FLAVOR_NAME,
        )
    except client.ApiException as e:
        if e.status != 404:
            raise


def test_devserver_creates_deployment(test_flavor):
    """
    Tests if creating a DevServer resource leads to the creation of a
    corresponding Deployment. This is the core reconciliation test.
    """
    # 1. Create a DevServer custom resource
    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "metadata": {"name": TEST_DEVSERVER_NAME, "namespace": NAMESPACE},
        "spec": {
            "flavor": TEST_FLAVOR_NAME,
            "image": "ubuntu:22.04",
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

        # 2. Wait and check for the corresponding Deployment
        deployment = None
        for _ in range(20):  # Poll for 10 seconds (20 * 0.5s)
            time.sleep(0.5)
            try:
                deployment = apps_v1.read_namespaced_deployment(
                    name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
                )
                break
            except client.ApiException as e:
                if e.status == 404:
                    continue
                raise

        # 3. Assert that the deployment was found
        assert deployment is not None, (
            f"Deployment '{TEST_DEVSERVER_NAME}' not created by operator."
        )
        assert deployment.spec.template.spec.containers[0].image == "ubuntu:22.04"

        # 3a. Wait and check for the status update on the DevServer
        devserver_status = None
        for _ in range(10):  # Poll for 5 seconds
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

        assert devserver_status == "Running", (
            "DevServer status was not updated to 'Running'."
        )

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

        # 5. Wait and check for the corresponding Deployment to be deleted
        deployment_deleted = False
        for _ in range(20):  # Poll for 10 seconds
            time.sleep(0.5)
            try:
                apps_v1.read_namespaced_deployment(
                    name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
                )
            except client.ApiException as e:
                if e.status == 404:
                    deployment_deleted = True
                    break

        assert deployment_deleted, (
            f"Deployment '{TEST_DEVSERVER_NAME}' not deleted after DevServer cleanup."
        )
