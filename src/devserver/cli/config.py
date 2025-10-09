import yaml
from pathlib import Path
from typing import Optional, Any

DEFAULT_CONFIG = {
    "ssh": {
        "public_key_file": "~/.ssh/id_rsa.pub",
    },
    "devctl-ssh-config-dir": "~/.config/devserver/ssh/",
}


def get_default_config_path() -> Path:
    return Path.home() / ".config" / "devserver" / "config.yml"


def create_default_config(path: Path):
    """Creates a default configuration file at the specified path."""
    from rich.console import Console

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

def load_config(config_path: Optional[Path]) -> dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    if config_path and config_path.exists():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)
        if user_config:
            config = deep_merge(user_config, config)
    return config
