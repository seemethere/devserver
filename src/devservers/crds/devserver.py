from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from kubernetes import client
from .base import BaseCustomResource, ObjectMeta
from .const import CRD_GROUP, CRD_VERSION, CRD_PLURAL_DEVSERVER


@dataclass
class DevServer(BaseCustomResource):
    group = CRD_GROUP
    version = CRD_VERSION
    plural = CRD_PLURAL_DEVSERVER
    namespaced = True

    metadata: ObjectMeta
    spec: Dict[str, Any]
    status: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(
        self,
        metadata: ObjectMeta,
        spec: Dict[str, Any],
        status: Dict[str, Any] = field(default_factory=dict),
        api: Optional[client.CustomObjectsApi] = None,
    ) -> None:
        super().__init__(api)
        self.metadata = metadata
        self.spec = spec
        self.status = status