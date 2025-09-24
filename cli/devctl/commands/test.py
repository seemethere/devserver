"""Test command implementation."""

import subprocess

import click

from ..ui.console import console
from ..config.settings import get_user_namespace


@click.command('test-k8s')
@click.pass_context  
def test_k8s(ctx: click.Context) -> None:
    """Test Kubernetes connectivity, permissions, and DevServer CRD access."""
    verbose = ctx.obj['verbose']
    namespace = get_user_namespace()
    
    console.print("[bold]Testing Kubernetes Connectivity & DevServer Access[/bold]")
    console.print()
    
    # Enhanced tests for Phase 3 (includes DevServer CRD testing)
    tests = [
        (f"Access User Namespace ({namespace})", ["kubectl", "get", "namespace", namespace]),
        ("List Pods in User Namespace", ["kubectl", "get", "pods", "-n", namespace]),
        ("Check Pod Creation Permission", ["kubectl", "auth", "can-i", "create", "pods", "-n", namespace]),
        ("Check DevServer Creation Permission", ["kubectl", "auth", "can-i", "create", "devservers", "-n", namespace]),
        ("Check DevServerFlavor Read Permission (Cluster-scoped)", ["kubectl", "auth", "can-i", "get", "devserverflavors"]),
        ("List DevServers in User Namespace", ["kubectl", "get", "devservers", "-n", namespace]),
        ("List DevServerFlavors (Cluster-scoped)", ["kubectl", "get", "devserverflavors"]),
        ("Check Namespace Creation Permission (Should be NO)", ["kubectl", "auth", "can-i", "create", "namespaces"]),
        ("Check Other Namespace Access (Should be NO)", ["kubectl", "get", "pods", "-n", "kube-system"]),
    ]
    
    for test_name, command in tests:
        console.print(f"Testing: [cyan]{test_name}[/cyan]")
        
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            
            # Handle security tests where "failure" is actually success
            if "Should be NO" in test_name:
                if result.returncode != 0 or "no" in result.stdout.lower() or "forbidden" in result.stderr.lower():
                    console.print("  ✓ [green]Security OK (Access Denied)[/green]")
                else:
                    console.print("  ⚠ [red]Security Issue (Access Allowed)[/red]")
                if verbose:
                    console.print(f"  [dim]Output: {result.stdout[:100] or result.stderr[:100]}...[/dim]")
            else:
                # Normal tests where success is expected
                if result.returncode == 0:
                    console.print("  ✓ [green]Success[/green]")
                    if verbose and result.stdout:
                        console.print(f"  [dim]{result.stdout[:100]}...[/dim]")
                else:
                    console.print("  ✗ [red]Failed[/red]")
                    if verbose and result.stderr:
                        console.print(f"  [dim]{result.stderr[:100]}...[/dim]")
                    
        except subprocess.TimeoutExpired:
            console.print("  ⏱ [yellow]Timeout[/yellow]")
        except Exception as e:
            console.print(f"  ✗ [red]Error: {e}[/red]")
        
        console.print()
