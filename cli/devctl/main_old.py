#!/usr/bin/env python3
"""DevCtl Phase 3 CLI - Complete DevServer Management."""

import json
import os
import subprocess
import time
from typing import Optional, Dict, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@click.group()
@click.version_option(version="0.3.0-phase3")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """DevCtl Phase 3 - Complete DevServer Management
    
    Phase 3 provides complete development server lifecycle management with
    DevServer CRDs, automatic resource provisioning, and container access.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['console'] = console
    
    # Set user namespace
    username = os.environ.get('USER', 'unknown')
    ctx.obj['username'] = username
    ctx.obj['namespace'] = f"dev-{username}"


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show environment and DevServer status."""
    verbose = ctx.obj['verbose']
    username = ctx.obj['username']
    namespace = ctx.obj['namespace']
    
    console.print("[bold]DevCtl Phase 3 Status[/bold]")
    console.print()
    
    table = Table(title="Environment Info")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Username", username)
    table.add_row("Assigned Namespace", namespace)
    table.add_row("CLI Version", "0.3.0-phase3")
    table.add_row("CLI Location", __file__)
    
    # Check if we're in the bastion container
    if os.path.exists('/.bastion-marker'):
        table.add_row("Environment", "Bastion Container ✓")
    else:
        table.add_row("Environment", "Local Development")
    
    # Test Kubernetes connectivity
    k8s_status = _test_kubernetes_connectivity(namespace, verbose)
    table.add_row("Kubernetes", k8s_status)
    
    # Test DevServer CRD access
    devserver_status = _test_devserver_access(namespace)
    table.add_row("DevServer CRDs", devserver_status)
    
    console.print(table)
    
    # Show user's DevServers
    devservers = _list_devservers(namespace)
    if devservers:
        console.print(f"\n[green]Your DevServers ({len(devservers)}):[/green]")
        ds_table = Table()
        ds_table.add_column("Name", style="cyan")
        ds_table.add_column("Flavor", style="blue")
        ds_table.add_column("Status", style="green")
        ds_table.add_column("Ready", style="green")
        
        for ds in devservers:
            ready_status = "Yes" if ds.get('status', {}).get('ready') else "No"
            ds_table.add_row(
                ds['metadata']['name'],
                ds['spec'].get('flavor', 'N/A'),
                ds.get('status', {}).get('phase', 'Unknown'),
                ready_status
            )
        console.print(ds_table)
    else:
        console.print(f"\n[yellow]No DevServers found in namespace '{namespace}'[/yellow]")
        console.print("Create one with: [cyan]devctl create <name> --flavor <flavor>[/cyan]")
    
    # Show available flavors
    flavors = _list_flavors(namespace)
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


@cli.command()
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
    table.add_row("devctl delete <name>", "Delete a development server")
    table.add_row("devctl exec <name>", "Execute commands in development server")
    
    # Utility commands
    table.add_row("devctl flavors", "List available resource flavors")
    table.add_row("devctl --help", "Show detailed help")
    
    console.print(table)
    
    console.print("\n[green]DevServer Examples:[/green]")
    console.print("• [cyan]devctl create mydev --flavor cpu-small[/cyan] - Create small dev server")
    console.print("• [cyan]devctl exec mydev -- bash[/cyan] - Open shell in dev server")
    console.print("• [cyan]devctl delete mydev[/cyan] - Remove dev server")
    
    console.print("\n[yellow]Coming in Phase 4:[/yellow]")
    console.print("• devctl create <name> --distributed --replicas N")
    console.print("• devctl ssh <name> (with SSH server setup)")
    console.print("• devctl monitor <name> (training progress)")


@cli.command('test-k8s')
@click.pass_context  
def test_k8s(ctx: click.Context) -> None:
    """Test Kubernetes connectivity, permissions, and DevServer CRD access."""
    verbose = ctx.obj['verbose']
    namespace = ctx.obj['namespace']
    
    console.print("[bold]Testing Kubernetes Connectivity & DevServer Access[/bold]")
    console.print()
    
    # Enhanced tests for Phase 3 (includes DevServer CRD testing)
    tests = [
        (f"Access User Namespace ({namespace})", ["kubectl", "get", "namespace", namespace]),
        ("List Pods in User Namespace", ["kubectl", "get", "pods", "-n", namespace]),
        ("Check Pod Creation Permission", ["kubectl", "auth", "can-i", "create", "pods", "-n", namespace]),
        ("Check DevServer Creation Permission", ["kubectl", "auth", "can-i", "create", "devservers", "-n", namespace]),
        ("Check DevServerFlavor Read Permission", ["kubectl", "auth", "can-i", "get", "devserverflavors", "-n", namespace]),
        ("List DevServers in User Namespace", ["kubectl", "get", "devservers", "-n", namespace]),
        ("List DevServerFlavors in User Namespace", ["kubectl", "get", "devserverflavors", "-n", namespace]),
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


# Helper functions

def _run_kubectl(*args, namespace=None, capture_output=True, timeout=10) -> subprocess.CompletedProcess:
    """Run kubectl command with proper error handling."""
    cmd = ["kubectl"]
    if namespace:
        cmd.extend(["-n", namespace])
    cmd.extend(args)
    
    try:
        return subprocess.run(cmd, capture_output=capture_output, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Exception("Command timed out")

def _test_kubernetes_connectivity(namespace: str, verbose: bool = False) -> str:
    """Test basic Kubernetes connectivity."""
    try:
        result = _run_kubectl("get", "pods", namespace=namespace)
        if result.returncode == 0:
            return "Connected ✓ (Secure)"
        else:
            # Try auth check if pods fail
            auth_result = _run_kubectl("auth", "can-i", "get", "pods", namespace=namespace)
            if auth_result.returncode == 0 and 'yes' in auth_result.stdout.lower():
                return "Connected ✓ (Auth OK)"
            else:
                return "Limited Access ⚠"
    except Exception as e:
        return f"Error: {e}"

def _test_devserver_access(namespace: str) -> str:
    """Test DevServer CRD access."""
    try:
        # Test if we can access DevServer CRDs
        result = _run_kubectl("auth", "can-i", "get", "devservers", namespace=namespace)
        if result.returncode == 0 and 'yes' in result.stdout.lower():
            return "Available ✓"
        else:
            return "No Access ⚠"
    except Exception as e:
        return f"Error: {e}"

def _list_devservers(namespace: str) -> List[Dict]:
    """List DevServers in user namespace."""
    try:
        result = _run_kubectl("get", "devservers", "-o", "json", namespace=namespace)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('items', [])
    except Exception:
        pass
    return []

def _list_flavors(namespace: str) -> List[Dict]:
    """List DevServerFlavors in user namespace."""
    try:
        result = _run_kubectl("get", "devserverflavors", "-o", "json", namespace=namespace)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('items', [])
    except Exception:
        pass
    return []

def _get_devserver(name: str, namespace: str) -> Optional[Dict]:
    """Get specific DevServer by name."""
    try:
        result = _run_kubectl("get", "devserver", name, "-o", "json", namespace=namespace)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None

def _wait_for_devserver_ready(name: str, namespace: str, timeout: int = 120) -> bool:
    """Wait for DevServer to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        devserver = _get_devserver(name, namespace)
        if devserver and devserver.get('status', {}).get('ready'):
            return True
        time.sleep(2)
    return False

# DevServer management commands

@cli.command()
@click.argument('name')
@click.option('--flavor', required=True, help='DevServerFlavor to use (e.g., cpu-small)')
@click.option('--image', default='ubuntu:22.04', help='Container image to use')
@click.option('--home-size', default='10Gi', help='Size of persistent home directory')
@click.option('--wait', is_flag=True, help='Wait for DevServer to be ready')
@click.pass_context
def create(ctx: click.Context, name: str, flavor: str, image: str, home_size: str, wait: bool) -> None:
    """Create a new development server."""
    username = ctx.obj['username']
    namespace = ctx.obj['namespace']
    
    console.print(f"[bold]Creating DevServer '{name}'[/bold]")
    console.print(f"Flavor: {flavor}")
    console.print(f"Image: {image}")
    console.print(f"Namespace: {namespace}")
    console.print()
    
    # Check if DevServer already exists
    if _get_devserver(name, namespace):
        console.print(f"[red]❌ DevServer '{name}' already exists in namespace '{namespace}'[/red]")
        console.print("Use a different name or delete the existing one first.")
        return
    
    # Check if flavor exists
    flavors = _list_flavors(namespace)
    if not any(f['metadata']['name'] == flavor for f in flavors):
        console.print(f"[red]❌ DevServerFlavor '{flavor}' not found[/red]")
        console.print("Available flavors:")
        for f in flavors:
            console.print(f"  • {f['metadata']['name']}")
        if not flavors:
            console.print("  (No flavors available - contact administrator)")
        return
    
    # Create DevServer YAML
    devserver_yaml = f"""
apiVersion: apps.devservers.io/v1
kind: DevServer
metadata:
  name: {name}
  namespace: {namespace}
spec:
  owner: {username}@company.com
  flavor: {flavor}
  image: {image}
  mode: standalone
  persistentHomeSize: {home_size}
  enableSSH: true
  lifecycle:
    idleTimeout: 3600
    autoShutdown: true
"""
    
    # Apply DevServer
    try:
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=devserver_yaml,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            console.print(f"[green]✅ DevServer '{name}' created successfully[/green]")
            
            if wait:
                console.print("⏳ Waiting for DevServer to be ready...")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Starting development server...", total=None)
                    
                    if _wait_for_devserver_ready(name, namespace):
                        progress.update(task, description="[green]DevServer is ready!")
                        console.print(f"\n[green]🎉 DevServer '{name}' is ready for use![/green]")
                        console.print(f"Access it with: [cyan]devctl exec {name} -- bash[/cyan]")
                    else:
                        progress.update(task, description="[red]Timeout waiting for DevServer")
                        console.print("\n[yellow]⚠ DevServer created but not ready within timeout[/yellow]")
                        console.print(f"Check status with: [cyan]devctl describe {name}[/cyan]")
        else:
            console.print(f"[red]❌ Failed to create DevServer: {result.stderr}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Error creating DevServer: {e}[/red]")

@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List your development servers."""
    namespace = ctx.obj['namespace']
    
    devservers = _list_devservers(namespace)
    
    if not devservers:
        console.print(f"[yellow]No DevServers found in namespace '{namespace}'[/yellow]")
        console.print("Create one with: [cyan]devctl create <name> --flavor <flavor>[/cyan]")
        return
    
    console.print(f"[bold]DevServers in {namespace}[/bold]")
    console.print()
    
    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Flavor", style="blue")
    table.add_column("Image", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Ready", style="green")
    table.add_column("Age", style="yellow")
    
    for ds in devservers:
        created = ds['metadata'].get('creationTimestamp', '')
        age = _calculate_age(created) if created else 'Unknown'
        ready_status = "Yes" if ds.get('status', {}).get('ready') else "No"
        
        table.add_row(
            ds['metadata']['name'],
            ds['spec'].get('flavor', 'N/A'),
            ds['spec'].get('image', 'N/A'),
            ds.get('status', {}).get('phase', 'Unknown'),
            ready_status,
            age
        )
    
    console.print(table)

@cli.command()
@click.argument('name')
@click.pass_context
def describe(ctx: click.Context, name: str) -> None:
    """Show detailed information about a DevServer."""
    namespace = ctx.obj['namespace']
    
    devserver = _get_devserver(name, namespace)
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
    try:
        result = _run_kubectl("get", "pods,pvc,svc,deployment", "-l", f"app=devserver,devserver={name}", namespace=namespace)
        if result.returncode == 0 and result.stdout.strip():
            console.print(result.stdout)
        else:
            console.print("No related resources found")
    except Exception as e:
        console.print(f"Error fetching resources: {e}")

@cli.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete(ctx: click.Context, name: str, force: bool) -> None:
    """Delete a development server."""
    namespace = ctx.obj['namespace']
    
    if not _get_devserver(name, namespace):
        console.print(f"[red]❌ DevServer '{name}' not found in namespace '{namespace}'[/red]")
        return
    
    if not force:
        console.print(f"[yellow]⚠ This will delete DevServer '{name}' and all its data![/yellow]")
        if not click.confirm("Are you sure you want to continue?"):
            console.print("Deletion cancelled.")
            return
    
    console.print(f"[bold]Deleting DevServer '{name}'[/bold]")
    
    try:
        result = _run_kubectl("delete", "devserver", name, namespace=namespace)
        if result.returncode == 0:
            console.print(f"[green]✅ DevServer '{name}' deletion initiated[/green]")
            console.print("Resources will be cleaned up automatically by the operator.")
        else:
            console.print(f"[red]❌ Failed to delete DevServer: {result.stderr}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error deleting DevServer: {e}[/red]")

@cli.command()
@click.argument('name')
@click.argument('command', nargs=-1)
@click.option('--shell', default='bash', help='Shell to use (default: bash)')
@click.pass_context
def exec(ctx: click.Context, name: str, command: tuple, shell: str) -> None:
    """Execute commands in a development server."""
    namespace = ctx.obj['namespace']
    
    devserver = _get_devserver(name, namespace)
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

@cli.command()
@click.pass_context
def flavors(ctx: click.Context) -> None:
    """List available DevServerFlavors."""
    namespace = ctx.obj['namespace']
    
    flavors = _list_flavors(namespace)
    
    if not flavors:
        console.print(f"[yellow]No DevServerFlavors found in namespace '{namespace}'[/yellow]")
        console.print("Contact your administrator to create resource flavors.")
        return
    
    console.print(f"[bold]Available DevServerFlavors in {namespace}[/bold]")
    console.print()
    
    for flavor in flavors:
        name = flavor['metadata']['name']
        spec = flavor['spec']
        resources = spec.get('resources', {})
        requests = resources.get('requests', {})
        limits = resources.get('limits', {})
        
        # Create a panel for each flavor
        content = []
        content.append(f"[cyan]CPU Request:[/cyan] {requests.get('cpu', 'N/A')}")
        content.append(f"[cyan]Memory Request:[/cyan] {requests.get('memory', 'N/A')}")
        if limits.get('cpu'):
            content.append(f"[cyan]CPU Limit:[/cyan] {limits['cpu']}")
        if limits.get('memory'):
            content.append(f"[cyan]Memory Limit:[/cyan] {limits['memory']}")
        if limits.get('nvidia.com/gpu'):
            content.append(f"[cyan]GPU:[/cyan] {limits['nvidia.com/gpu']}")
        
        if spec.get('nodeSelector'):
            content.append(f"[cyan]Node Selector:[/cyan] {spec['nodeSelector']}")
        
        panel = Panel(
            "\n".join(content),
            title=f"[bold]{name}[/bold]",
            border_style="blue"
        )
        console.print(panel)

def _calculate_age(created_timestamp: str) -> str:
    """Calculate age from Kubernetes timestamp."""
    try:
        from datetime import datetime
        # Parse ISO timestamp
        created = datetime.fromisoformat(created_timestamp.replace('Z', '+00:00'))
        now = datetime.now(created.tzinfo)
        diff = now - created
        
        if diff.days > 0:
            return f"{diff.days}d"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m"
        else:
            return f"{diff.seconds}s"
    except Exception:
        return "Unknown"

if __name__ == '__main__':
    cli()