import yaml
import pathlib
from devservers.crds.const import CRD_GROUP, CRD_PLURAL_DEVSERVER, CRD_PLURAL_DEVSERVERFLAVOR


# Path to the CRD directory
CRD_DIR = pathlib.Path(__file__).parent.parent / "crds"


def test_devserver_crd_loads():
    """
    Tests that the DevServer CRD file can be loaded and parsed as YAML.
    """
    crd_file = CRD_DIR / "devserver.io_devservers.yaml"
    assert crd_file.exists(), "DevServer CRD file not found."

    with open(crd_file, "r") as f:
        crd = yaml.safe_load(f)

    assert crd is not None, "Failed to parse DevServer CRD YAML."
    assert crd["kind"] == "CustomResourceDefinition"
    assert crd["metadata"]["name"] == f"{CRD_PLURAL_DEVSERVER}.{CRD_GROUP}"
    assert "DevServer" in crd["spec"]["names"]["kind"]


def test_devserverflavor_crd_loads():
    """
    Tests that the DevServerFlavor CRD file can be loaded and parsed as YAML.
    """
    crd_file = CRD_DIR / "devserver.io_devserverflavors.yaml"
    assert crd_file.exists(), "DevServerFlavor CRD file not found."

    with open(crd_file, "r") as f:
        crd = yaml.safe_load(f)

    assert crd is not None, "Failed to parse DevServerFlavor CRD YAML."
    assert crd["kind"] == "CustomResourceDefinition"
    assert crd["metadata"]["name"] == f"{CRD_PLURAL_DEVSERVERFLAVOR}.{CRD_GROUP}"
    assert "DevServerFlavor" in crd["spec"]["names"]["kind"]
    assert "Cluster" in crd["spec"]["scope"]
