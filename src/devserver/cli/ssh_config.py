import sys
from pathlib import Path
from typing import Optional


def get_config_dir(config_dir_override: Optional[Path] = None) -> Path:
    """Returns the path to the devserver config directory."""
    base_dir = (
        config_dir_override
        if config_dir_override
        else Path.home() / ".config" / "devserver"
    )
    base_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return base_dir


def _get_permission_file(config_dir: Path) -> Path:
    """Returns the path to the SSH config permission file."""
    return config_dir / "ssh-config-permission"


def check_ssh_config_permission(
    ask_prompt: bool = False,
    assume_yes: bool = False,
    config_dir_override: Optional[Path] = None,
) -> bool:
    """
    Checks if the user has given permission to modify ~/.ssh/config.

    Args:
        ask_prompt: If True, prompt the user for permission if not already given.
        assume_yes: If True, automatically grant permission without prompting.
        config_dir_override: An alternative path for the config directory.

    Returns:
        True if permission is granted, False otherwise.
    """
    config_dir = get_config_dir(config_dir_override)
    permission_file = _get_permission_file(config_dir)

    if permission_file.exists():
        return permission_file.read_text().strip() == "yes"

    if assume_yes:
        permission_file.write_text("yes")
        return True

    ssh_config = Path.home() / ".ssh" / "config"
    if ssh_config.exists():
        try:
            content = ssh_config.read_text()
            if f"Include {config_dir}/*.sshconfig" in content:
                permission_file.write_text("yes")
                return True
        except Exception:
            pass

    if ask_prompt:
        from rich.console import Console
        from rich.prompt import Confirm

        console = Console()
        console.print(
            "\n[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]"
        )
        console.print("[cyan]🔧 SSH Configuration Setup[/cyan]\n")
        console.print("To enable easy SSH access and VS Code Remote connections,")
        console.print("we can add devserver configs to your ~/.ssh/config file.")
        console.print("\n[dim]This adds one line at the top of ~/.ssh/config:[/dim]")
        console.print(f"[dim]  Include {config_dir}/*.sshconfig[/dim]\n")
        console.print("[green]Benefits:[/green]")
        console.print("  • Simple commands: [green]ssh <devserver-name>[/green]")
        console.print(
            "  • VS Code Remote works: [green]code --remote ssh-remote+<devserver-name>[/green]"
        )

        approved = Confirm.ask(
            "\n[bold]May we add this line to your ~/.ssh/config?[/bold]", default=True
        )
        permission_file.write_text("yes" if approved else "no")
        return approved

    return False


def ensure_ssh_config_include(
    assume_yes: bool = False, config_dir_override: Optional[Path] = None
) -> bool:
    """
    Ensures the Include directive for devserver configs is present in ~/.ssh/config.

    Returns:
        True if the Include directive is present or was added, False otherwise.
    """
    if not check_ssh_config_permission(
        ask_prompt=True, assume_yes=assume_yes, config_dir_override=config_dir_override
    ):
        return False

    config_dir = get_config_dir(config_dir_override)
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    ssh_config_path = ssh_dir / "config"
    include_line = f"Include {config_dir}/*.sshconfig\n"

    try:
        content = ssh_config_path.read_text() if ssh_config_path.exists() else ""
        if f"Include {config_dir}/" in content:
            return True

        new_content = include_line + "\n" + content
        ssh_config_path.write_text(new_content)
        ssh_config_path.chmod(0o600)
        return True
    except Exception:
        return False


def set_ssh_config_permission(
    enabled: bool, config_dir_override: Optional[Path] = None
):
    """
    Sets the permission for modifying the SSH config.
    """
    config_dir = get_config_dir(config_dir_override)
    permission_file = _get_permission_file(config_dir)
    permission_file.write_text("yes" if enabled else "no")


def create_ssh_config_for_devserver(
    name: str,
    ssh_private_key_file: str,
    assume_yes: bool = False,
    config_dir_override: Optional[Path] = None,
) -> tuple[Path, bool]:
    """
    Creates an SSH config file for a devserver.

    Args:
        name: The name of the devserver.
        ssh_private_key_file: Path to the SSH private key file.
        assume_yes: If True, automatically grant permission without prompting.
        config_dir_override: An alternative path for the config directory.

    Returns:
        A tuple containing the path to the config file and a boolean indicating
        if the Include directive is being used.
    """
    ensure_ssh_config_include(
        assume_yes=assume_yes, config_dir_override=config_dir_override
    )

    config_dir = get_config_dir(config_dir_override)
    key_path = Path(ssh_private_key_file).expanduser()
    config_path = config_dir / f"{name}.sshconfig"

    python_executable = Path(sys.executable)

    config_content = f"""
Host {name}
    User dev
    ProxyCommand {python_executable} -m devserver.cli.main ssh --proxy-mode {name}
    IdentityFile {key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
"""
    config_path.write_text(config_content)
    config_path.chmod(0o600)

    return config_path, check_ssh_config_permission(
        config_dir_override=config_dir_override
    )


def remove_ssh_config_for_devserver(
    name: str, config_dir_override: Optional[Path] = None
):
    """
    Removes the SSH config file for a devserver.
    """
    config_dir = get_config_dir(config_dir_override)
    config_path = config_dir / f"{name}.sshconfig"
    if config_path.exists():
        config_path.unlink()
