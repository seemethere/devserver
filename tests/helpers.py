import time
import pytest
from kubernetes import client
from typing import Any, Callable, TypeVar

# Constants for polling
POLL_INTERVAL = 0.5

# Constants from the main test file
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_DEVSERVER = "devservers"
CRD_PLURAL_DEVSERVERUSER = "devserverusers"


T = TypeVar("T")


def wait_for(
    callable: Callable[[], T],
    timeout: int = 30,
    interval: float = POLL_INTERVAL,
    failure_message: str = "Condition not met within timeout",
) -> T:
    """
    Generic wait utility that polls a callable until it returns a truthy value
    or a timeout is reached.
    The callable is responsible for handling exceptions and returning a falsy
    value if the condition is not yet met.
    Args:
        callable: A function that is polled. If it returns a truthy value,
                  the wait is considered successful.
        timeout: Total time to wait in seconds.
        interval: Time to sleep between polls in seconds.
        failure_message: The message for pytest.fail if the timeout is reached.
    Returns:
        The truthy value returned by the callable.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = callable()
        if result:
            return result
        time.sleep(interval)
    pytest.fail(failure_message)


def wait_for_statefulset_to_exist(
    apps_v1_api: client.AppsV1Api, name: str, namespace: str, timeout: int = 30
) -> Any:
    """Waits for a StatefulSet to exist and returns it."""
    print(f"⏳ Waiting for statefulset '{name}' to be created by operator...")

    def check():
        try:
            return apps_v1_api.read_namespaced_stateful_set(
                name=name, namespace=namespace
            )
        except client.ApiException as e:
            if e.status == 404:
                return None  # Not found yet, continue polling
            raise  # Other errors should fail the test

    statefulset = wait_for(
        check,
        timeout=timeout,
        failure_message=f"StatefulSet '{name}' did not appear within {timeout} seconds.",
    )
    print(f"✅ StatefulSet '{name}' found.")
    return statefulset


def wait_for_statefulset_to_be_deleted(
    apps_v1_api: client.AppsV1Api, name: str, namespace: str, timeout: int = 60
):
    """Waits for a StatefulSet to be deleted."""
    print(f"⏳ Waiting for statefulset '{name}' to be deleted...")

    def check():
        try:
            apps_v1_api.read_namespaced_stateful_set(name=name, namespace=namespace)
            return None  # Still exists, continue polling
        except client.ApiException as e:
            if e.status == 404:
                return True  # Successfully deleted
            raise

    wait_for(
        check,
        timeout=timeout,
        failure_message=f"StatefulSet '{name}' was not deleted within {timeout} seconds.",
    )
    print(f"✅ StatefulSet '{name}' deleted.")


def wait_for_devserver_to_be_deleted(
    custom_objects_api: client.CustomObjectsApi,
    name: str,
    namespace: str,
    timeout: int = 30,
):
    """Waits for a DevServer to be deleted."""
    print(f"⏳ Waiting for DevServer '{name}' to be deleted...")

    def check():
        try:
            custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural=CRD_PLURAL_DEVSERVER,
                name=name,
            )
            return None  # Still exists
        except client.ApiException as e:
            if e.status == 404:
                return True  # Deleted
            raise

    wait_for(
        check,
        timeout=timeout,
        failure_message=f"DevServer '{name}' was not deleted within {timeout} seconds.",
    )
    print(f"✅ DevServer '{name}' deleted.")



def wait_for_devserver_to_exist(
    custom_objects_api: client.CustomObjectsApi, name: str, namespace: str, timeout: int = 10
) -> Any:
    """
    Waits for a DevServer custom resource object to exist in the Kubernetes API.
    """
    print(f"⏳ Waiting for DevServer '{name}' to exist...")

    def check():
        try:
            return custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural=CRD_PLURAL_DEVSERVER,
                name=name,
            )
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise

    devserver = wait_for(
        check,
        timeout=timeout,
        failure_message=f"DevServer '{name}' did not appear within {timeout} seconds.",
    )
    print(f"✅ DevServer '{name}' found.")
    return devserver


def wait_for_pvc_to_exist(
    core_v1_api: client.CoreV1Api, name: str, namespace: str, timeout: int = 30
) -> Any:
    """Waits for a PVC to exist and returns it."""
    print(f"⏳ Waiting for PVC '{name}' to appear...")

    def check():
        try:
            return core_v1_api.read_namespaced_persistent_volume_claim(
                name=name, namespace=namespace
            )
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise

    pvc = wait_for(
        check,
        timeout=timeout,
        failure_message=f"PVC '{name}' did not appear within {timeout} seconds.",
    )
    print(f"✅ PVC '{name}' found.")
    return pvc


def wait_for_devserver_status(
    custom_objects_api: client.CustomObjectsApi,
    name: str,
    namespace: str,
    expected_status: str = "Running",
    timeout: int = 30,
):
    """
    Waits for a DevServer to reach a specific status in its `.status.phase` field.
    """
    print(f"⏳ Waiting for DevServer '{name}' status to become '{expected_status}'...")

    def check():
        try:
            ds = custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural=CRD_PLURAL_DEVSERVER,
                name=name,
            )
            if "status" in ds and "phase" in ds["status"]:
                if ds["status"]["phase"] == expected_status:
                    return True
            return None
        except client.ApiException as e:
            if e.status == 404:
                return None  # Not created yet
            raise

    wait_for(
        check,
        timeout=timeout,
        failure_message=f"DevServer '{name}' did not reach status '{expected_status}' within {timeout}s.",
    )
    print(f"✅ DevServer '{name}' reached status '{expected_status}'.")


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

    def check():
        try:
            user = custom_objects_api.get_cluster_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                plural=CRD_PLURAL_DEVSERVERUSER,
                name=name,
            )
            if "status" in user and "phase" in user["status"]:
                if user["status"]["phase"] == expected_status:
                    return True
            return None
        except client.ApiException as e:
            if e.status == 404:
                return None  # Not created yet
            raise

    wait_for(
        check,
        timeout=timeout,
        failure_message=f"DevServerUser '{name}' did not reach status '{expected_status}' within {timeout}s.",
    )
    print(f"✅ DevServerUser '{name}' reached status '{expected_status}'.")


def wait_for_cluster_custom_object_to_be_deleted(
    custom_objects_api: client.CustomObjectsApi,
    group: str,
    version: str,
    plural: str,
    name: str,
    timeout: int = 30,
):
    """Waits for a cluster-scoped custom object to be deleted."""
    print(f"⏳ Waiting for cluster custom object '{name}' to be deleted...")

    def check():
        try:
            custom_objects_api.get_cluster_custom_object(
                group=group, version=version, plural=plural, name=name
            )
            return None  # Still exists
        except client.ApiException as e:
            if e.status == 404:
                return True  # Deleted
            raise

    wait_for(
        check,
        timeout=timeout,
        failure_message=f"Cluster custom object '{name}' was not deleted within {timeout}s.",
    )
    print(f"✅ Cluster custom object '{name}' deleted.")


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
