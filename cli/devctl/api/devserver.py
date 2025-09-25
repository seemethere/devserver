"""DevServer API operations."""

import json
import subprocess
import time
from typing import Dict, List, Optional

from .kubectl import run_kubectl


def list_devservers(namespace: str) -> List[Dict]:
    """List DevServers in user namespace."""
    try:
        result = run_kubectl("get", "devservers", "-o", "json", namespace=namespace)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('items', [])
    except Exception:
        pass
    return []


def list_flavors() -> List[Dict]:
    """List cluster-scoped DevServerFlavors."""
    try:
        result = run_kubectl("get", "devserverflavors", "-o", "json")
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('items', [])
    except Exception:
        pass
    return []


def get_devserver(name: str, namespace: str) -> Optional[Dict]:
    """Get specific DevServer by name."""
    try:
        result = run_kubectl("get", "devserver", name, "-o", "json", namespace=namespace)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def create_devserver(name: str, spec: Dict, namespace: str) -> bool:
    """Create a new DevServer."""

    lifecycle = spec.get('lifecycle', {})
    lifecycle_yaml_parts = [
        f"    idleTimeout: {lifecycle.get('idleTimeout', 3600)}",
        f"    autoShutdown: {str(lifecycle.get('autoShutdown', True)).lower()}",
    ]
    if 'timeToLive' in lifecycle:
        lifecycle_yaml_parts.append(f"    timeToLive: {lifecycle['timeToLive']}")

    lifecycle_yaml = "\n".join(lifecycle_yaml_parts)

    devserver_yaml = f"""
apiVersion: apps.devservers.io/v1
kind: DevServer
metadata:
  name: {name}
  namespace: {namespace}
spec:
  owner: {spec['owner']}
  flavor: {spec['flavor']}
  image: {spec.get('image', 'ubuntu:22.04')}
  mode: {spec.get('mode', 'standalone')}
  persistentHomeSize: {spec.get('persistentHomeSize', '10Gi')}
  enableSSH: {str(spec.get('enableSSH', True)).lower()}
  lifecycle:
{lifecycle_yaml}
"""
    
    try:
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=devserver_yaml,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def patch_devserver(name: str, namespace: str, patch: Dict) -> bool:
    """Patch a DevServer resource."""
    try:
        patch_json = json.dumps(patch)
        result = run_kubectl(
            "patch", "devserver", name,
            "--type", "merge",
            "-p", patch_json,
            namespace=namespace
        )
        return result.returncode == 0
    except Exception:
        return False


def delete_devserver(name: str, namespace: str) -> bool:
    """Delete a DevServer."""
    try:
        result = run_kubectl("delete", "devserver", name, namespace=namespace)
        return result.returncode == 0
    except Exception:
        return False


def wait_for_devserver_ready(name: str, namespace: str, timeout: int = 120) -> bool:
    """Wait for DevServer to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        devserver = get_devserver(name, namespace)
        if devserver and devserver.get('status', {}).get('ready'):
            return True
        time.sleep(2)
    return False


def get_devserver_resources(name: str, namespace: str) -> str:
    """Get related resources for a DevServer."""
    try:
        result = run_kubectl("get", "pods,pvc,svc,deployment", "-l", f"app=devserver,devserver={name}", namespace=namespace)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "No related resources found"


def flavor_exists(flavor_name: str) -> bool:
    """Check if a DevServerFlavor exists."""
    flavors = list_flavors()
    return any(f['metadata']['name'] == flavor_name for f in flavors)
