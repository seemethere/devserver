#!/usr/bin/env python3
"""Simple Phase 1 CLI for devctl - proof of concept only."""

import os
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

console = Console()

@click.group()
@click.version_option(version="0.1.0-phase1")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """DevCtl Phase 1 - Bastion Proof of Concept
    
    This is a minimal CLI to prove the bastion server concept works.
    Full functionality will be added in Phase 2 with the operator.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['console'] = console


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show bastion and user status."""
    verbose = ctx.obj['verbose']
    
    console.print("[bold]DevCtl Phase 1 Status[/bold]")
    console.print()
    
    # Basic user info
    username = os.environ.get('USER', 'unknown')
    namespace = f"dev-{username}"
    
    table = Table(title="Environment Info")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Username", username)
    table.add_row("Assigned Namespace", namespace)
    table.add_row("Bastion Version", "0.1.0-phase1")
    table.add_row("CLI Location", __file__)
    
    # Check if we're in the bastion container
    if os.path.exists('/.bastion-marker'):
        table.add_row("Environment", "Bastion Container ✓")
    else:
        table.add_row("Environment", "Local Development")
    
    # Basic k8s connectivity check
    try:
        import subprocess
        result = subprocess.run(['kubectl', 'cluster-info'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            table.add_row("Kubernetes", "Connected ✓")
            if verbose:
                console.print("\n[dim]Cluster Info:[/dim]")
                console.print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
        else:
            table.add_row("Kubernetes", "Connection Failed ✗")
    except Exception as e:
        table.add_row("Kubernetes", f"Error: {e}")
    
    console.print(table)
    
    # Phase 1 limitations notice
    console.print("\n[yellow]Phase 1 Limitations:[/yellow]")
    console.print("• No server creation yet (coming in Phase 2)")
    console.print("• No CRDs or operator (coming in Phase 2)")
    console.print("• This is just a bastion infrastructure test")


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show information about available commands and next steps."""
    console.print("[bold]DevCtl Phase 1 - Available Commands[/bold]")
    console.print()
    
    table = Table()
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    
    table.add_row("devctl status", "Show current environment status")
    table.add_row("devctl info", "Show this information")
    table.add_row("devctl test-k8s", "Test basic Kubernetes connectivity")
    table.add_row("devctl --help", "Show detailed help")
    
    console.print(table)
    
    console.print("\n[yellow]Coming in Phase 2:[/yellow]")
    console.print("• devctl create <name> --flavor <flavor>")
    console.print("• devctl list")
    console.print("• devctl delete <name>")
    console.print("• devctl ssh <name>")


@cli.command('test-k8s')
@click.pass_context  
def test_k8s(ctx: click.Context) -> None:
    """Test basic Kubernetes connectivity and permissions."""
    verbose = ctx.obj['verbose']
    
    console.print("[bold]Testing Kubernetes Connectivity[/bold]")
    console.print()
    
    username = os.environ.get('USER', 'unknown')
    namespace = f"dev-{username}"
    
    tests = [
        ("Cluster Info", ["kubectl", "cluster-info", "--request-timeout=5s"]),
        ("List Namespaces", ["kubectl", "get", "namespaces"]),
        (f"Check Namespace {namespace}", ["kubectl", "get", "namespace", namespace]),
        ("List Pods in Namespace", ["kubectl", "get", "pods", "-n", namespace]),
    ]
    
    for test_name, command in tests:
        console.print(f"Testing: [cyan]{test_name}[/cyan]")
        
        try:
            import subprocess
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                console.print(f"  ✓ [green]Success[/green]")
                if verbose and result.stdout:
                    console.print(f"  [dim]{result.stdout[:100]}...[/dim]")
            else:
                console.print(f"  ✗ [red]Failed[/red]")
                if verbose and result.stderr:
                    console.print(f"  [dim]{result.stderr[:100]}...[/dim]")
                    
        except subprocess.TimeoutExpired:
            console.print(f"  ⏱ [yellow]Timeout[/yellow]")
        except Exception as e:
            console.print(f"  ✗ [red]Error: {e}[/red]")
        
        console.print()


if __name__ == '__main__':
    cli()