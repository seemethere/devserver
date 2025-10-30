#!/usr/bin/env python3
"""
Development script to bootstrap the operator in the cluster for remote development.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from kubernetes import client, config

def get_current_context():
    """Get the current kubeconfig context."""
    try:
        contexts, active_context = config.list_kube_config_contexts()
        if not contexts:
            print("❌ No contexts found in kubeconfig.")
            sys.exit(1)
        return active_context['name']
    except Exception as e:
        print(f"❌ Failed to get current kubeconfig context: {e}")
        sys.exit(1)

def get_current_namespace(context):
    """Get the default namespace for the current context."""
    try:
        contexts, active_context = config.list_kube_config_contexts()
        if 'namespace' in active_context['context']:
            return active_context['context']['namespace']
        return 'default'
    except Exception as e:
        print(f"❌ Failed to get namespace for context '{context}': {e}")
        return 'default'

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bootstrap the DevServer operator for remote development"
    )
    parser.add_argument(
        "--context",
        help="The kubectl context to use.",
    )
    parser.add_argument(
        "--namespace",
        "-n",
        help="Namespace to deploy to (defaults to current context's namespace or 'default').",
    )
    args = parser.parse_args()

    context = args.context or get_current_context()
    namespace = args.namespace or get_current_namespace(context)

    print(f"Targeting context: {context}, namespace: {namespace}")

    try:
        config.load_kube_config(context=context)
    except Exception as e:
        print(f"❌ Failed to load kubeconfig for context '{context}': {e}")
        sys.exit(1)

    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    rbac_v1 = client.RbacAuthorizationV1Api()

    ensure_namespace(core_v1, namespace)
    ensure_rbac(rbac_v1, namespace)
    ensure_deployment(apps_v1, namespace)

    pod_name = get_operator_pod(core_v1, namespace)
    if not pod_name:
        print("❌ Could not find operator pod.")
        sys.exit(1)

    sync_files(namespace, pod_name)
    restart_operator(namespace, pod_name)
    generate_devctl_wrapper(namespace)

    print("✅ Bootstrap complete. Operator is running and synced.")

def ensure_namespace(api: client.CoreV1Api, namespace: str):
    """Ensure the namespace exists."""
    try:
        api.read_namespace(name=namespace)
        print(f"✅ Namespace '{namespace}' already exists.")
    except client.ApiException as e:
        if e.status == 404:
            print(f"🔧 Creating namespace '{namespace}'...")
            api.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))
            print(f"✅ Namespace '{namespace}' created.")
        else:
            raise

def ensure_rbac(api: client.RbacAuthorizationV1Api, namespace: str):
    # Simplified RBAC for dev purposes.
    # In a real scenario, this would be more granular.
    service_account_name = "devserver-operator-dev"
    role_name = "devserver-operator-dev-role"
    role_binding_name = "devserver-operator-dev-rb"

    # Service Account
    try:
        api.read_namespaced_service_account(name=service_account_name, namespace=namespace)
    except client.ApiException as e:
        if e.status == 404:
            sa = client.V1ServiceAccount(metadata=client.V1ObjectMeta(name=service_account_name))
            api.create_namespaced_service_account(namespace=namespace, body=sa)

    # Role
    try:
        api.read_namespaced_role(name=role_name, namespace=namespace)
    except client.ApiException as e:
        if e.status == 404:
            role = client.V1Role(
                metadata=client.V1ObjectMeta(name=role_name),
                rules=[client.V1PolicyRule(api_groups=["*"], resources=["*"], verbs=["*"])]
            )
            api.create_namespaced_role(namespace=namespace, body=role)

    # Role Binding
    try:
        api.read_namespaced_role_binding(name=role_binding_name, namespace=namespace)
    except client.ApiException as e:
        if e.status == 404:
            rb = client.V1RoleBinding(
                metadata=client.V1ObjectMeta(name=role_binding_name),
                subjects=[client.V1Subject(kind="ServiceAccount", name=service_account_name, namespace=namespace)],
                role_ref=client.V1RoleRef(kind="Role", name=role_name, api_group="rbac.authorization.k8s.io")
            )
            api.create_namespaced_role_binding(namespace=namespace, body=rb)

def ensure_deployment(api: client.AppsV1Api, namespace: str):
    deployment_name = "devserver-operator-dev"
    image = "ghcr.io/seemethere/devservers:main" # From .github/workflows/docker-build.yml

    container = client.V1Container(
        name="operator",
        image=image,
        image_pull_policy="Always",
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "devserver-operator-dev"}),
        spec=client.V1PodSpec(
            containers=[container],
            service_account_name="devserver-operator-dev"
        )
    )

    spec = client.V1DeploymentSpec(
        replicas=1,
        template=template,
        selector={'matchLabels': {"app": "devserver-operator-dev"}}
    )

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=deployment_name),
        spec=spec,
    )

    try:
        api.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        print(f"🔧 Updating Deployment '{deployment_name}'...")
        api.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=deployment)
        print(f"✅ Deployment '{deployment_name}' updated.")
    except client.ApiException as e:
        if e.status == 404:
            print(f"🔧 Creating Deployment '{deployment_name}'...")
            api.create_namespaced_deployment(namespace=namespace, body=deployment)
            print(f"✅ Deployment '{deployment_name}' created.")
        else:
            raise

def get_operator_pod(api: client.CoreV1Api, namespace: str) -> str:
    print("🔎 Finding operator pod...")
    for i in range(30): # Wait up to 30 seconds
        pods = api.list_namespaced_pod(namespace, label_selector="app=devserver-operator-dev")
        if pods.items and pods.items[0].status.phase == "Running":
            pod_name = pods.items[0].metadata.name
            print(f"✅ Found running pod: {pod_name}")
            return pod_name
        time.sleep(1)
    return ""

def sync_files(namespace: str, pod_name: str):
    print("🔄 Syncing files to pod...")
    # This assumes `kubectl rsync` plugin is installed.
    # We sync the entire repo, excluding .git and other ignored files by default.
    # Adjust exclude list as needed.
    source_path = Path(__file__).parent.parent.resolve()
    dest_path = f"{pod_name}:/app"
    cmd = [
        "kubectl", "rsync",
        "--namespace", namespace,
        f"{source_path}/",
        dest_path,
        "--exclude=.git",
        "--exclude=.idea",
        "--exclude=.vscode",
        "--exclude=__pycache__",
        "--exclude=.venv"
    ]
    subprocess.run(cmd, check=True)
    print("✅ Files synced.")

def restart_operator(namespace: str, pod_name: str):
    print("🔄 Restarting operator...")
    cmd = ["kubectl", "exec", "-n", namespace, pod_name, "--", "kill", "-HUP", "1"]
    subprocess.run(cmd, check=True)
    print("✅ Operator restarted.")

def generate_devctl_wrapper(namespace: str):
    """Generates a devctl wrapper script."""
    devctl_script_content = f"""#!/bin/bash
# This is an auto-generated script from 'make dev-bootstrap'
# It's a wrapper around 'uv run python -m devservers.cli.main' with the correct namespace.

ARGS=("$@")
NAMESPACE_FLAG_SET=false

# Check if --namespace or -n is already in the arguments
for arg in "${{ARGS[@]}}"; do
    if [[ "$arg" == "--namespace" || "$arg" == "-n" ]]; then
        NAMESPACE_FLAG_SET=true
        break
    fi
done

# If namespace flag is not set, add it
if [ "$NAMESPACE_FLAG_SET" = false ]; then
    uv run python -m devservers.cli.main --namespace {namespace} "$@"
else
    uv run python -m devservers.cli.main "$@"
fi
"""
    devctl_path = Path(__file__).parent.parent / "devctl"
    devctl_path.write_text(devctl_script_content)
    devctl_path.chmod(0o755)
    print(f"✅ Generated './devctl' wrapper for namespace '{namespace}'.")

if __name__ == "__main__":
    main()
