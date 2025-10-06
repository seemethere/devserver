import sys
from pathlib import Path
from typing import Optional

from kubernetes import client, config
from rich.console import Console


def create_devserver(
    name: str,
    flavor: str,
    image: Optional[str] = None,
    ssh_public_key_file: str = "~/.ssh/id_rsa.pub",
    namespace: str = "default",
    time_to_live: str = "4h",
) -> None:
    """Creates a new DevServer resource."""
    config.load_kube_config()
    custom_objects_api = client.CustomObjectsApi()
    console = Console()
    try:
        key_path = Path(ssh_public_key_file).expanduser()
        with open(key_path, "r") as f:
            ssh_public_key = f.read().strip()
    except FileNotFoundError:
        console.print(f"Error: SSH public key file not found at '{key_path}'")
        sys.exit(1)
    except Exception as e:
        console.print(f"Error reading SSH public key file: {e}")
        sys.exit(1)

    # Construct the DevServer manifest
    manifest = {
        "apiVersion": "devserver.io/v1",
        "kind": "DevServer",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "flavor": flavor,
            "image": image or "ubuntu:22.04",  # Default image
            "ssh": {"publicKey": ssh_public_key},
            "lifecycle": {"timeToLive": time_to_live},
            "enableSSH": True,
        },
    }

    try:
        custom_objects_api.create_namespaced_custom_object(
            group="devserver.io",
            version="v1",
            namespace=namespace,
            plural="devservers",
            body=manifest,
        )
        console.print(f"DevServer '{name}' created successfully.")
    except client.ApiException as e:
        if e.status == 409:  # Conflict
            console.print(f"Error: DevServer '{name}' already exists.")
        else:
            console.print(f"Error creating DevServer: {e.reason}")
