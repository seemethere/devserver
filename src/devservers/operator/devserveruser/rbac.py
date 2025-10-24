"""RBAC provisioning for DevServerUser resources."""

from __future__ import annotations
from typing import Dict
from ...crds.const import CRD_GROUP, CRD_PLURAL_DEVSERVER


DEFAULT_ROLE_RULES = [
    # Allow full management of DevServer resources
    {
        "apiGroups": [CRD_GROUP],
        "resources": [CRD_PLURAL_DEVSERVER],
        "verbs": ["get", "list", "watch", "create", "delete"],
    },
    # Allow viewing and debugging of core workload resources
    {
        "apiGroups": [""],
        "resources": ["pods"],
        "verbs": ["get", "list", "watch"],
    },
    # Allow port-forwarding (requires 'get' on pods) and exec
    {
        "apiGroups": [""],
        "resources": ["pods/portforward"],
        "verbs": ["get", "create"],
    },
    {
        "apiGroups": [""],
        "resources": ["pods/exec"],
        "verbs": ["create"],
    },
]


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
