"""Reconciliation logic for DevServerUser resources."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, cast

from kubernetes import client
from kubernetes.client import ApiException

from devserver.utils.users import compute_user_namespace
from ...crds.const import CRD_GROUP

from .rbac import build_default_role_body, build_default_rolebinding_body


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

    async def reconcile(self, logger: logging.Logger) -> ReconcileResult:
        namespace_name = await self._ensure_namespace(logger)
        await self._ensure_service_account(namespace_name, logger)
        await self._ensure_default_role(namespace_name, logger)
        await self._ensure_default_rolebinding(namespace_name, logger)
        return ReconcileResult(namespace=namespace_name, message="Namespace and RBAC ensured")

    async def cleanup(self, logger: logging.Logger) -> None:
        namespace_name = compute_user_namespace(self.username)
        label_selector = f"{CRD_GROUP}/user={self.username}"
        await self._delete_service_account(namespace_name, logger)
        await self._delete_role(namespace_name, logger)
        await self._delete_rolebinding(namespace_name, logger)
        # Namespace deletion is left to cluster admins; we only remove RBAC artifacts
        logger.info("Skipped namespace deletion for user '%s' (label selector=%s)", self.username, label_selector)

    def _desired_namespace_name(self) -> str:
        return compute_user_namespace(self.username)

    async def _ensure_namespace(self, logger: logging.Logger) -> str:
        namespace_name = self._desired_namespace_name()
        body = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels={
                    f"{CRD_GROUP}/user": self.username,
                    f"{CRD_GROUP}/managed": "true",
                },
            )
        )
        try:
            await asyncio.to_thread(self.core_v1.create_namespace, body=body)
            logger.info("Namespace '%s' created for user '%s'", namespace_name, self.username)
        except ApiException as exc:
            if exc.status != 409:
                raise
            logger.info("Namespace '%s' already exists", namespace_name)
        return namespace_name

    async def _ensure_service_account(self, namespace: str, logger: logging.Logger) -> None:
        """Ensures a ServiceAccount for the user exists."""
        sa_name = f"{self.username}-sa"
        body = client.V1ServiceAccount(
            metadata=client.V1ObjectMeta(name=sa_name, namespace=namespace)
        )
        try:
            await asyncio.to_thread(
                self.core_v1.create_namespaced_service_account,
                namespace=namespace,
                body=body,
            )
            logger.info("ServiceAccount '%s' created for user '%s'", sa_name, self.username)
        except ApiException as exc:
            if exc.status != 409:
                raise
            logger.info("ServiceAccount '%s' already exists.", sa_name)

    async def _delete_service_account(self, namespace: str, logger: logging.Logger) -> None:
        """Deletes the ServiceAccount for the user."""
        sa_name = f"{self.username}-sa"
        try:
            await asyncio.to_thread(
                self.core_v1.delete_namespaced_service_account,
                name=sa_name,
                namespace=namespace,
            )
            logger.info("Deleted ServiceAccount '%s' for namespace '%s'", sa_name, namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
            logger.info("ServiceAccount '%s' absent for namespace '%s'", sa_name, namespace)

    async def _ensure_default_role(self, namespace: str, logger: logging.Logger) -> None:
        role_body = build_default_role_body(namespace, self.username)
        try:
            metadata = cast(Dict[str, object], role_body["metadata"])
            role_name = cast(str, metadata["name"])
        except KeyError:
            raise ValueError("Role body is missing expected metadata")

        try:
            await asyncio.to_thread(
                self.rbac_v1.read_namespaced_role, name=role_name, namespace=namespace
            )
            await asyncio.to_thread(
                self.rbac_v1.patch_namespaced_role,
                name=role_name,
                namespace=namespace,
                body=role_body,
            )
            logger.info("Default Role patched for user '%s'", self.username)
        except ApiException as exc:
            if exc.status == 404:
                await asyncio.to_thread(
                    self.rbac_v1.create_namespaced_role,
                    namespace=namespace,
                    body=role_body,
                )
                logger.info("Default Role created for user '%s'", self.username)
            else:
                raise

    async def _ensure_default_rolebinding(self, namespace: str, logger: logging.Logger) -> None:
        rolebinding_body = build_default_rolebinding_body(namespace, self.username)
        try:
            metadata = cast(Dict[str, object], rolebinding_body["metadata"])
            rb_name = cast(str, metadata["name"])
        except KeyError:
            raise ValueError("RoleBinding body is missing expected metadata")

        try:
            await asyncio.to_thread(
                self.rbac_v1.read_namespaced_role_binding,
                name=rb_name,
                namespace=namespace,
            )
            await asyncio.to_thread(
                self.rbac_v1.patch_namespaced_role_binding,
                name=rb_name,
                namespace=namespace,
                body=rolebinding_body,
            )
            logger.info("Default RoleBinding patched for user '%s'", self.username)
        except ApiException as exc:
            if exc.status == 404:
                await asyncio.to_thread(
                    self.rbac_v1.create_namespaced_role_binding,
                    namespace=namespace,
                    body=rolebinding_body,
                )
                logger.info("Default RoleBinding created for user '%s'", self.username)
            else:
                raise

    async def _delete_role(self, namespace: str, logger: logging.Logger) -> None:
        try:
            await asyncio.to_thread(
                self.rbac_v1.delete_namespaced_role,
                name="devserver-user",
                namespace=namespace,
            )
            logger.info("Deleted Role for namespace '%s'", namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
            logger.info("Role absent for namespace '%s'", namespace)

    async def _delete_rolebinding(self, namespace: str, logger: logging.Logger) -> None:
        try:
            await asyncio.to_thread(
                self.rbac_v1.delete_namespaced_role_binding,
                name="devserver-user",
                namespace=namespace,
            )
            logger.info("Deleted RoleBinding for namespace '%s'", namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
            logger.info("RoleBinding absent for namespace '%s'", namespace)
