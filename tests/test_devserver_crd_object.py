from unittest.mock import MagicMock

from devserver.crds import DevServer
from devserver.crds.const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVER


def test_devserver_get():
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = {
        "metadata": {"name": "test-server", "namespace": "test-ns"},
        "spec": {"flavor": "cpu-small", "image": "ubuntu:20.04"},
        "status": {"phase": "Ready"},
    }

    server = DevServer.get("test-server", namespace="test-ns", api=api)

    assert isinstance(server, DevServer)
    assert server.metadata.name == "test-server"
    assert server.metadata.namespace == "test-ns"
    assert server.spec["flavor"] == "cpu-small"
    assert server.status["phase"] == "Ready"

    api.get_namespaced_custom_object.assert_called_once_with(
        group=CRD_GROUP,
        version=CRD_VERSION,
        plural=CRD_PLURAL_DEVSERVER,
        namespace="test-ns",
        name="test-server",
    )
