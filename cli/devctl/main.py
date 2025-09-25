#!/usr/bin/env python3
"""DevCtl Phase 3 CLI - Complete DevServer Management."""

import click

from .config.settings import VERSION, get_username, get_user_namespace

# Import commands
from .commands.status import status
from .commands.info import info
from .commands.test import test_k8s
from .commands.devserver import create, list, describe, delete, exec, ssh, flavors, extend, update


@click.group()
@click.version_option(version=VERSION)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """DevCtl Phase 3 - Complete DevServer Management
    
    Phase 3 provides complete development server lifecycle management with
    DevServer CRDs, automatic resource provisioning, and container access.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    # Set user context
    ctx.obj['username'] = get_username()
    ctx.obj['namespace'] = get_user_namespace()


# Register commands
cli.add_command(status)
cli.add_command(info)
cli.add_command(test_k8s)
cli.add_command(create)
cli.add_command(list)
cli.add_command(describe)
cli.add_command(delete)
cli.add_command(exec)
cli.add_command(ssh)
cli.add_command(flavors)
cli.add_command(extend)
cli.add_command(update)


if __name__ == '__main__':
    cli()
