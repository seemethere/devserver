# DevCtl CLI - Phase 1

Simple CLI for the PyTorch Development Server Platform bastion server.

## Installation

The CLI is automatically installed in the bastion container. For local development:

```bash
cd cli/
pip install -e .
```

## Phase 1 Commands

### `devctl status`
Shows current environment status including:
- Username and assigned namespace
- Bastion version information  
- Kubernetes connectivity status
- Environment detection (bastion vs local)

### `devctl info`
Lists available commands and shows what's coming in Phase 2.

### `devctl test-k8s`
Tests basic Kubernetes connectivity and permissions:
- Cluster info retrieval
- Namespace listing
- User namespace access
- Basic pod operations

### `devctl --help`
Shows detailed help for all commands.

## Phase 1 Environment

When running in the bastion, the CLI automatically:
- Detects it's in a bastion container (via `/.bastion-marker`)
- Uses the current user's assigned namespace (`dev-{username}`)
- Connects to Kubernetes via service account
- Shows Phase 1 limitations and what's coming next

## Example Output

```bash
$ devctl status
DevCtl Phase 1 Status

┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting         ┃ Value                     ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Username        │ testuser                  │
│ Assigned        │ dev-testuser              │
│ Namespace       │                           │
│ Bastion Version │ 0.1.0-phase1              │
│ Environment     │ Bastion Container ✓       │
│ Kubernetes      │ Connected ✓               │
└─────────────────┴───────────────────────────┘

Phase 1 Limitations:
• No server creation yet (coming in Phase 2)
• No CRDs or operator (coming in Phase 2)  
• This is just a bastion infrastructure test
```

## Development

For CLI development:

```bash
# Install in development mode
pip install -e .

# Run tests (when added)
pytest

# Format code (when configured)
black devctl/
```

## Dependencies

- `click` - Command line interface framework
- `rich` - Rich text and beautiful formatting

Minimal dependencies for Phase 1 - more will be added as functionality grows.
