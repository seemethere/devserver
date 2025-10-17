from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from kubernetes import client


@dataclass
class ObjectMeta:
    name: str
    namespace: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


class BaseCustomResource:
    group: str
    version: str
    plural: str
    namespaced: bool

    def __init__(self, api: Optional[client.CustomObjectsApi] = None) -> None:
        self.api = api or client.CustomObjectsApi()

    @classmethod
    def get(
        cls,
        name: str,
        *,
        namespace: Optional[str] = None,
        api: Optional[client.CustomObjectsApi] = None,
    ) -> "BaseCustomResource":
        
        api_instance = api or client.CustomObjectsApi()
        if cls.namespaced:
            if not namespace:
                raise ValueError("Namespace is required for namespaced resources")
            data = api_instance.get_namespaced_custom_object(
                group=cls.group,
                version=cls.version,
                namespace=namespace,
                plural=cls.plural,
                name=name,
            )
        else:
            if namespace:
                raise ValueError("Cluster-scoped resources must not receive a namespace")
            data = api_instance.get_cluster_custom_object(
                group=cls.group,
                version=cls.version,
                plural=cls.plural,
                name=name,
            )
        
        meta = ObjectMeta(**data["metadata"])
        return cls(metadata=meta, spec=data["spec"], status=data.get("status", {}), api=api)


    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": {
                "name": self.metadata.name,
                "namespace": self.metadata.namespace,
                "labels": self.metadata.labels or None,
                "annotations": self.metadata.annotations or None,
            },
            "spec": self.spec,
            "status": self.status or None,
        }