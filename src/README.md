# Source Code

This directory contains the Python source code for the DevServer project.

## `cli/`

This package contains the command-line interface (`devctl`) for interacting with DevServers.

- `main.py`: The main entry point for the CLI, using `argparse` to define and handle commands.
- `handlers.py`: Contains the functions that implement the logic for each CLI command (e.g., creating, listing, deleting DevServers) by communicating with the Kubernetes API.

## `devserver_operator/`

This package implements the Kubernetes operator for managing `DevServer` custom resources. It uses the [Kopf](https://kopf.readthedocs.io/) framework.

- `operator.py`: Contains the core operator logic, including handlers for `DevServer` resource lifecycle events (creation, deletion, etc.). When a `DevServer` is created, this operator creates a corresponding `Deployment`.
