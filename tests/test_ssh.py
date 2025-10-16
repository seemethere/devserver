import asyncio
import pytest
from typing import Any, Dict
import uuid
import io
import sys
from pathlib import Path

from devserver.cli import handlers
from tests.conftest import TEST_NAMESPACE
from kubernetes import client
from tests.helpers import async_wait_for, wait_for_devserver_to_exist
from devserver.cli.config import Configuration
from devserver.cli.utils import get_current_context


@pytest.mark.parametrize("image", ["ubuntu:latest", "fedora:latest"])
@pytest.mark.asyncio
async def test_ssh_command_functional_on_various_images(
    operator_running: Any,
    k8s_clients: Dict[str, Any],
    test_flavor: str,
    test_ssh_key_pair: dict[str, str],
    image: str,
    test_config: Configuration,
) -> None:
    """
    Functional test for the 'ssh' command that verifies an actual SSH connection
    on different base images.
    """
    core_api = k8s_clients["core_v1"]
    # Sanitize image name for use in devserver name
    sanitized_image_name = image.replace(":", "-").replace("/", "-")
    devserver_name = f"ssh-test-{sanitized_image_name}-{uuid.uuid4().hex[:6]}"
    pod_name = f"{devserver_name}-0"

    try:
        # Create a DevServer for the test
        await asyncio.to_thread(
            handlers.create_devserver,
            configuration=test_config,
            name=devserver_name,
            flavor=test_flavor,
            image=image,
            namespace=TEST_NAMESPACE,
            ssh_public_key_file=test_ssh_key_pair["public"],
        )

        # Wait for the pod to be running and ready
        async def is_pod_ready():
            try:
                pod = await asyncio.to_thread(
                    core_api.read_namespaced_pod,
                    name=pod_name,
                    namespace=TEST_NAMESPACE,
                )
                if pod.status.phase == "Running" and pod.status.container_statuses:
                    if all(cs.ready for cs in pod.status.container_statuses):
                        return True
            except client.ApiException as e:
                if e.status == 404:
                    return False  # Pod not found yet, continue polling
                raise  # Re-raise other API errors
            return False

        await async_wait_for(
            is_pod_ready,
            timeout=120,
            interval=2,
            failure_message=f"Pod {pod_name} did not become ready in time.",
        )

        # Capture stdout to check the command output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        # Poll the ssh command until it succeeds
        async def ssh_command_succeeds():
            try:
                # Replace the actual handler call with a stub or mock if needed,
                # but for a functional test, calling the real thing is better.
                await asyncio.to_thread(
                    handlers.ssh_devserver,
                    configuration=test_config,
                    name=devserver_name,
                    namespace=TEST_NAMESPACE,
                    ssh_private_key_file=test_ssh_key_pair["private"],
                    remote_command=("whoami",),
                    assume_yes=True,
                    no_proxy=False,
                )
                return True
            except Exception as e:
                # In a real test, you might want to inspect the exception
                # to see if it's a connection error. For this example, we retry on any.
                print(f"SSH command failed with: {e}. Retrying...")
                return False

        await async_wait_for(
            ssh_command_succeeds,
            timeout=30,
            interval=2,
            failure_message="SSH command did not succeed in time.",
        )

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # The output should contain 'dev' indicating the correct user
        assert "dev" in output.strip()

    finally:
        # Cleanup
        try:
            await asyncio.to_thread(
                handlers.delete_devserver,
                configuration=test_config,
                name=devserver_name,
                namespace=TEST_NAMESPACE,
            )
        except Exception:
            pass


@pytest.mark.asyncio
async def test_ssh_config_file_management(
    operator_running: Any,
    k8s_clients: Dict[str, Any],
    test_flavor: str,
    test_ssh_key_pair: dict[str, str],
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Tests the creation, content, and cleanup of the devserver SSH config files.
    """
    devserver_name = f"ssh-config-test-{uuid.uuid4().hex[:6]}"
    config_dir = tmp_path / "ssh_config"
    config_dir.mkdir()

    test_config_with_path = Configuration({
        "devctl-ssh-config-dir": str(config_dir),
    })

    # We need to run ssh with a dummy command, but since port-forwarding will fail
    # in a non-interactive test, we'll patch subprocess.run to prevent it from blocking.
    called_ssh_command = None

    def mock_subprocess_run(command, *args, **kwargs):
        nonlocal called_ssh_command
        if command and command[0] == "ssh":
            called_ssh_command = command

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.delenv("KUBECONFIG", raising=False)

    mock_user = "test@example.com"
    monkeypatch.setattr(
        "devserver.cli.handlers.ssh.get_current_context", lambda: (mock_user, "default")
    )
    monkeypatch.setattr(
        "devserver.cli.handlers.delete.get_current_context",
        lambda: (mock_user, "default"),
    )
    monkeypatch.setattr("tests.test_ssh.get_current_context", lambda: (mock_user, "default"))

    try:
        # 1. Test config file creation
        await asyncio.to_thread(
            handlers.create_devserver,
            configuration=test_config_with_path,
            name=devserver_name,
            flavor=test_flavor,
            namespace=TEST_NAMESPACE,
            ssh_public_key_file=test_ssh_key_pair["public"],
        )

        # Wait for the DevServer CRD object to be available via the API
        await wait_for_devserver_to_exist(
            k8s_clients["custom_objects_api"], devserver_name, TEST_NAMESPACE
        )

        await asyncio.to_thread(
            handlers.ssh_devserver,
            configuration=test_config_with_path,
            name=devserver_name,
            namespace=TEST_NAMESPACE,
            ssh_private_key_file=test_ssh_key_pair["private"],
            remote_command=("whoami",),
            assume_yes=True,
            no_proxy=False,
        )

        user, _ = get_current_context()
        sanitized_user = user.replace("@", "-")
        hostname = f"devserver-{sanitized_user}-{devserver_name}"
        assert called_ssh_command == ["ssh", hostname, "whoami"]

        # Find the config file (it may have a user prefix like {user}-{name}.sshconfig)
        config_files = list(config_dir.glob(f"*{devserver_name}.sshconfig"))
        assert len(config_files) == 1, f"Expected 1 config file, found {len(config_files)}"
        config_file = config_files[0]

        # 2. Test config file content
        content = config_file.read_text()
        python_executable = sys.executable
        namespace_arg = f"--namespace {TEST_NAMESPACE}"
        expected_proxy_command = (
            f"ProxyCommand sh -c '{python_executable} -m devserver.cli.main ssh-proxy {devserver_name} {namespace_arg}'"
        )
        assert f"Host {hostname}" in content
        assert expected_proxy_command in content
        assert "IdentityAgent SSH_AUTH_SOCK" in content

    finally:
        # 3. Test cleanup on deletion
        await asyncio.to_thread(
            handlers.delete_devserver,
            configuration=test_config_with_path,
            name=devserver_name,
            namespace=TEST_NAMESPACE,
        )
        assert not config_file.exists()

    # 4. Test cleanup of stale config for expired/non-existent devserver
    # Manually create a stale config file with the same naming pattern
    stale_config_name = "stale-devserver"
    user, _ = get_current_context()
    stale_filename = f"{user}-{stale_config_name}.sshconfig" if user else f"{stale_config_name}.sshconfig"
    stale_config_file = config_dir / stale_filename
    stale_config_file.write_text("dummy content")

    # The ssh command should exit, so we catch the SystemExit exception
    with pytest.raises(SystemExit):
        await asyncio.to_thread(
            handlers.ssh_devserver,
            configuration=test_config_with_path,
            name=stale_config_name,
            namespace=TEST_NAMESPACE,
            ssh_private_key_file=test_ssh_key_pair["private"],
            remote_command=("whoami",),
            assume_yes=True,
            no_proxy=False,
        )

    # Check that all config files for the stale devserver have been removed
    stale_config_files = list(config_dir.glob(f"*{stale_config_name}.sshconfig"))
    assert len(stale_config_files) == 0, f"Expected 0 stale config files, found {len(stale_config_files)}"


@pytest.mark.asyncio
async def test_ssh_direct_connection(
    operator_running: Any,
    k8s_clients: Dict[str, Any],
    test_flavor: str,
    test_ssh_key_pair: dict[str, str],
    monkeypatch,
    test_config: Configuration,
) -> None:
    """
    Tests the --no-proxy (direct) SSH connection via port-forwarding.
    """
    devserver_name = f"ssh-direct-test-{uuid.uuid4().hex[:6]}"
    
    # We will patch subprocess.run to verify it's called with the correct port-forward command
    # and to prevent it from hanging in a non-interactive test.
    called_ssh_command = None
    def mock_subprocess_run(command, *args, **kwargs):
        nonlocal called_ssh_command
        called_ssh_command = command
    
    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    
    try:
        # 1. Create a devserver
        await asyncio.to_thread(
            handlers.create_devserver,
            configuration=test_config,
            name=devserver_name,
            flavor=test_flavor,
            namespace=TEST_NAMESPACE,
            ssh_public_key_file=test_ssh_key_pair["public"],
            wait=True,
        )

        # 2. Attempt a direct SSH connection
        await asyncio.to_thread(
            handlers.ssh_devserver,
            configuration=test_config,
            name=devserver_name,
            namespace=TEST_NAMESPACE,
            ssh_private_key_file=test_ssh_key_pair["private"],
            remote_command=("whoami",),
            assume_yes=True,
            no_proxy=True,
        )

        # 3. Verify that subprocess.run was called with a direct ssh command
        assert called_ssh_command is not None
        assert "ssh" in called_ssh_command[0]
        assert "localhost" in "".join(called_ssh_command)
        assert "-p" in called_ssh_command
        
    finally:
        # 4. Cleanup
        await asyncio.to_thread(
            handlers.delete_devserver,
            configuration=test_config,
            name=devserver_name,
            namespace=TEST_NAMESPACE,
        )


@pytest.mark.asyncio
async def test_ssh_config_with_kubeconfig_path(
    operator_running: Any,
    k8s_clients: Dict[str, Any],
    test_flavor: str,
    test_ssh_key_pair: dict[str, str],
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Tests that the SSH config correctly includes the kubeconfig path when provided.
    """
    devserver_name = f"ssh-kube-test-{uuid.uuid4().hex[:6]}"
    config_dir = tmp_path / "ssh_config"
    config_dir.mkdir()
    kubeconfig_file = tmp_path / "test.kubeconfig"
    kubeconfig_file.write_text("apiVersion: v1")

    test_config_with_path = Configuration({
        "devctl-ssh-config-dir": str(config_dir),
    })

    def mock_subprocess_run(*args, **kwargs):
        pass

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setenv("KUBECONFIG", str(kubeconfig_file))

    mock_user = "test@example.com"
    monkeypatch.setattr(
        "devserver.cli.handlers.ssh.get_current_context", lambda: (mock_user, "default")
    )
    monkeypatch.setattr(
        "devserver.cli.handlers.delete.get_current_context",
        lambda: (mock_user, "default"),
    )

    try:
        await asyncio.to_thread(
            handlers.create_devserver,
            configuration=test_config_with_path,
            name=devserver_name,
            flavor=test_flavor,
            namespace=TEST_NAMESPACE,
            ssh_public_key_file=test_ssh_key_pair["public"],
        )

        await wait_for_devserver_to_exist(
            k8s_clients["custom_objects_api"], devserver_name, TEST_NAMESPACE
        )

        await asyncio.to_thread(
            handlers.ssh_devserver,
            configuration=test_config_with_path,
            name=devserver_name,
            namespace=TEST_NAMESPACE,
            ssh_private_key_file=test_ssh_key_pair["private"],
            remote_command=("whoami",),
            assume_yes=True,
            no_proxy=False,
        )

        config_files = list(config_dir.glob(f"*{devserver_name}.sshconfig"))
        assert len(config_files) == 1
        config_file = config_files[0]

        content = config_file.read_text()
        sanitized_user = mock_user.replace("@", "-")
        hostname = f"devserver-{sanitized_user}-{devserver_name}"
        assert f"Host {hostname}" in content
        python_executable = sys.executable
        expected_proxy_command = (
            f"ProxyCommand sh -c '{python_executable} -m devserver.cli.main ssh-proxy {devserver_name} "
            f"--namespace {TEST_NAMESPACE} --kubeconfig-path {kubeconfig_file}'"
        )
        assert expected_proxy_command in content

    finally:
        await asyncio.to_thread(
            handlers.delete_devserver,
            configuration=test_config_with_path,
            name=devserver_name,
            namespace=TEST_NAMESPACE,
        )
