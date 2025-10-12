"""Utility functions for DevServer operator components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

DEFAULT_ROLE_RULES = [
    {
        "apiGroups": [""],
        "resources": [
            "pods",
            "services",
            "endpoints",
            "persistentvolumeclaims",
            "configmaps",
        ],
        "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"],
    },
    {
        "apiGroups": ["apps"],
        "resources": ["statefulsets", "deployments", "replicasets"],
        "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"],
    },
    {
        "apiGroups": ["devserver.io"],
        "resources": ["devservers"],
        "verbs": ["get", "list", "watch", "create", "delete"],
    },
]


@dataclass(frozen=True)
class DevServerUserSpec:
    """Subset of DevServerUser spec relevant for namespace and RBAC provisioning."""

    username: str
    @classmethod
    def from_spec(cls, spec: Dict[str, object]) -> "DevServerUserSpec":
        return cls(
            username=str(spec.get("username")),
        )


def build_default_role_body(namespace: str, username: str) -> Dict[str, object]:
    """Create a Role manifest granting standard devserver permissions."""

    role_name = "devserver-user"
    return {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "Role",
        "metadata": {"name": role_name, "namespace": namespace},
        "rules": DEFAULT_ROLE_RULES,
    }


def build_default_rolebinding_body(namespace: str, username: str) -> Dict[str, object]:
    """Create a RoleBinding manifest binding the user to the default role."""

    return {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "RoleBinding",
        "metadata": {"name": "devserver-user", "namespace": namespace},
        "subjects": [
            {"kind": "User", "name": username},
            {
                "kind": "ServiceAccount",
                "name": f"{username}-sa",
                "namespace": namespace,
            },
        ],
        "roleRef": {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "Role",
            "name": "devserver-user",
        },
    }
