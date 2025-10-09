import click
from rich.console import Console
from rich.prompt import Confirm
from pathlib import Path

from . import handlers
from .ssh_config import ensure_ssh_config_include, set_ssh_config_permission, get_config_dir
from .config import load_config, get_default_config_path, create_default_config


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the devserver config file.",
)
@click.option(
    "--assume-yes", is_flag=True, help="Automatically answer yes to all prompts."
)
@click.pass_context
def main(ctx, config_path, assume_yes) -> None:
    """A CLI to manage DevServers."""
    ctx.ensure_object(dict)
    console = Console()

    default_config_path = get_default_config_path()
    effective_config_path = config_path if config_path else default_config_path

    if not effective_config_path.exists() and effective_config_path == default_config_path:
        console.print(f"Configuration file not found at [cyan]{effective_config_path}[/cyan].")
        if assume_yes or Confirm.ask("Would you like to create a default one?", default=True):
            create_default_config(effective_config_path)

    ctx.obj["CONFIG"] = load_config(effective_config_path)
    ctx.obj["ASSUME_YES"] = assume_yes


@main.command(help="Create a new DevServer.")
@click.option("--name", type=str, default="dev", help="The name of the DevServer.")
@click.option("--flavor", type=str, required=True, help="The flavor of the DevServer.")
@click.option("--image", type=str, help="The container image to use.")
@click.option(
    "--ssh-public-key-file",
    type=str,
    default=None,
    help="Path to the SSH public key file.",
)
@click.option(
    "--time",
    "--ttl",
    "time_to_live",
    type=str,
    default="4h",
    help="The time to live for the DevServer.",
)
@click.option(
    "--wait",
    is_flag=True,
    help="Wait for the DevServer to be ready.",
)
@click.pass_context
def create(
    ctx, name: str, flavor: str, image: str, ssh_public_key_file: str, time_to_live: str, wait: bool
) -> None:
    """Create a new DevServer."""
    config = ctx.obj["CONFIG"]
    if ssh_public_key_file is None:
        ssh_public_key_file = config["ssh"]["public_key_file"]
    
    handlers.create_devserver(
        name=name,
        flavor=flavor,
        image=image,
        ssh_public_key_file=ssh_public_key_file,
        time_to_live=time_to_live,
        wait=wait,
    )


@main.command(help="Delete a DevServer.")
@click.argument("name", type=str)
@click.pass_context
def delete(ctx, name: str) -> None:
    """Delete a DevServer."""
    handlers.delete_devserver(name=name)


@main.command(help="Describe a DevServer.")
@click.argument("name", type=str)
def describe(name: str) -> None:
    """Describe a DevServer."""
    handlers.describe_devserver(name=name)


@main.command(name="list", help="List all DevServers.")
def list_command() -> None:
    """List all DevServers."""
    handlers.list_devservers()


@main.command(help="SSH into a DevServer.")
@click.argument("name", type=str)
@click.option(
    "-i",
    "--identity-file",
    "ssh_private_key_file",
    type=str,
    default="~/.ssh/id_rsa",
    help="Path to the SSH private key file.",
)
@click.option(
    "--proxy-mode",
    is_flag=True,
    hidden=True,
    help="Run in proxy mode for SSH ProxyCommand.",
)
@click.argument("remote_command", nargs=-1)
@click.pass_context
def ssh(
    ctx, name: str, ssh_private_key_file: str, proxy_mode: bool, remote_command: tuple[str, ...]
) -> None:
    """SSH into a DevServer."""
    handlers.ssh_devserver(
        name=name,
        ssh_private_key_file=ssh_private_key_file,
        proxy_mode=proxy_mode,
        remote_command=remote_command,
        assume_yes=ctx.obj["ASSUME_YES"],
    )


@main.group()
def config() -> None:
    """Manage devctl configuration."""
    pass


@config.command(name="ssh-include")
@click.argument("action", type=click.Choice(["enable", "disable"]))
@click.pass_context
def ssh_include(ctx, action: str):
    """Enable or disable SSH config Include directive."""
    console = Console()
    assume_yes = ctx.obj["ASSUME_YES"]

    if action.lower() == "enable":
        set_ssh_config_permission(True)
        if ensure_ssh_config_include(
            assume_yes=assume_yes
        ):
            console.print("[green]✅ Enabled SSH config Include directive.[/green]")

            config_dir = get_config_dir()
            console.print(
                f"[cyan]Added 'Include {config_dir}/*.sshconfig' to ~/.ssh/config[/cyan]"
            )
        else:
            console.print("[yellow]SSH config Include was not enabled.[/yellow]")
    elif action.lower() == "disable":
        set_ssh_config_permission(False)
        console.print("[yellow]✅ Disabled automatic SSH config Include.[/yellow]")
        console.print("[dim]Note: Existing Include directive in ~/.ssh/config not removed.[/dim]")
        console.print(
            "[dim]You can manually remove the 'Include ~/.config/devserver/*.sshconfig' line if desired.[/dim]"
        )


if __name__ == "__main__":
    main()
