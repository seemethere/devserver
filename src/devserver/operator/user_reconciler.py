import kopf
import kubernetes

from . import utils

from typing import Any, Dict
import logging

USER_NAMESPACE_PREFIX = "devserver-user-"
FINALIZER = "devserver.io/user-finalizer"

def get_user_namespace(username: str) -> str:
    """Returns the namespace for a given user."""
    return f"{USER_NAMESPACE_PREFIX}{username}"


def reconcile_user(spec: Dict[str, Any], name: str, uid: str, logger: logging.Logger, body: Dict[str, Any], **kwargs: Any) -> None:
    """
    Reconciles a User resource.

    This function ensures that a namespace and the necessary RBAC roles
    and rolebindings exist for a given user. It also handles user suspension.
    """
    username = spec.get('username')
    suspended = spec.get('suspended', False)

    if not username:
        raise kopf.PermanentError("Username must be set in spec")

    api = kubernetes.client.CoreV1Api()
    rbac_api = kubernetes.client.RbacAuthorizationV1Api()

    namespace_name = get_user_namespace(username)

    # Ensure namespace exists
    try:
        api.read_namespace(name=namespace_name)
    except kubernetes.client.ApiException as e:
        if e.status == 404:
            logger.info(f"Creating namespace {namespace_name}")
            api.create_namespace(body=kubernetes.client.V1Namespace(metadata=kubernetes.client.V1ObjectMeta(name=namespace_name)))
        else:
            raise

    # Define Role
    role = {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "Role",
        "metadata": {"name": "devserver-user-role"},
        "rules": [
            {
                "apiGroups": ["devserver.io"],
                "resources": ["devservers"],
                "verbs": ["create", "delete", "get", "list", "patch", "update"],
            },
            {
                "apiGroups": [""],
                "resources": ["pods/portforward"],
                "verbs": ["create"],
            },
        ],
    }

    # Define RoleBinding
    role_binding = {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "RoleBinding",
        "metadata": {"name": "devserver-user-binding"},
        "subjects": [{"kind": "User", "name": username, "apiGroup": "rbac.authorization.k8s.io"}],
        "roleRef": {
            "kind": "Role",
            "name": "devserver-user-role",
            "apiGroup": "rbac.authorization.k8s.io",
        },
    }

    # Create or update Role and RoleBinding
    try:
        rbac_api.read_namespaced_role(name="devserver-user-role", namespace=namespace_name)
        rbac_api.replace_namespaced_role(name="devserver-user-role", namespace=namespace_name, body=role)
    except kubernetes.client.ApiException as e:
        if e.status == 404:
            rbac_api.create_namespaced_role(namespace=namespace_name, body=role)
        else:
            raise

    try:
        existing_rb = rbac_api.read_namespaced_role_binding(name="devserver-user-binding", namespace=namespace_name)
        if not suspended:
             if existing_rb.subjects[0].name != username:
                rbac_api.replace_namespaced_role_binding(name="devserver-user-binding", namespace=namespace_name, body=role_binding)
        else:
             rbac_api.delete_namespaced_role_binding(name="devserver-user-binding", namespace=namespace_name)

    except kubernetes.client.ApiException as e:
        if e.status == 404:
            if not suspended:
                rbac_api.create_namespaced_role_binding(namespace=namespace_name, body=role_binding)
        else:
            raise

    # Add finalizer if not present
    if FINALIZER not in body['metadata'].get('finalizers', []):
        utils.add_finalizer(name, FINALIZER, 'devserverusers')


def on_user_delete(spec: Dict[str, Any], name: str, logger: logging.Logger, body: Dict[str, Any], **kwargs: Any) -> None:
    """
    Handles the deletion of a User resource.

    This function deletes the user's namespace, which in turn deletes all
    resources within that namespace. It then removes the finalizer from the
    User resource, allowing it to be deleted.
    """
    username = spec.get('username')
    if not username:
        return  # Nothing to do if username is not set

    namespace_name = get_user_namespace(username)
    api = kubernetes.client.CoreV1Api()

    try:
        api.delete_namespace(name=namespace_name)
        logger.info(f"Namespace {namespace_name} deleted.")
    except kubernetes.client.ApiException as e:
        if e.status != 404:
            raise

    # Remove finalizer if present
    if FINALIZER in body['metadata'].get('finalizers', []):
        utils.remove_finalizer(name, FINALIZER, 'devserverusers')
