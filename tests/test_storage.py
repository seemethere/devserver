import time
import pytest
from kubernetes import client
from tests.conftest import TEST_NAMESPACE

# Constants from the main test file
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_DEVSERVER = "devservers"
NAMESPACE = TEST_NAMESPACE


def test_devserver_persistent_storage(test_flavor, operator_running, k8s_clients):
    """
    Tests that a DevServer with persistentHomeSize correctly creates a
    StatefulSet with a volumeClaimTemplate and a corresponding PVC.
    """
    apps_v1 = k8s_clients["apps_v1"]
    core_v1 = k8s_clients["core_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]

    devserver_name = "test-persistent-storage"
    storage_size = "1Gi"
    pvc_name = f"home-{devserver_name}-0"

    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "metadata": {"name": devserver_name, "namespace": NAMESPACE},
        "spec": {
            "flavor": test_flavor,
            "persistentHomeSize": storage_size,
            "ssh": {"publicKey": "ssh-rsa AAAA..."},
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

        # 1. Verify the StatefulSet's volumeClaimTemplate has the correct size
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
        
        assert statefulset is not None
        vct = statefulset.spec.volume_claim_templates[0]
        assert vct.spec.resources.requests["storage"] == storage_size

        # 2. Verify the PVC is created by the StatefulSet controller
        pvc = None
        for _ in range(30):
            time.sleep(0.5)
            try:
                pvc = core_v1.read_namespaced_persistent_volume_claim(
                    name=pvc_name, namespace=NAMESPACE
                )
                break
            except client.ApiException as e:
                if e.status == 404:
                    continue
                raise

        assert pvc is not None, f"PVC '{pvc_name}' was not created."
        assert pvc.spec.resources.requests["storage"] == storage_size

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
        
        # Note: The PVC created by the StatefulSet is not automatically
        # garbage collected to prevent data loss. It would need to be
        # cleaned up manually in a real environment. For the test,
        # the namespace cleanup in conftest.py will handle it.


def test_persistent_storage_retains_on_recreation(test_flavor, operator_running, k8s_clients):
    """
    Tests that the PVC is retained when a DevServer is deleted and then
    re-attached when the same DevServer is recreated.
    """
    apps_v1 = k8s_clients["apps_v1"]
    core_v1 = k8s_clients["core_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]

    devserver_name = "test-recreation"
    pvc_name = f"home-{devserver_name}-0"

    devserver_manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "DevServer",
        "metadata": {"name": devserver_name, "namespace": NAMESPACE},
        "spec": {
            "flavor": test_flavor,
            "persistentHomeSize": "1Gi",
            "ssh": {"publicKey": "ssh-rsa AAAA..."},
        },
    }

    try:
        # 1. Initial Creation
        print("PHASE 1: Creating DevServer and PVC...")
        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # Wait for PVC to be created
        for _ in range(30):
            time.sleep(0.5)
            try:
                core_v1.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=NAMESPACE)
                print(f"✅ PVC '{pvc_name}' created.")
                break
            except client.ApiException as e:
                if e.status != 404:
                    raise
        else:
            pytest.fail(f"PVC '{pvc_name}' was not created in phase 1.")

        # 2. Deletion
        print("PHASE 2: Deleting DevServer, verifying PVC remains...")
        custom_objects_api.delete_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            name=devserver_name,
        )

        # Wait for StatefulSet to be deleted
        for _ in range(30):
            time.sleep(0.5)
            try:
                apps_v1.read_namespaced_stateful_set(name=devserver_name, namespace=NAMESPACE)
            except client.ApiException as e:
                if e.status == 404:
                    print(f"✅ StatefulSet '{devserver_name}' deleted.")
                    break
        else:
            pytest.fail(f"StatefulSet '{devserver_name}' was not deleted in phase 2.")
        
        # Assert that the PVC still exists
        try:
            core_v1.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=NAMESPACE)
            print(f"✅ PVC '{pvc_name}' correctly retained after deletion.")
        except client.ApiException as e:
            if e.status == 404:
                pytest.fail(f"PVC '{pvc_name}' was deleted, but should have been retained.")
            raise

        # 3. Re-creation
        print("PHASE 3: Re-creating DevServer, verifying it re-attaches...")
        custom_objects_api.create_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # Wait for StatefulSet to be re-created and become ready
        for _ in range(60): # Longer wait for re-attachment
            time.sleep(1)
            try:
                sts = apps_v1.read_namespaced_stateful_set(name=devserver_name, namespace=NAMESPACE)
                if sts.status.ready_replicas == 1:
                    print(f"✅ StatefulSet '{devserver_name}' re-created and ready.")
                    break
            except client.ApiException as e:
                if e.status != 404:
                    raise
        else:
            pytest.fail("StatefulSet did not become ready after re-creation.")

    finally:
        # Final cleanup
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
