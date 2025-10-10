from devserver.operator.resources.statefulset import build_statefulset
from devserver.operator.user_reconciler import DevServerUserReconciler
from unittest.mock import MagicMock
from kubernetes.client.rest import ApiException

def test_build_statefulset_with_node_selector():
    name = "test-server"
    namespace = "test-ns"
    spec = {
        "ssh": {
            "publicKey": "ssh-rsa AAA..."
        }
    }
    flavor = {
        "spec": {
            "resources": {
                "requests": {"cpu": "1", "memory": "1Gi"},
                "limits": {"cpu": "2", "memory": "2Gi"},
            },
            "nodeSelector": {
                "disktype": "ssd",
                "team": "backend"
            }
        }
    }

    statefulset = build_statefulset(name, namespace, spec, flavor)

    assert "nodeSelector" in statefulset["spec"]["template"]["spec"]
    assert statefulset["spec"]["template"]["spec"]["nodeSelector"] == {
        "disktype": "ssd",
        "team": "backend"
    }

def test_build_statefulset_without_node_selector():
    name = "test-server"
    namespace = "test-ns"
    spec = {
        "ssh": {
            "publicKey": "ssh-rsa AAA..."
        }
    }
    flavor = {
        "spec": {
            "resources": {
                "requests": {"cpu": "1", "memory": "1Gi"},
                "limits": {"cpu": "2", "memory": "2Gi"},
            }
        }
    }

    statefulset = build_statefulset(name, namespace, spec, flavor)

    assert "nodeSelector" not in statefulset["spec"]["template"]["spec"]


def test_compute_user_namespace_default():
    spec = {"username": "alice"}
    reconciler = DevServerUserReconciler(spec=spec, metadata={})
    assert reconciler._desired_namespace_name() == "dev-alice"


def test_devserver_user_reconciler_creates_namespace(monkeypatch):
    spec = {"username": "bob"}
    reconciler = DevServerUserReconciler(spec=spec, metadata={})

    namespace_api = MagicMock()
    rbac_api = MagicMock()

    monkeypatch.setattr(reconciler, "core_v1", namespace_api)
    monkeypatch.setattr(reconciler, "rbac_v1", rbac_api)

    namespace_api.create_namespace.side_effect = ApiException(status=409)
    rbac_api.create_namespaced_role.side_effect = ApiException(status=409)
    rbac_api.create_namespaced_role_binding.side_effect = ApiException(status=409)

    logger = MagicMock()
    result = reconciler.reconcile(logger)

    assert result.namespace == "dev-bob"
    namespace_api.create_namespace.assert_called_once()
    rbac_api.create_namespaced_role.assert_called_once()
    rbac_api.create_namespaced_role_binding.assert_called_once()
