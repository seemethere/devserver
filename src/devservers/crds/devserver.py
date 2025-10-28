from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
from kubernetes import client
from .base import BaseCustomResource, ObjectMeta
from .const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVER


@dataclass
class PersistentHomeSpec:
    """A dataclass to represent the persistentHome field in the DevServer spec."""

    enabled: bool
    size: str = "10Gi"


@dataclass
class DevServer(BaseCustomResource):
    group = CRD_GROUP
    version = CRD_VERSION
    plural = CRD_PLURAL_DEVSERVER
    namespaced = True

    metadata: ObjectMeta
    spec: Dict[str, Any]
    status: Dict[str, Any] = field(default_factory=dict, init=False)

    def __init__(
        self,
        metadata: ObjectMeta,
        spec: Dict[str, Any],
        status: Optional[Dict[str, Any]] = None,
        api: Optional[client.CustomObjectsApi] = None,
    ) -> None:
        super().__init__(api)
        self.metadata = metadata
        self.spec = spec
        self.status = status or {}

    @property
    def persistent_home(self) -> Optional[PersistentHomeSpec]:
        """
        Provides typed access to the persistentHome spec.
        Returns:
            A PersistentHomeSpec object if persistentHome is defined in the spec,
            otherwise None.
        """
        persistent_home_data = self.spec.get("persistentHome")
        if persistent_home_data:
            return PersistentHomeSpec(**persistent_home_data)
        return None

    @persistent_home.setter
    def persistent_home(self, value: Optional[PersistentHomeSpec]) -> None:
        """
        Sets the persistentHome spec from a PersistentHomeSpec object.
        """
        if value:
            self.spec["persistentHome"] = asdict(value)
        elif "persistentHome" in self.spec:
            del self.spec["persistentHome"]
