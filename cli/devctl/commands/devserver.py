"""DevServer management commands."""

import subprocess

import click
from rich.table import Table

from ..api.devserver import (
    list_devservers, get_devserver, create_devserver, delete_devserver,
    wait_for_devserver_ready, get_devserver_resources, flavor_exists, list_flavors
)
from ..ui.console import console, create_devserver_table, create_flavor_panels, create_progress_spinner
from ..config.settings import get_username, get_user_namespace, DEFAULT_IMAGE, DEFAULT_HOME_SIZE


@click.command()
@click.argument('name')
@click.option('--flavor', required=True, help='DevServerFlavor to use (e.g., cpu-small)')
@click.option('--image', default=DEFAULT_IMAGE, help='Container image to use')
@click.option('--home-size', default=DEFAULT_HOME_SIZE, help='Size of persistent home directory')
@click.option('--wait', is_flag=True, help='Wait for DevServer to be ready')
@click.pass_context
def create(ctx: click.Context, name: str, flavor: str, image: str, home_size: str, wait: bool) -> None:
    """Create a new development server."""
    username = get_username()
    namespace = get_user_namespace()
    
    console.print(f"[bold]Creating DevServer '{name}'[/bold]")
    console.print(f"Flavor: {flavor}")
    console.print(f"Image: {image}")
    console.print(f"Namespace: {namespace}")
    console.print()
    
    # Check if DevServer already exists
    if get_devserver(name, namespace):
        console.print(f"[red]❌ DevServer '{name}' already exists in namespace '{namespace}'[/red]")
        console.print("Use a different name or delete the existing one first.")
        return
    
    # Check if flavor exists
    if not flavor_exists(flavor):
        console.print(f"[red]❌ DevServerFlavor '{flavor}' not found[/red]")
        console.print("Available flavors:")
        flavors = list_flavors()
        for f in flavors:
            console.print(f"  • {f['metadata']['name']}")
        if not flavors:
            console.print("  (No flavors available - contact administrator)")
        return
    
    # Create DevServer spec
    spec = {
        'owner': f"{username}@company.com",
        'flavor': flavor,
        'image': image,
        'mode': 'standalone',
        'persistentHomeSize': home_size,
        'enableSSH': True,
        'idleTimeout': 3600,
        'autoShutdown': True
    }
    
    # Create DevServer
    if create_devserver(name, spec, namespace):
        console.print(f"[green]✅ DevServer '{name}' created successfully[/green]")
        
        if wait:
            console.print("⏳ Waiting for DevServer to be ready...")
            with create_progress_spinner() as progress:
                task = progress.add_task("Starting development server...", total=None)
                
                if wait_for_devserver_ready(name, namespace):
                    progress.update(task, description="[green]DevServer is ready!")
                    console.print(f"\n[green]🎉 DevServer '{name}' is ready for use![/green]")
                    console.print(f"Access it with: [cyan]devctl exec {name} -- bash[/cyan]")
                else:
                    progress.update(task, description="[red]Timeout waiting for DevServer")
                    console.print("\n[yellow]⚠ DevServer created but not ready within timeout[/yellow]")
                    console.print(f"Check status with: [cyan]devctl describe {name}[/cyan]")
    else:
        console.print("[red]❌ Failed to create DevServer[/red]")


@click.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List your development servers."""
    namespace = get_user_namespace()
    
    devservers = list_devservers(namespace)
    
    if not devservers:
        console.print(f"[yellow]No DevServers found in namespace '{namespace}'[/yellow]")
        console.print("Create one with: [cyan]devctl create <name> --flavor <flavor>[/cyan]")
        return
    
    console.print(f"[bold]DevServers in {namespace}[/bold]")
    console.print()
    
    table = create_devserver_table(devservers)
    console.print(table)


@click.command()
@click.argument('name')
@click.pass_context
def describe(ctx: click.Context, name: str) -> None:
    """Show detailed information about a DevServer."""
    namespace = get_user_namespace()
    
    devserver = get_devserver(name, namespace)
    if not devserver:
        console.print(f"[red]❌ DevServer '{name}' not found in namespace '{namespace}'[/red]")
        return
    
    console.print(f"[bold]DevServer: {name}[/bold]")
    console.print()
    
    # Basic info
    spec = devserver.get('spec', {})
    status = devserver.get('status', {})
    
    info_table = Table(title="Specification")
    info_table.add_column("Field", style="cyan")
    info_table.add_column("Value", style="green")
    
    info_table.add_row("Name", name)
    info_table.add_row("Namespace", namespace)
    info_table.add_row("Owner", spec.get('owner', 'N/A'))
    info_table.add_row("Flavor", spec.get('flavor', 'N/A'))
    info_table.add_row("Image", spec.get('image', 'N/A'))
    info_table.add_row("Mode", spec.get('mode', 'N/A'))
    info_table.add_row("Home Size", spec.get('persistentHomeSize', 'N/A'))
    info_table.add_row("SSH Enabled", str(spec.get('enableSSH', False)))
    
    console.print(info_table)
    
    # Status info
    if status:
        status_table = Table(title="Status")
        status_table.add_column("Field", style="cyan")
        status_table.add_column("Value", style="green")
        
        status_table.add_row("Phase", status.get('phase', 'Unknown'))
        status_table.add_row("Ready", str(status.get('ready', False)))
        status_table.add_row("SSH Endpoint", status.get('sshEndpoint', 'N/A'))
        status_table.add_row("Service Name", status.get('serviceName', 'N/A'))
        if status.get('startTime'):
            status_table.add_row("Started", status['startTime'])
        
        console.print(status_table)
    
    # Show related resources
    console.print("\n[green]Related Resources:[/green]")
    resources_output = get_devserver_resources(name, namespace)
    console.print(resources_output)


@click.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete(ctx: click.Context, name: str, force: bool) -> None:
    """Delete a development server."""
    namespace = get_user_namespace()
    
    if not get_devserver(name, namespace):
        console.print(f"[red]❌ DevServer '{name}' not found in namespace '{namespace}'[/red]")
        return
    
    if not force:
        console.print(f"[yellow]⚠ This will delete DevServer '{name}' and all its data![/yellow]")
        if not click.confirm("Are you sure you want to continue?"):
            console.print("Deletion cancelled.")
            return
    
    console.print(f"[bold]Deleting DevServer '{name}'[/bold]")
    
    if delete_devserver(name, namespace):
        console.print(f"[green]✅ DevServer '{name}' deletion initiated[/green]")
        console.print("Resources will be cleaned up automatically by the operator.")
    else:
        console.print("[red]❌ Failed to delete DevServer[/red]")


@click.command()
@click.argument('name')
@click.argument('command', nargs=-1)
@click.option('--shell', default='bash', help='Shell to use (default: bash)')
@click.pass_context
def exec(ctx: click.Context, name: str, command: tuple, shell: str) -> None:
    """Execute commands in a development server."""
    namespace = get_user_namespace()
    
    devserver = get_devserver(name, namespace)
    if not devserver:
        console.print(f"[red]❌ DevServer '{name}' not found in namespace '{namespace}'[/red]")
        return
    
    # Check if DevServer is ready
    if not devserver.get('status', {}).get('ready'):
        console.print(f"[yellow]⚠ DevServer '{name}' is not ready yet[/yellow]")
        console.print(f"Current status: {devserver.get('status', {}).get('phase', 'Unknown')}")
        console.print(f"Check status with: [cyan]devctl describe {name}[/cyan]")
        return
    
    # Build kubectl exec command
    kubectl_cmd = ["kubectl", "exec", "-it", f"deployment/{name}", "-n", namespace]
    
    if command:
        # Execute specific command
        kubectl_cmd.extend(["--", *command])
        action_desc = f"Running: {' '.join(command)}"
    else:
        # Open interactive shell
        kubectl_cmd.extend(["--", shell])
        action_desc = f"Opening {shell} shell"
    
    console.print(f"[bold]{action_desc} in DevServer '{name}'[/bold]")
    console.print("(Press Ctrl+D or type 'exit' to return)")
    console.print()
    
    try:
        # Execute kubectl with direct TTY access
        subprocess.run(kubectl_cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Command failed with exit code {e.returncode}[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Command interrupted[/yellow]")


@click.command()
@click.argument('name')
@click.option('--shell', default='bash', help='Shell to use (default: bash)')
@click.pass_context
def ssh(ctx: click.Context, name: str, shell: str) -> None:
    """SSH into a development server (interactive shell)."""
    namespace = get_user_namespace()
    
    devserver = get_devserver(name, namespace)
    if not devserver:
        console.print(f"[red]❌ DevServer '{name}' not found in namespace '{namespace}'[/red]")
        return
    
    # Check if DevServer is ready
    if not devserver.get('status', {}).get('ready'):
        console.print(f"[yellow]⚠ DevServer '{name}' is not ready yet[/yellow]")
        console.print(f"Current status: {devserver.get('status', {}).get('phase', 'Unknown')}")
        console.print(f"Check status with: [cyan]devctl describe {name}[/cyan]")
        return
    
    # SSH is just an interactive exec with the specified shell
    console.print(f"[bold]Connecting to DevServer '{name}'[/bold]")
    console.print("(Press Ctrl+D or type 'exit' to disconnect)")
    console.print()
    
    # Build kubectl exec command for interactive shell
    kubectl_cmd = ["kubectl", "exec", "-it", f"deployment/{name}", "-n", namespace, "--", shell]
    
    try:
        # Execute kubectl with direct TTY access
        subprocess.run(kubectl_cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ SSH connection failed with exit code {e.returncode}[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Connection interrupted[/yellow]")


@click.command()
@click.pass_context
def flavors(ctx: click.Context) -> None:
    """List available DevServerFlavors."""
    flavors = list_flavors()
    
    if not flavors:
        console.print("[yellow]No DevServerFlavors found (cluster-wide)[/yellow]")
        console.print("Contact your administrator to create resource flavors.")
        return
    
    console.print("[bold]Available DevServerFlavors (Cluster-wide)[/bold]")
    console.print()
    
    panels = create_flavor_panels(flavors)
    for panel in panels:
        console.print(panel)
