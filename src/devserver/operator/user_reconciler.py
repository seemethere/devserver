"""Reconciliation logic for DevServerUser resources."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

from kubernetes import client
from kubernetes.client import ApiException

from devserver.utils.users import compute_user_namespace

from .utils import build_default_role_body, build_default_rolebinding_body


@dataclass
class ReconcileResult:
    namespace: str
    message: str


class DevServerUserReconciler:
    """Handles provisioning namespaces and RBAC for DevServerUser."""

    def __init__(self, spec: Dict[str, object], metadata: Dict[str, object]) -> None:
        self.metadata = metadata
        self.username = str(spec.get("username"))
        self.core_v1 = client.CoreV1Api()
        self.rbac_v1 = client.RbacAuthorizationV1Api()

    def reconcile(self, logger: logging.Logger) -> ReconcileResult:
        namespace_name = self._ensure_namespace(logger)
        self._ensure_service_account(namespace_name, logger)
        self._ensure_default_role(namespace_name, logger)
        self._ensure_default_rolebinding(namespace_name, logger)
        return ReconcileResult(namespace=namespace_name, message="Namespace and RBAC ensured")

    def cleanup(self, logger: logging.Logger) -> None:
        namespace_name = compute_user_namespace(self.username)
        label_selector = f"devserver.io/user={self.username}"
        self._delete_service_account(namespace_name, logger)
        self._delete_role(namespace_name, logger)
        self._delete_rolebinding(namespace_name, logger)
        # Namespace deletion is left to cluster admins; we only remove RBAC artifacts
        logger.info("Skipped namespace deletion for user '%s' (label selector=%s)", self.username, label_selector)

    def _desired_namespace_name(self) -> str:
        return compute_user_namespace(self.username)

    def _ensure_namespace(self, logger: logging.Logger) -> str:
        namespace_name = self._desired_namespace_name()
        body = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels={
                    "devserver.io/user": self.username,
                    "devserver.io/managed": "true",
                },
            )
        )
        try:
            self.core_v1.create_namespace(body=body)
            logger.info("Namespace '%s' created for user '%s'", namespace_name, self.username)
        except ApiException as exc:
            if exc.status != 409:
                raise
            logger.info("Namespace '%s' already exists", namespace_name)
        return namespace_name

    def _ensure_service_account(self, namespace: str, logger: logging.Logger) -> None:
        """Ensures a ServiceAccount for the user exists."""
        sa_name = f"{self.username}-sa"
        body = client.V1ServiceAccount(
            metadata=client.V1ObjectMeta(name=sa_name, namespace=namespace)
        )
        try:
            self.core_v1.create_namespaced_service_account(namespace=namespace, body=body)
            logger.info("ServiceAccount '%s' created for user '%s'", sa_name, self.username)
        except ApiException as exc:
            if exc.status != 409:
                raise
            logger.info("ServiceAccount '%s' already exists.", sa_name)

    def _delete_service_account(self, namespace: str, logger: logging.Logger) -> None:
        """Deletes the ServiceAccount for the user."""
        sa_name = f"{self.username}-sa"
        try:
            self.core_v1.delete_namespaced_service_account(name=sa_name, namespace=namespace)
            logger.info("Deleted ServiceAccount '%s' for namespace '%s'", sa_name, namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
            logger.info("ServiceAccount '%s' absent for namespace '%s'", sa_name, namespace)

    def _ensure_default_role(self, namespace: str, logger: logging.Logger) -> None:
        role_body = build_default_role_body(namespace, self.username)
        try:
            self.rbac_v1.create_namespaced_role(namespace=namespace, body=role_body)
            logger.info("Default Role ensured for user '%s'", self.username)
        except ApiException as exc:
            if exc.status != 409:
                raise
            logger.info("Role already exists for namespace '%s'", namespace)

    def _ensure_default_rolebinding(self, namespace: str, logger: logging.Logger) -> None:
        rolebinding_body = build_default_rolebinding_body(namespace, self.username)
        try:
            self.rbac_v1.create_namespaced_role_binding(namespace=namespace, body=rolebinding_body)
            logger.info("Default RoleBinding ensured for user '%s'", self.username)
        except ApiException as exc:
            if exc.status != 409:
                raise
            logger.info("RoleBinding already exists for namespace '%s'", namespace)

    def _delete_role(self, namespace: str, logger: logging.Logger) -> None:
        try:
            self.rbac_v1.delete_namespaced_role(name="devserver-user", namespace=namespace)
            logger.info("Deleted Role for namespace '%s'", namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
            logger.info("Role absent for namespace '%s'", namespace)

    def _delete_rolebinding(self, namespace: str, logger: logging.Logger) -> None:
        try:
            self.rbac_v1.delete_namespaced_role_binding(name="devserver-user", namespace=namespace)
            logger.info("Deleted RoleBinding for namespace '%s'", namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
            logger.info("RoleBinding absent for namespace '%s'", namespace)
