import pytest
import subprocess
import time
import re
from kubernetes import client, config

# --- Helper Functions ---

def run_command(command, check=True):
    """Executes a command and returns its output."""
    print(f"Executing: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, check=check)
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    return result

def get_bastion_pod_name():
    """Finds the bastion pod name."""
    command = [
        "kubectl", "get", "pods",
        "-n", "devserver-bastion",
        "-l", "app=bastion",
        "-o", "jsonpath={.items[0].metadata.name}"
    ]
    return run_command(command).stdout.strip()

def run_in_bastion(command_str):
    """Runs a devctl command inside the bastion pod."""
    pod_name = get_bastion_pod_name()
    # Set USER=testuser and source the profile to mimic a real user login
    command_to_exec = f"USER=testuser bash -c 'source /etc/profile && {command_str}'"
    full_command = [
        "kubectl", "exec", "-n", "devserver-bastion", pod_name,
        "--", "bash", "-c", command_to_exec
    ]
    return run_command(full_command, check=False) # check=False to handle expected errors

# --- Pytest Fixtures ---

@pytest.fixture(scope="session")
def platform_deployment():
    """Deploys the operator and bastion. Assumes a fresh cluster."""
    print("Deploying DevServer platform...")
    # These scripts are idempotent and will clean up before deploying.
    run_command(["make", "deploy-operator"])
    run_command(["make", "deploy-bastion"])
    
    # Wait for bastion to be ready
    print("Waiting for bastion pod to be running...")
    run_command([
        "kubectl", "wait", "--for=condition=Ready", "pod",
        "-n", "devserver-bastion", "-l", "app=bastion", "--timeout=300s"
    ])
    
    # Wait for operator to be ready
    print("Waiting for operator pod to be running...")
    run_command([
        "kubectl", "wait", "--for=condition=Ready", "pod",
        "-n", "devserver-operator-system", "-l", "control-plane=controller-manager", "--timeout=300s"
    ])
    
    print("Platform deployed successfully.")
    yield
    # No teardown, assume ephemeral cluster for CI/manual cleanup

@pytest.fixture(scope="module")
def k8s_api():
    """Provides a Kubernetes API client."""
    config.load_kube_config()
    return client.CoreV1Api()

@pytest.fixture(scope="module")
def k8s_custom_objects_api():
    """Provides a Kubernetes Custom Objects API client."""
    config.load_kube_config()
    return client.CustomObjectsApi()

# --- Test Functions ---

@pytest.mark.usefixtures("platform_deployment")
class TestDevServerLifecycle:
    
    def test_auto_expiration(self, k8s_custom_objects_api):
        """Verify that a DevServer is deleted after its timeToLive expires."""
        server_name = "test-expire"
        username = "testuser"
        namespace = f"dev-{username}"
        ttl_seconds = 7
        
        # Cleanup any previous runs
        run_in_bastion(f"devctl delete {server_name} --force")
        time.sleep(2)

        # Create a DevServer with a short time-to-live
        print(f"Creating DevServer '{server_name}' with {ttl_seconds}s TTL...")
        result = run_in_bastion(f"devctl create {server_name} --flavor cpu-small --time {ttl_seconds}s --wait")
        assert result.returncode == 0, f"Failed to create devserver: {result.stderr}"

        # Verify it was created
        devserver = k8s_custom_objects_api.get_namespaced_custom_object(
            group="apps.devservers.io",
            version="v1",
            name=server_name,
            namespace=namespace,
            plural="devservers",
        )
        assert devserver is not None
        assert devserver['spec']['lifecycle']['timeToLive'] == f"{ttl_seconds}s"
        
        # Wait for expiration
        print(f"Waiting {ttl_seconds + 5} seconds for expiration...")
        time.sleep(ttl_seconds + 5)
        
        # Verify it was deleted
        try:
            k8s_custom_objects_api.get_namespaced_custom_object(
                group="apps.devservers.io",
                version="v1",
                name=server_name,
                namespace=namespace,
                plural="devservers",
            )
            pytest.fail(f"DevServer '{server_name}' was not deleted after expiration.")
        except client.ApiException as e:
            assert e.status == 404

    def test_extend_expiration(self, k8s_custom_objects_api):
        """Verify that the expiration time of a DevServer can be extended."""
        server_name = "test-extend"
        username = "testuser"
        namespace = f"dev-{username}"
        
        run_in_bastion(f"devctl delete {server_name} --force")
        time.sleep(2)

        # Create with a short TTL
        result = run_in_bastion(f"devctl create {server_name} --flavor cpu-small --time 20s --wait")
        assert result.returncode == 0
        
        # Get original expiration time
        devserver = k8s_custom_objects_api.get_namespaced_custom_object(
            group="apps.devservers.io", version="v1", name=server_name,
            namespace=namespace, plural="devservers"
        )
        original_expiration = devserver['spec']['lifecycle']['expirationTime']
        
        # Extend the expiration
        print("Extending DevServer lifetime...")
        result = run_in_bastion(f"devctl extend {server_name} --time 5m")
        assert result.returncode == 0

        # Verify new expiration is later
        devserver = k8s_custom_objects_api.get_namespaced_custom_object(
            group="apps.devservers.io", version="v1", name=server_name,
            namespace=namespace, plural="devservers"
        )
        new_expiration = devserver['spec']['lifecycle']['expirationTime']
        
        assert new_expiration > original_expiration
        
        # Cleanup
        run_in_bastion(f"devctl delete {server_name} --force")

    def test_flavor_update(self, k8s_api, k8s_custom_objects_api):
        """Verify that a DevServer's flavor can be updated, preserving its PVC."""
        server_name = "test-flavor-update"
        username = "testuser"
        namespace = f"dev-{username}"
        pvc_name = f"{server_name}-home"

        run_in_bastion(f"devctl delete {server_name} --force")
        time.sleep(5) # Allow time for PVC to be deleted

        # Create with cpu-small
        result = run_in_bastion(f"devctl create {server_name} --flavor cpu-small --wait")
        assert result.returncode == 0
        
        # Check initial PVC UID
        pvc = k8s_api.read_namespaced_persistent_volume_claim(pvc_name, namespace)
        original_pvc_uid = pvc.metadata.uid

        # Check initial deployment resources
        apps_v1 = client.AppsV1Api()
        deployment = apps_v1.read_namespaced_deployment(server_name, namespace)
        initial_cpu_limit = deployment.spec.template.spec.containers[0].resources.limits['cpu']
        assert initial_cpu_limit == "2" # From cpu-small flavor

        # Update to cpu-medium
        print("Updating DevServer to cpu-medium...")
        result = run_in_bastion(f"devctl update {server_name} --flavor cpu-medium")
        assert result.returncode == 0
        
        # Wait for the deployment to roll out
        print("Waiting for deployment rollout...")
        time.sleep(15) # Simple wait, could be improved with watch
        
        # Verify new deployment resources
        deployment = apps_v1.read_namespaced_deployment(server_name, namespace)
        updated_cpu_limit = deployment.spec.template.spec.containers[0].resources.limits['cpu']
        assert updated_cpu_limit == "4" # From cpu-medium flavor
        
        # Verify PVC was not changed
        pvc = k8s_api.read_namespaced_persistent_volume_claim(pvc_name, namespace)
        assert pvc.metadata.uid == original_pvc_uid
        
        # Cleanup
        run_in_bastion(f"devctl delete {server_name} --force")
