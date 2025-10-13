import shutil
import subprocess
import uuid

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
IMAGE_NAME = "seemethere/devserver-base:motd-test"


@pytest.fixture(scope="module")
def motd_test_image():
    """Builds the devserver-base image for testing and yields the image name."""
    if not DOCKER_RUNNING:
        pytest.skip("Docker is not running or not available.")

    image_name = f"seemethere/devserver-base:motd-test-{uuid.uuid4().hex}"

    # Build the image
    build_command = ["docker", "build", "-t", image_name, "docker/base/"]
    result = subprocess.run(build_command, capture_output=True, text=True)
    assert result.returncode == 0, f"Failed to build test image. Stderr: {result.stderr}"

    yield image_name

    # Cleanup the image
    cleanup_command = ["docker", "rmi", "-f", image_name]
    subprocess.run(cleanup_command, capture_output=True, text=True)


@pytest.mark.skipif(not DOCKER_RUNNING, reason="Docker is not running or not available.")
def test_motd_generation(motd_test_image):
    """
    Tests that the generate_motd.sh script runs successfully and produces
    the expected output.
    """
    command = [
        "docker",
        "run",
        "--rm",
        "-e",
        "DEVSERVER_TEST_MODE=true",
        motd_test_image,
        "/usr/local/bin/generate_motd.sh",
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 0, f"MOTD script failed. Stderr: {result.stderr}"

    stdout = result.stdout
    assert "Welcome to your DevServer!" in stdout
    assert "OS:" in stdout
    assert "Kernel:" in stdout
    assert "CPU:" in stdout
    assert "Memory:" in stdout
    assert "Disk:" in stdout
    assert "Uptime:" in stdout
    assert "Happy coding!" in stdout
