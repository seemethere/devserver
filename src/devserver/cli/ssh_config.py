import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Confirm



def _get_permission_file(config_dir: Path) -> Path:
    """Returns the path to the SSH config permission file."""
    config_dir.mkdir(mode=0o700, exist_ok=True)
    return config_dir / "ssh-config-permission"


def check_ssh_config_permission(
    ssh_config_dir: Path,
    ask_prompt: bool = False,
    assume_yes: bool = False,
) -> bool:
    """
    Checks if the user has given permission to modify ~/.ssh/config.

    Args:
        ssh_config_dir: The path to the devserver ssh config directory.
        ask_prompt: If True, prompt the user for permission if not already given.
        assume_yes: If True, automatically grant permission without prompting.

    Returns:
        True if permission is granted, False otherwise.
    """
    permission_file = _get_permission_file(ssh_config_dir)

    if permission_file.exists():
        return permission_file.read_text().strip() == "yes"

    if assume_yes:
        permission_file.write_text("yes")
        return True

    ssh_config = Path.home() / ".ssh" / "config"
    if ssh_config.exists():
        try:
            content = ssh_config.read_text()
            if f"Include {ssh_config_dir}/*.sshconfig" in content:
                permission_file.write_text("yes")
                return True
        except Exception:
            pass

    if ask_prompt:
        console = Console()
        console.print(
            "\n[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]"
        )
        console.print("[cyan]🔧 SSH Configuration Setup[/cyan]\n")
        console.print("To enable easy SSH access and VS Code Remote connections,")
        console.print("we can add devserver configs to your ~/.ssh/config file.")
        console.print("\n[dim]This adds one line at the top of ~/.ssh/config:[/dim]")
        console.print(f"[dim]  Include {ssh_config_dir}/*.sshconfig[/dim]\n")
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
    ssh_config_dir: Path,
    assume_yes: bool = False,
) -> bool:
    """
    Ensures the Include directive for devserver configs is present in ~/.ssh/config.

    Returns:
        True if the Include directive is present or was added, False otherwise.
    """
    if not check_ssh_config_permission(
        ssh_config_dir, ask_prompt=True, assume_yes=assume_yes
    ):
        return False

    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    ssh_config_path = ssh_dir / "config"
    include_line = f"Include {ssh_config_dir}/*.sshconfig\n"

    try:
        content = ssh_config_path.read_text() if ssh_config_path.exists() else ""
        if f"Include {ssh_config_dir}/" in content:
            return True

        new_content = include_line + "\n" + content
        ssh_config_path.write_text(new_content)
        ssh_config_path.chmod(0o600)
        return True
    except Exception:
        return False


def set_ssh_config_permission(
    ssh_config_dir: Path,
    enabled: bool,
):
    """
    Sets the permission for modifying the SSH config.
    """
    permission_file = _get_permission_file(ssh_config_dir)
    permission_file.write_text("yes" if enabled else "no")


def create_ssh_config_for_devserver(
    ssh_config_dir: Path,
    name: str,
    ssh_private_key_file: str,
    user: Optional[str] = None,
    namespace: Optional[str] = None,
    kubeconfig_path: Optional[str] = None,
    ssh_forward_agent: bool = False,
    assume_yes: bool = False,
) -> tuple[Path, bool]:
    """
    Creates an SSH config file for a devserver.

    Args:
        ssh_config_dir: The path to the devserver ssh config directory.
        name: The name of the devserver.
        ssh_private_key_file: Path to the SSH private key file.
        user: The user associated with the devserver.
        namespace: The namespace of the devserver.
        kubeconfig_path: Optional path to the kubeconfig file.
        ssh_forward_agent: If True, forward the SSH agent. Default is False.
        assume_yes: If True, automatically grant permission without prompting.

    Returns:
        A tuple containing the path to the config file and a boolean indicating
        if the Include directive is being used.
    """
    ensure_ssh_config_include(
        ssh_config_dir,
        assume_yes=assume_yes,
    )

    key_path = Path(ssh_private_key_file).expanduser()
    config_filename = f"{user}-{name}.sshconfig" if user else f"{name}.sshconfig"
    config_path = ssh_config_dir / config_filename

    python_executable = Path(sys.executable)
    namespace_arg = f"--namespace {namespace}" if namespace else ""
    proxy_command_env = f"KUBECONFIG={kubeconfig_path} " if kubeconfig_path else ""

    config_content = f"""
Host {name}
    User dev
    ProxyCommand {proxy_command_env}{python_executable} -m devserver.cli.main ssh --proxy-mode {name} {namespace_arg}
    IdentityFile {key_path}
    ForwardAgent {"yes" if ssh_forward_agent else "no"}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
"""
    config_path.write_text(config_content)
    config_path.chmod(0o600)

    return config_path, check_ssh_config_permission(ssh_config_dir)


def remove_ssh_config_for_devserver(
    ssh_config_dir: Path,
    name: str,
    user: Optional[str] = None,
):
    """
    Removes the SSH config file for a devserver.
    """
    config_filename = f"{user}-{name}.sshconfig" if user else f"{name}.sshconfig"
    config_path = ssh_config_dir / config_filename
    if config_path.exists():
        config_path.unlink()
