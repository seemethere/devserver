import os
import shutil
import subprocess

import pytest

# Check if Docker is installed and the daemon is running
DOCKER_AVAILABLE = shutil.which("docker") is not None


def is_docker_running():
    """Checks if the Docker daemon is responsive."""
    if not DOCKER_AVAILABLE:
        return False
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


DOCKER_RUNNING = is_docker_running()

# Define the project root to mount into the container
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


@pytest.mark.skipif(not DOCKER_RUNNING, reason="Docker is not running or not available.")
@pytest.mark.parametrize("image", ["ubuntu:latest", "fedora:latest"])
def test_startup_script_on_various_images(image):
    """
    Tests that the startup.sh script runs to completion on different base images,
    creating the user and setting up the environment correctly.
    """
    script_path = "src/devservers/operator/devserver/resources/startup.sh"

    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{PROJECT_ROOT}:/app",
        "-w",
        "/app",
        "-e",
        "DEVSERVER_TEST_MODE=true",
        image,
        "sh",
        script_path,
    ]

    result = subprocess.run(
        command, capture_output=True, text=True
    )

    # Ensure the script exits successfully
    assert result.returncode == 0, f"Script failed on {image}. Stderr: {result.stderr}"

    # Verify that the key stages of the script were executed
    assert "Configuring container..." in result.stdout
    assert "Ensuring 'dev' user and group" in result.stdout
    assert "Setting up SSH for 'dev' user" in result.stdout
    assert "Starting sshd..." in result.stdout
    assert "Test mode: skipping sshd execution." in result.stdout

    # Ensure no errors were logged
    assert "ERROR:" not in result.stderr
    assert "ERROR:" not in result.stdout
