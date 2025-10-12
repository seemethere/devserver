import time
import pytest
from kubernetes import client
from typing import Any

# Constants for polling
POLL_INTERVAL = 0.5

# Constants from the main test file
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_DEVSERVER = "devservers"
CRD_PLURAL_DEVSERVERUSER = "devserverusers"


def wait_for_statefulset_to_exist(
    apps_v1_api: client.AppsV1Api, name: str, namespace: str, timeout: int = 30
) -> Any:
    """Waits for a StatefulSet to exist and returns it."""
    print(f"⏳ Waiting for statefulset '{name}' to be created by operator...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            statefulset = apps_v1_api.read_namespaced_stateful_set(
                name=name, namespace=namespace
            )
            print(f"✅ StatefulSet '{name}' found.")
            return statefulset
        except client.ApiException as e:
            if e.status == 404:
                time.sleep(POLL_INTERVAL)
            else:
                raise
    pytest.fail(f"StatefulSet '{name}' did not appear within {timeout} seconds.")


def wait_for_statefulset_to_be_deleted(
    apps_v1_api: client.AppsV1Api, name: str, namespace: str, timeout: int = 60
):
    """Waits for a StatefulSet to be deleted."""
    print(f"⏳ Waiting for statefulset '{name}' to be deleted...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            apps_v1_api.read_namespaced_stateful_set(name=name, namespace=namespace)
            time.sleep(POLL_INTERVAL)
        except client.ApiException as e:
            if e.status == 404:
                print(f"✅ StatefulSet '{name}' deleted.")
                return
            else:
                raise
    pytest.fail(f"StatefulSet '{name}' was not deleted within {timeout} seconds.")


def wait_for_devserver_to_be_deleted(
    custom_objects_api: client.CustomObjectsApi,
    name: str,
    namespace: str,
    timeout: int = 30,
):
    """Waits for a DevServer to be deleted."""
    print(f"⏳ Waiting for DevServer '{name}' to be deleted...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural=CRD_PLURAL_DEVSERVER,
                name=name,
            )
            time.sleep(POLL_INTERVAL)
        except client.ApiException as e:
            if e.status == 404:
                print(f"✅ DevServer '{name}' deleted.")
                return
            else:
                raise
    pytest.fail(f"DevServer '{name}' was not deleted within {timeout} seconds.")


def wait_for_devserver_to_exist(
    custom_objects_api: client.CustomObjectsApi, name: str, namespace: str, timeout: int = 10
) -> Any:
    """
    Waits for a DevServer custom resource object to exist in the Kubernetes API.

    This function only confirms the object's presence in the API server. It does
    not wait for the operator to reconcile the object or for any underlying
    resources (like Pods) to be created or become ready.

    Use this when you need to test logic that happens before the operator has
    acted, such as verifying the behavior of a CLI command that reads the object
    immediately after creation.
    """
    print(f"⏳ Waiting for DevServer '{name}' to exist...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            devserver = custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural=CRD_PLURAL_DEVSERVER,
                name=name,
            )
            print(f"✅ DevServer '{name}' found.")
            return devserver
        except client.ApiException as e:
            if e.status == 404:
                time.sleep(POLL_INTERVAL)
            else:
                raise
    pytest.fail(f"DevServer '{name}' did not appear within {timeout} seconds.")


def wait_for_pvc_to_exist(
    core_v1_api: client.CoreV1Api, name: str, namespace: str, timeout: int = 30
) -> Any:
    """Waits for a PVC to exist and returns it."""
    print(f"⏳ Waiting for PVC '{name}' to appear...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            pvc = core_v1_api.read_namespaced_persistent_volume_claim(
                name=name, namespace=namespace
            )
            print(f"✅ PVC '{name}' found.")
            return pvc
        except client.ApiException as e:
            if e.status == 404:
                time.sleep(POLL_INTERVAL)
            else:
                raise
    pytest.fail(f"PVC '{name}' did not appear within {timeout} seconds.")


def wait_for_devserver_status(
    custom_objects_api: client.CustomObjectsApi,
    name: str,
    namespace: str,
    expected_status: str = "Running",
    timeout: int = 30,
):
    """
    Waits for a DevServer to reach a specific status in its `.status.phase` field.

    This function waits for the operator to act on the DevServer object and
    update its status. It implies that the object exists and that the
    reconciliation loop has progressed to a certain point.

    Use this for end-to-end tests where you need the underlying resources
    (e.g., the Pod) to be in a certain state (e.g., 'Running') before
    proceeding with the test.
    """
    print(f"⏳ Waiting for DevServer '{name}' status to become '{expected_status}'...")
    start_time = time.time()
    current_status = None
    while time.time() - start_time < timeout:
        try:
            ds = custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural=CRD_PLURAL_DEVSERVER,
                name=name,
            )
            if "status" in ds and "phase" in ds["status"]:
                current_status = ds["status"]["phase"]
                if current_status == expected_status:
                    print(f"✅ DevServer '{name}' reached status '{expected_status}'.")
                    return
            time.sleep(POLL_INTERVAL)
        except client.ApiException as e:
            if e.status == 404:
                # It might not have been created yet
                time.sleep(POLL_INTERVAL)
            else:
                raise
    pytest.fail(
        f"DevServer '{name}' did not reach status '{expected_status}' within {timeout} seconds. "
        f"Last known status: {current_status}"
    )


def wait_for_devserveruser_status(
    custom_objects_api: client.CustomObjectsApi,
    name: str,
    expected_status: str = "Ready",
    timeout: int = 10,
):
    """
    Waits for a DevServerUser to reach a specific status in its `.status.phase` field.
    """
    print(f"⏳ Waiting for DevServerUser '{name}' status to become '{expected_status}'...")
    start_time = time.time()
    current_status = None
    while time.time() - start_time < timeout:
        try:
            user = custom_objects_api.get_cluster_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                plural=CRD_PLURAL_DEVSERVERUSER,
                name=name,
            )
            if "status" in user and "phase" in user["status"]:
                current_status = user["status"]["phase"]
                if current_status == expected_status:
                    print(f"✅ DevServerUser '{name}' reached status '{expected_status}'.")
                    return
            time.sleep(POLL_INTERVAL)
        except client.ApiException as e:
            if e.status == 404:
                # It might not have been created yet
                time.sleep(POLL_INTERVAL)
            else:
                raise
    pytest.fail(
        f"DevServerUser '{name}' did not reach status '{expected_status}' within {timeout} seconds. "
        f"Last known status: {current_status}"
    )


def wait_for_cluster_custom_object_to_be_deleted(
    custom_objects_api: client.CustomObjectsApi,
    group: str,
    version: str,
    plural: str,
    name: str,
    timeout: int = 30,
):
    """Waits for a cluster-scoped custom object to be deleted."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            custom_objects_api.get_cluster_custom_object(
                group=group, version=version, plural=plural, name=name
            )
            time.sleep(POLL_INTERVAL)
        except client.ApiException as e:
            if e.status == 404:
                return
            raise
    pytest.fail(f"Cluster custom object '{name}' was not deleted within {timeout}s.")


def cleanup_devserver(
    custom_objects_api: client.CustomObjectsApi, name: str, namespace: str
):
    """Safely delete a DevServer, ignoring not-found errors."""
    try:
        print(f"🧹 Cleaning up DevServer '{name}' in namespace '{namespace}'...")
        custom_objects_api.delete_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=namespace,
            plural=CRD_PLURAL_DEVSERVER,
            name=name,
            body=client.V1DeleteOptions(),
        )
    except client.ApiException as e:
        if e.status == 404:
            print(f"ℹ️ DevServer '{name}' was already deleted.")
        else:
            print(f"⚠️ Error during cleanup of DevServer '{name}': {e}")
            raise
