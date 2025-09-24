"""Info and help commands."""

import click
from rich.table import Table

from ..ui.console import console


@click.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show information about available commands and next steps."""
    console.print("[bold]DevCtl Phase 3 - Available Commands[/bold]")
    console.print()
    
    table = Table()
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    
    # Basic commands
    table.add_row("devctl status", "Show environment and DevServer status")
    table.add_row("devctl info", "Show this information")
    table.add_row("devctl test-k8s", "Test Kubernetes connectivity and permissions")
    
    # DevServer management
    table.add_row("devctl create <name> --flavor <flavor>", "Create a new development server")
    table.add_row("devctl list", "List your development servers")
    table.add_row("devctl describe <name>", "Show detailed DevServer information")
    table.add_row("devctl ssh <name>", "SSH into a development server (interactive)")
    table.add_row("devctl exec <name>", "Execute commands in development server")
    table.add_row("devctl delete <name>", "Delete a development server")
    
    # Utility commands
    table.add_row("devctl flavors", "List available resource flavors")
    table.add_row("devctl --help", "Show detailed help")
    
    console.print(table)
    
    console.print("\n[green]DevServer Examples:[/green]")
    console.print("• [cyan]devctl create mydev --flavor cpu-small[/cyan] - Create small dev server")
    console.print("• [cyan]devctl ssh mydev[/cyan] - Connect to dev server")
    console.print("• [cyan]devctl exec mydev -- python train.py[/cyan] - Run specific commands")
    console.print("• [cyan]devctl delete mydev[/cyan] - Remove dev server")
    
    console.print("\n[yellow]Coming in Phase 4:[/yellow]")
    console.print("• devctl create <name> --distributed --replicas N")
    console.print("• devctl monitor <name> (training progress)")
    console.print("• devctl logs <name> (container logs)")
