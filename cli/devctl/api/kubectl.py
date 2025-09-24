"""Kubectl wrapper utilities."""

import subprocess
from typing import Dict, List, Optional


def run_kubectl(*args, namespace=None, capture_output=True, timeout=10) -> subprocess.CompletedProcess:
    """Run kubectl command with proper error handling."""
    cmd = ["kubectl"]
    if namespace:
        cmd.extend(["-n", namespace])
    cmd.extend(args)
    
    try:
        return subprocess.run(cmd, capture_output=capture_output, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Exception("Command timed out")


def test_kubernetes_connectivity(namespace: str, verbose: bool = False) -> str:
    """Test basic Kubernetes connectivity."""
    try:
        result = run_kubectl("get", "pods", namespace=namespace)
        if result.returncode == 0:
            return "Connected ✓ (Secure)"
        else:
            # Try auth check if pods fail
            auth_result = run_kubectl("auth", "can-i", "get", "pods", namespace=namespace)
            if auth_result.returncode == 0 and 'yes' in auth_result.stdout.lower():
                return "Connected ✓ (Auth OK)"
            else:
                return "Limited Access ⚠"
    except Exception as e:
        return f"Error: {e}"


def test_devserver_access(namespace: str) -> str:
    """Test DevServer CRD access."""
    try:
        # Test namespace-scoped DevServer access
        devserver_result = run_kubectl("auth", "can-i", "get", "devservers", namespace=namespace)
        # Test cluster-scoped DevServerFlavor access
        flavor_result = run_kubectl("auth", "can-i", "get", "devserverflavors")
        
        devserver_ok = devserver_result.returncode == 0 and 'yes' in devserver_result.stdout.lower()
        flavor_ok = flavor_result.returncode == 0 and 'yes' in flavor_result.stdout.lower()
        
        if devserver_ok and flavor_ok:
            return "Available ✓"
        elif devserver_ok:
            return "DevServers ✓, Flavors ⚠"
        elif flavor_ok:
            return "Flavors ✓, DevServers ⚠"
        else:
            return "No Access ⚠"
    except Exception as e:
        return f"Error: {e}"


def check_permissions(resource: str, verb: str, namespace: str) -> bool:
    """Check if user has permission for a specific operation."""
    try:
        result = run_kubectl("auth", "can-i", verb, resource, namespace=namespace)
        return result.returncode == 0 and 'yes' in result.stdout.lower()
    except Exception:
        return False
