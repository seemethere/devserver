import click
from . import handlers


@click.group()
def main() -> None:
    """A CLI to manage DevServers."""
    pass


@main.command(help="Create a new DevServer.")
@click.option("--name", type=str, default="dev", help="The name of the DevServer.")
@click.option("--flavor", type=str, required=True, help="The flavor of the DevServer.")
@click.option("--image", type=str, help="The container image to use.")
@click.option(
    "--ssh-public-key-file",
    type=str,
    default="~/.ssh/id_rsa.pub",
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
def create(
    name: str, flavor: str, image: str, ssh_public_key_file: str, time_to_live: str
) -> None:
    """Create a new DevServer."""
    handlers.create_devserver(
        name=name,
        flavor=flavor,
        image=image,
        ssh_public_key_file=ssh_public_key_file,
        time_to_live=time_to_live,
    )


@main.command(help="List all DevServers.")
def list() -> None:
    """List all DevServers."""
    handlers.list_devservers()


@main.command(help="Show the available flavors.")
def flavors() -> None:
    """Show the available flavors."""
    handlers.list_flavors()


@main.command(help="Delete a DevServer.")
@click.argument("name", type=str)
def delete(name: str) -> None:
    """Delete a DevServer."""
    handlers.delete_devserver(name=name)


@main.command(help="Describe a DevServer.")
@click.argument("name", type=str)
def describe(name: str) -> None:
    """Describe a DevServer."""
    handlers.describe_devserver(name=name)


@main.command(help="SSH into a DevServer.")
@click.argument("name", type=str)
@click.option(
    "--ssh-private-key-file",
    type=str,
    default="~/.ssh/id_rsa",
    help="Path to the SSH private key file.",
)
@click.argument("remote_command", nargs=-1)
def ssh(name: str, ssh_private_key_file: str, remote_command: tuple[str, ...]) -> None:
    """SSH into a DevServer."""
    handlers.ssh_devserver(
        name=name,
        ssh_private_key_file=ssh_private_key_file,
        remote_command=remote_command,
    )


if __name__ == "__main__":
    main()
