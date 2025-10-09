import pytest
from kubernetes import client
import time

from devserver.operator.user_reconciler import get_user_namespace

# Constants
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
CRD_PLURAL_DEVSERVERUSER = "devserverusers"
TEST_USER_NAME = "reconciler-test-user"


@pytest.mark.usefixtures("operator_running")
class TestUserReconciler:
    """
    Integration tests for the User Reconciler logic.
    """

    def test_user_creation_creates_namespace_and_rbac(self, k8s_clients, request):
        """
        Tests that creating a DevServerUser results in the creation of:
        1. A dedicated namespace.
        2. A Role within that namespace.
        3. A RoleBinding within that namespace.
        """
        custom_objects_api = k8s_clients["custom_objects_api"]
        core_v1_api = k8s_clients["core_v1"]
        rbac_v1_api = k8s_clients["rbac_v1"]
        user_namespace = get_user_namespace(TEST_USER_NAME)

        user_manifest = {
            "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
            "kind": "DevServerUser",
            "metadata": {"name": TEST_USER_NAME},
            "spec": {"username": TEST_USER_NAME},
        }

        def cleanup():
            try:
                custom_objects_api.delete_cluster_custom_object(
                    group=CRD_GROUP,
                    version=CRD_VERSION,
                    plural=CRD_PLURAL_DEVSERVERUSER,
                    name=TEST_USER_NAME,
                )
                # Allow time for the operator to clean up the namespace
                time.sleep(2)
            except client.ApiException as e:
                if e.status != 404:
                    print(f"Error cleaning up DevServerUser: {e}")

        request.addfinalizer(cleanup)

        # Create the DevServerUser
        custom_objects_api.create_cluster_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            plural=CRD_PLURAL_DEVSERVERUSER,
            body=user_manifest,
        )

        # 1. Verify Namespace was created
        for _ in range(10):
            try:
                ns = core_v1_api.read_namespace(name=user_namespace)
                assert ns.metadata.name == user_namespace
                break
            except client.ApiException as e:
                if e.status == 404:
                    time.sleep(1)
                else:
                    raise
        else:
            pytest.fail(f"Namespace {user_namespace} was not created.")

        # 2. Verify Role was created
        role = rbac_v1_api.read_namespaced_role(name="devserver-user-role", namespace=user_namespace)
        assert role.metadata.name == "devserver-user-role"

        # 3. Verify RoleBinding was created
        rb = rbac_v1_api.read_namespaced_role_binding(name="devserver-user-binding", namespace=user_namespace)
        assert rb.subjects[0].name == TEST_USER_NAME

    def test_user_suspension_removes_rolebinding(self, k8s_clients, test_user):
        """
        Tests that setting `suspended: true` on a DevServerUser removes the RoleBinding.
        """
        custom_objects_api = k8s_clients["custom_objects_api"]
        rbac_v1_api = k8s_clients["rbac_v1"]
        user_namespace = test_user["namespace"]

        # Suspend the user
        custom_objects_api.patch_cluster_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            plural=CRD_PLURAL_DEVSERVERUSER,
            name=test_user["name"],
            body={"spec": {"suspended": True}},
        )

        # Verify RoleBinding is deleted
        for _ in range(10):
            try:
                rbac_v1_api.read_namespaced_role_binding(name="devserver-user-binding", namespace=user_namespace)
                time.sleep(1)
            except client.ApiException as e:
                if e.status == 404:
                    break
                else:
                    raise
        else:
            pytest.fail("RoleBinding was not deleted after suspension.")
