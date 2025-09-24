"""Status command implementation."""

import click
from rich.table import Table

from ..api.kubectl import test_kubernetes_connectivity, test_devserver_access
from ..api.devserver import list_devservers, list_flavors
from ..ui.console import console, create_devserver_table
from ..config.settings import get_username, get_user_namespace, is_bastion_environment, VERSION


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show environment and DevServer status."""
    verbose = ctx.obj['verbose']
    username = get_username()
    namespace = get_user_namespace()
    
    console.print("[bold]DevCtl Phase 3 Status[/bold]")
    console.print()
    
    table = Table(title="Environment Info")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Username", username)
    table.add_row("Assigned Namespace", namespace)
    table.add_row("CLI Version", VERSION)
    table.add_row("CLI Location", __file__)
    
    # Check environment
    if is_bastion_environment():
        table.add_row("Environment", "Bastion Container ✓")
    else:
        table.add_row("Environment", "Local Development")
    
    # Test connectivity
    k8s_status = test_kubernetes_connectivity(namespace, verbose)
    table.add_row("Kubernetes", k8s_status)
    
    # Test DevServer CRD access
    devserver_status = test_devserver_access(namespace)
    table.add_row("DevServer CRDs", devserver_status)
    
    console.print(table)
    
    # Show user's DevServers
    devservers = list_devservers(namespace)
    if devservers:
        console.print(f"\n[green]Your DevServers ({len(devservers)}):[/green]")
        ds_table = create_devserver_table(devservers)
        console.print(ds_table)
    else:
        console.print(f"\n[yellow]No DevServers found in namespace '{namespace}'[/yellow]")
        console.print("Create one with: [cyan]devctl create <name> --flavor <flavor>[/cyan]")
    
    # Show available flavors
    flavors = list_flavors()
    if flavors:
        console.print(f"\n[green]Available Flavors ({len(flavors)}):[/green]")
        flavor_table = Table()
        flavor_table.add_column("Name", style="cyan")
        flavor_table.add_column("CPU Request", style="blue")
        flavor_table.add_column("Memory Request", style="blue")
        
        for flavor in flavors:
            resources = flavor['spec'].get('resources', {})
            requests = resources.get('requests', {})
            flavor_table.add_row(
                flavor['metadata']['name'],
                requests.get('cpu', 'N/A'),
                requests.get('memory', 'N/A')
            )
        console.print(flavor_table)
    
    # Phase 3 capabilities notice
    console.print("\n[green]Phase 3 Capabilities:[/green]")
    console.print("• ✅ Complete DevServer lifecycle management")
    console.print("• ✅ Automatic resource provisioning (PVC, Deployment, Service)")
    console.print("• ✅ Container access and SSH endpoints")
    console.print("• ✅ Resource flavors and sizing")
    console.print("\n[yellow]Coming in Phase 4:[/yellow]")
    console.print("• Distributed PyTorch training support")
    console.print("• Auto-shutdown and lifecycle management")
    console.print("• Enhanced monitoring and cost tracking")
