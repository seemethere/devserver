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
@click.version_option(version="0.2.0-phase2")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """DevCtl Phase 2 - Secure User Provisioning
    
    Phase 2 provides secure user provisioning with automatic namespace creation,
    user-specific ServiceAccounts, and namespace-scoped kubectl access.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['console'] = console


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show bastion and user status."""
    verbose = ctx.obj['verbose']
    
    console.print("[bold]DevCtl Phase 2 Status[/bold]")
    console.print()
    
    # Basic user info
    username = os.environ.get('USER', 'unknown')
    namespace = f"dev-{username}"
    
    table = Table(title="Environment Info")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Username", username)
    table.add_row("Assigned Namespace", namespace)
    table.add_row("Bastion Version", "0.2.0-phase2")
    table.add_row("CLI Location", __file__)
    
    # Check if we're in the bastion container
    if os.path.exists('/.bastion-marker'):
        table.add_row("Environment", "Bastion Container ✓")
    else:
        table.add_row("Environment", "Local Development")
    
    # Secure k8s connectivity check (using user's limited permissions)
    try:
        import subprocess
        # Test connectivity using user's own namespace instead of cluster-info
        # This respects the security model and limited permissions
        result = subprocess.run(['kubectl', 'get', 'pods', '-n', namespace], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            table.add_row("Kubernetes", "Connected ✓ (Secure)")
            if verbose:
                console.print(f"\n[dim]User namespace ({namespace}) accessible[/dim]")
                console.print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
        else:
            # Try a simpler auth check if pods fail
            auth_result = subprocess.run(['kubectl', 'auth', 'can-i', 'get', 'pods', '-n', namespace], 
                                       capture_output=True, text=True, timeout=5)
            if auth_result.returncode == 0 and 'yes' in auth_result.stdout.lower():
                table.add_row("Kubernetes", "Connected ✓ (Auth OK)")
            else:
                table.add_row("Kubernetes", "Limited Access ⚠")
    except Exception as e:
        table.add_row("Kubernetes", f"Error: {e}")
    
    console.print(table)
    
    # Phase 2 capabilities notice
    console.print("\n[green]Phase 2 Capabilities:[/green]")
    console.print("• ✅ Secure user provisioning (automatic namespace creation)")
    console.print("• ✅ User-specific ServiceAccounts with limited RBAC")
    console.print("• ✅ Namespace-scoped kubectl access")
    console.print("• ✅ User controller with automatic resource provisioning")
    console.print("\n[yellow]Coming in Future Phases:[/yellow]")
    console.print("• DevServer CRD and operator (Phase 3)")
    console.print("• Distributed PyTorch training support (Phase 3)")
    console.print("• Resource flavors and auto-shutdown (Phase 4)")


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show information about available commands and next steps."""
    console.print("[bold]DevCtl Phase 2 - Available Commands[/bold]")
    console.print()
    
    table = Table()
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    
    table.add_row("devctl status", "Show current environment status")
    table.add_row("devctl info", "Show this information")
    table.add_row("devctl test-k8s", "Test basic Kubernetes connectivity")
    table.add_row("devctl --help", "Show detailed help")
    
    console.print(table)
    
    console.print("\n[yellow]Coming in Phase 3 (DevServer Operator):[/yellow]")
    console.print("• devctl create <name> --flavor <flavor>")
    console.print("• devctl list")
    console.print("• devctl delete <name>")
    console.print("• devctl ssh <name>")
    console.print("• devctl run <name> --distributed --replicas N")


@cli.command('test-k8s')
@click.pass_context  
def test_k8s(ctx: click.Context) -> None:
    """Test basic Kubernetes connectivity and permissions."""
    verbose = ctx.obj['verbose']
    
    console.print("[bold]Testing Kubernetes Connectivity[/bold]")
    console.print()
    
    username = os.environ.get('USER', 'unknown')
    namespace = f"dev-{username}"
    
    # Security-appropriate tests for Phase 2 (respects limited user permissions)
    tests = [
        (f"Access User Namespace ({namespace})", ["kubectl", "get", "namespace", namespace]),
        ("List Pods in User Namespace", ["kubectl", "get", "pods", "-n", namespace]),
        ("Check Pod Creation Permission", ["kubectl", "auth", "can-i", "create", "pods", "-n", namespace]),
        ("Check Namespace Creation Permission (Should be NO)", ["kubectl", "auth", "can-i", "create", "namespaces"]),
        ("Check Other Namespace Access (Should be NO)", ["kubectl", "get", "pods", "-n", "kube-system"]),
    ]
    
    for test_name, command in tests:
        console.print(f"Testing: [cyan]{test_name}[/cyan]")
        
        try:
            import subprocess
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            
            # Handle security tests where "failure" is actually success
            if "Should be NO" in test_name:
                if result.returncode != 0 or "no" in result.stdout.lower() or "forbidden" in result.stderr.lower():
                    console.print(f"  ✓ [green]Security OK (Access Denied)[/green]")
                else:
                    console.print(f"  ⚠ [red]Security Issue (Access Allowed)[/red]")
                if verbose:
                    console.print(f"  [dim]Output: {result.stdout[:100] or result.stderr[:100]}...[/dim]")
            else:
                # Normal tests where success is expected
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