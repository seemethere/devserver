import time
import pytest
from kubernetes import client, config
from tests.conftest import TEST_NAMESPACE

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

NAMESPACE = TEST_NAMESPACE
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


def test_devserver_creates_deployment(test_flavor, operator_running):
    """
    Tests if creating a DevServer resource leads to the creation of a
    corresponding Deployment. This is the core reconciliation test with
    the actual operator running.
    """
    print(f"🧪 Starting test_devserver_creates_deployment in namespace: {NAMESPACE}")
    
    # Verify the flavor exists
    try:
        custom_objects_api.get_cluster_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            plural=CRD_PLURAL_FLAVOR,
            name=TEST_FLAVOR_NAME,
        )
        print(f"✅ DevServerFlavor '{TEST_FLAVOR_NAME}' found")
    except Exception as e:
        print(f"❌ DevServerFlavor '{TEST_FLAVOR_NAME}' not found: {e}")
        raise
    
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
        print(f"📝 Creating DevServer '{TEST_DEVSERVER_NAME}' in namespace '{NAMESPACE}'")
        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )
        print(f"✅ DevServer '{TEST_DEVSERVER_NAME}' created successfully")

        # 2. Wait and check for the corresponding Deployment (operator should create it)
        deployment = None
        print(f"⏳ Waiting for deployment '{TEST_DEVSERVER_NAME}' to be created by operator...")
        for i in range(30):  # Poll for 15 seconds (30 * 0.5s) - longer timeout for operator
            time.sleep(0.5)
            try:
                deployment = apps_v1.read_namespaced_deployment(
                    name=TEST_DEVSERVER_NAME, namespace=NAMESPACE
                )
                print(f"✅ Deployment found after {i+1} attempts!")
                break
            except client.ApiException as e:
                if e.status == 404:
                    if i % 10 == 0:  # Log every 5 seconds
                        print(f"⏳ Still waiting for deployment (attempt {i+1}/30)...")
                    continue
                raise

        # 3. Assert that the deployment was found and has correct properties
        assert deployment is not None, (
            f"Deployment '{TEST_DEVSERVER_NAME}' not created by operator."
        )
        assert deployment.spec.template.spec.containers[0].image == "ubuntu:22.04"
        
        # Verify the deployment has the correct resource specifications from the flavor
        container = deployment.spec.template.spec.containers[0]
        assert container.resources.requests["cpu"] == "100m"
        assert container.resources.requests["memory"] == "128Mi"
        assert container.resources.limits["cpu"] == "500m"
        assert container.resources.limits["memory"] == "512Mi"
        
        # Verify container is set up to keep running
        assert container.command == ["sleep"]
        assert container.args == ["infinity"]

        # 3a. Wait and check for the status update on the DevServer
        devserver_status = None
        devserver_message = None
        for _ in range(20):  # Poll for 10 seconds
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
                devserver_message = ds["status"].get("message", "")
                break

        assert devserver_status == "Running", (
            f"DevServer status was not updated to 'Running'. Got: {devserver_status}"
        )
        assert "created successfully" in devserver_message, (
            f"DevServer status message unexpected. Got: {devserver_message}"
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
        # (Should be garbage collected due to owner reference)
        deployment_deleted = False
        for _ in range(30):  # Poll for 15 seconds - longer timeout for cleanup
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


def test_devserver_missing_flavor_error(operator_running):
    """
    Tests that creating a DevServer with a non-existent flavor
    properly handles the error condition.
    """
    # Create a DevServer with a non-existent flavor
    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer", 
        "metadata": {"name": "test-missing-flavor", "namespace": NAMESPACE},
        "spec": {
            "flavor": "non-existent-flavor",
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

        # Wait to see if the operator handles the error properly
        # We don't need to verify specific status since the main test is that
        # no deployment should be created when flavor is missing
        time.sleep(2)  # Give operator time to process

        # Verify that no deployment was created due to the error
        with pytest.raises(client.ApiException) as exc_info:
            apps_v1.read_namespaced_deployment(
                name="test-missing-flavor", namespace=NAMESPACE
            )
        assert exc_info.value.status == 404, "Deployment should not exist for invalid flavor"

    finally:
        # Cleanup
        try:
            custom_objects_api.delete_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                name="test-missing-flavor",
            )
        except client.ApiException as e:
            if e.status != 404:
                raise


def test_devserver_with_default_image(test_flavor, operator_running):
    """
    Tests that creating a DevServer without specifying an image
    uses the default image (ubuntu:latest).
    """
    devserver_name = "test-default-image"
    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "metadata": {"name": devserver_name, "namespace": NAMESPACE},
        "spec": {
            "flavor": TEST_FLAVOR_NAME,
            # No image specified - should use default
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

        # Wait for deployment to be created
        deployment = None
        for _ in range(30):
            time.sleep(0.5)
            try:
                deployment = apps_v1.read_namespaced_deployment(
                    name=devserver_name, namespace=NAMESPACE
                )
                break
            except client.ApiException as e:
                if e.status == 404:
                    continue
                raise

        # Verify the default image was used
        assert deployment is not None
        container = deployment.spec.template.spec.containers[0]
        assert container.image == "ubuntu:latest", f"Expected ubuntu:latest, got {container.image}"

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


def test_multiple_devservers(test_flavor, operator_running):
    """
    Tests that the operator can handle multiple DevServer resources simultaneously.
    """
    devserver_names = ["test-multi-1", "test-multi-2", "test-multi-3"]
    
    try:
        # Create multiple DevServers with different well-known images
        images = ["nginx:alpine", "alpine:latest", "busybox:latest"]
        for i, name in enumerate(devserver_names):
            devserver_manifest = {
                "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
                "kind": "DevServer",
                "metadata": {"name": name, "namespace": NAMESPACE},
                "spec": {
                    "flavor": TEST_FLAVOR_NAME,
                    "image": images[i],  # Use different real images
                },
            }
            custom_objects_api.create_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL_DEVSERVER,
                body=devserver_manifest,
            )

        # Wait for all deployments to be created
        created_deployments = []
        for _ in range(30):
            time.sleep(0.5)
            deployments_found = 0
            for name in devserver_names:
                try:
                    deployment = apps_v1.read_namespaced_deployment(
                        name=name, namespace=NAMESPACE
                    )
                    if name not in created_deployments:
                        created_deployments.append(name)
                    deployments_found += 1
                except client.ApiException as e:
                    if e.status != 404:
                        raise
            
            if deployments_found == len(devserver_names):
                break

        # Verify all deployments were created with correct images
        assert len(created_deployments) == len(devserver_names), (
            f"Not all deployments created. Expected {len(devserver_names)}, got {len(created_deployments)}"
        )
        
        for i, name in enumerate(devserver_names):
            deployment = apps_v1.read_namespaced_deployment(
                name=name, namespace=NAMESPACE
            )
            expected_image = images[i]
            actual_image = deployment.spec.template.spec.containers[0].image
            assert actual_image == expected_image, (
                f"Wrong image for {name}. Expected {expected_image}, got {actual_image}"
            )

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
