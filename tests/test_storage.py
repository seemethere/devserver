import asyncio
import pytest
from kubernetes import client
from tests.conftest import TEST_NAMESPACE
from tests.helpers import (
    wait_for_pvc_to_exist,
    wait_for_statefulset_to_exist,
    wait_for_statefulset_to_be_deleted,
    cleanup_devserver,
)
from devserver.crds.const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVER

# Constants from the main test file
NAMESPACE = TEST_NAMESPACE


@pytest.mark.asyncio
async def test_persistent_storage_retains_on_recreation(
    test_flavor, operator_running, k8s_clients
):
    """
    Tests that a DevServer with persistentHomeSize correctly creates a
    StatefulSet with a volumeClaimTemplate and a corresponding PVC. It also
    tests that the PVC is retained when a DevServer is deleted and then
    re-attached when the same DevServer is recreated.
    """
    apps_v1 = k8s_clients["apps_v1"]
    core_v1 = k8s_clients["core_v1"]
    custom_objects_api = k8s_clients["custom_objects_api"]

    devserver_name = "test-recreation"
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
            "lifecycle": {"timeToLive": "1h"},
        },
    }

    try:
        # 1. Initial Creation
        print("PHASE 1: Creating DevServer and PVC...")
        await asyncio.to_thread(
            custom_objects_api.create_namespaced_custom_object,
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # 1a. Verify the StatefulSet's volumeClaimTemplate has the correct size
        statefulset = await wait_for_statefulset_to_exist(
            apps_v1, name=devserver_name, namespace=NAMESPACE
        )

        assert statefulset is not None
        vct = statefulset.spec.volume_claim_templates[0]
        assert vct.spec.resources.requests["storage"] == storage_size

        # 1b. Verify the PVC is created by the StatefulSet controller
        pvc = await wait_for_pvc_to_exist(core_v1, name=pvc_name, namespace=NAMESPACE)

        assert pvc is not None, f"PVC '{pvc_name}' was not created."
        assert pvc.spec.resources.requests["storage"] == storage_size
        print(f"✅ PVC '{pvc_name}' created.")

        # 2. Deletion
        print("PHASE 2: Deleting DevServer, verifying PVC remains...")
        await asyncio.to_thread(
            custom_objects_api.delete_namespaced_custom_object,
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            name=devserver_name,
        )

        # Wait for StatefulSet to be deleted
        await wait_for_statefulset_to_be_deleted(
            apps_v1, name=devserver_name, namespace=NAMESPACE
        )
        print(f"✅ StatefulSet '{devserver_name}' deleted.")

        # Assert that the PVC still exists
        try:
            await asyncio.to_thread(
                core_v1.read_namespaced_persistent_volume_claim,
                name=pvc_name,
                namespace=NAMESPACE,
            )
            print(f"✅ PVC '{pvc_name}' correctly retained after deletion.")
        except client.ApiException as e:
            if e.status == 404:
                pytest.fail(
                    f"PVC '{pvc_name}' was deleted, but should have been retained."
                )
            raise

        # 3. Re-creation
        print("PHASE 3: Re-creating DevServer, verifying it re-attaches...")
        await asyncio.to_thread(
            custom_objects_api.create_namespaced_custom_object,
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL_DEVSERVER,
            body=devserver_manifest,
        )

        # Wait for StatefulSet to be re-created and become ready
        await wait_for_statefulset_to_exist(
            apps_v1, name=devserver_name, namespace=NAMESPACE
        )

        # A further wait for it to be ready
        for _ in range(60):  # Longer wait for re-attachment
            await asyncio.sleep(1)
            try:
                sts = await asyncio.to_thread(
                    apps_v1.read_namespaced_stateful_set,
                    name=devserver_name,
                    namespace=NAMESPACE,
                )
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
        await cleanup_devserver(custom_objects_api, name=devserver_name, namespace=NAMESPACE)
