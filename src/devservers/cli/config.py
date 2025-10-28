import copy
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml
from rich.console import Console

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "devctl"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yml"
DEFAULT_CONFIG: Dict[str, Any] = {
    "ssh": {
        "public_key_file": "",
        "private_key_file": "",
        "forward_agent": False,
    },
    "devctl-ssh-config-dir": str(DEFAULT_CONFIG_DIR / "ssh/"),
}

_SSH_KEY_PREFERENCE = [
    "id_ed25519",
    "id_ecdsa",
    "id_ecdsa_sk",
    "id_rsa",
]


def _discover_default_ssh_keys() -> Tuple[str, str]:
    ssh_dir = Path.home() / ".ssh"

    for key_name in _SSH_KEY_PREFERENCE:
        private_path = ssh_dir / key_name
        public_path = ssh_dir / f"{key_name}.pub"

        if private_path.is_file() and public_path.is_file():
            return str(private_path), str(public_path)

    console = Console()
    console.print(
        "[yellow]⚠️ No SSH key pair found in ~/.ssh. Configure ssh.private_key_file/ssh.public_key_file in your devctl config or generate a key (id_ed25519, id_ecdsa, id_ecdsa_sk, id_rsa) and then rerun.[/yellow]"
    )
    sys.exit(1)


class Configuration:
    def __init__(self, config_data: Dict[str, Any]):
        self._config = config_data
        self._config.setdefault("ssh", {})
        self._discovered_private_key: Optional[str] = None
        self._discovered_public_key: Optional[str] = None

    @property
    def ssh_public_key_file(self) -> str:
        configured_value = self._config.get("ssh", {}).get("public_key_file", "")
        assert configured_value, "SSH public key file not configured"
        return configured_value

    @property
    def ssh_private_key_file(self) -> str:
        configured_value = self._config.get("ssh", {}).get("private_key_file", "")
        assert configured_value, "SSH private key file not configured"
        return configured_value

    @property
    def ssh_config_dir(self) -> Path:
        path_str = self._config.get(
            "devctl-ssh-config-dir", str(DEFAULT_CONFIG_DIR / "ssh/")
        )
        return Path(path_str).expanduser()

    @property
    def ssh_forward_agent(self) -> bool:
        return self._config.get("ssh", {}).get(
            "forward_agent", False
        )


def get_default_config_path() -> Path:
    return DEFAULT_CONFIG_PATH


def create_default_config(path: Path):
    """Creates a default configuration file at the specified path."""
    console = Console()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        config = copy.deepcopy(DEFAULT_CONFIG)

        private_key, public_key = _discover_default_ssh_keys()
        config["ssh"]["private_key_file"] = private_key
        config["ssh"]["public_key_file"] = public_key
        console.print(
            f"[green]Detected SSH key pair:[/green] [cyan]{public_key}[/cyan]"
        )

        with open(path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        console.print(f"[green]✅ Default configuration created at {path}[/green]")
    except Exception as e:
        console.print(f"[red]Error creating default configuration: {e}[/red]")


def deep_merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination

def load_config(config_path: Optional[Path]) -> Configuration:
    config_data = copy.deepcopy(DEFAULT_CONFIG)
    if config_path and config_path.exists():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)
        if user_config:
            config_data = deep_merge(user_config, config_data)
    return Configuration(config_data)
