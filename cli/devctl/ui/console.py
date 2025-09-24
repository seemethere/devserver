"""Console utilities and formatting."""

from datetime import datetime
from typing import Dict, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def calculate_age(created_timestamp: str) -> str:
    """Calculate age from Kubernetes timestamp."""
    try:
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


def create_devserver_table(devservers: List[Dict]) -> Table:
    """Create a table for displaying DevServers."""
    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Flavor", style="blue")
    table.add_column("Image", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Ready", style="green")
    table.add_column("Age", style="yellow")
    
    for ds in devservers:
        created = ds['metadata'].get('creationTimestamp', '')
        age = calculate_age(created) if created else 'Unknown'
        ready_status = "Yes" if ds.get('status', {}).get('ready') else "No"
        
        table.add_row(
            ds['metadata']['name'],
            ds['spec'].get('flavor', 'N/A'),
            ds['spec'].get('image', 'N/A'),
            ds.get('status', {}).get('phase', 'Unknown'),
            ready_status,
            age
        )
    
    return table


def create_flavor_panels(flavors: List[Dict]) -> List[Panel]:
    """Create panels for displaying DevServerFlavors."""
    panels = []
    
    for flavor in flavors:
        name = flavor['metadata']['name']
        spec = flavor['spec']
        resources = spec.get('resources', {})
        requests = resources.get('requests', {})
        limits = resources.get('limits', {})
        
        # Create content for the panel
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
        panels.append(panel)
    
    return panels


def create_progress_spinner(description: str = "Processing..."):
    """Create a progress spinner for long operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    )
