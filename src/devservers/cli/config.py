import yaml
from pathlib import Path
from typing import Optional, Any, Dict
from rich.console import Console

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "devctl"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yml"
DEFAULT_CONFIG = {
    "ssh": {
        "public_key_file": "~/.ssh/id_rsa.pub",
        "private_key_file": "~/.ssh/id_rsa",
        "forward_agent": False,
    },
    "devctl-ssh-config-dir": str(DEFAULT_CONFIG_DIR / "ssh/"),
}


class Configuration:
    def __init__(self, config_data: Dict[str, Any]):
        self._config = config_data

    @property
    def ssh_public_key_file(self) -> str:
        return self._config.get("ssh", {}).get(
            "public_key_file", "~/.ssh/id_rsa.pub"
        )

    @property
    def ssh_private_key_file(self) -> str:
        return self._config.get("ssh", {}).get(
            "private_key_file", "~/.ssh/id_rsa"
        )

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
        with open(path, "w") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)
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
    config_data = DEFAULT_CONFIG.copy()
    if config_path and config_path.exists():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)
        if user_config:
            config_data = deep_merge(user_config, config_data)
    return Configuration(config_data)
