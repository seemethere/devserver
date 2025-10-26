# Source Code

This directory contains the Python source code for the DevServer project. The main package is [`devservers/`](./devservers/README.md), which includes the Kubernetes operator, the CLI, and the Custom Resource Definitions (CRDs).

## Architecture

The project is organized into several key components within the `devservers` package:

-   [`operator/`](./devservers/operator/README.md): A Kubernetes operator responsible for managing the lifecycle of `DevServer` custom resources.
-   [`cli/`](./devservers/cli/README.md): A command-line interface (`devctl`) for users to interact with and manage their DevServers.
-   `crds/`: Contains the Python models for the `DevServer` CRD. These models are used by the operator and CLI to interact with the custom resources.
-   `utils/`: Shared utility functions used across both the operator and the CLI.

### Core Components

```
src/
└── devservers/
    ├── operator/                  # Kubernetes operator implementation
    │   ├── devserver/             # Logic for the DevServer CRD
    │   │   ├── handler.py         # Kopf handlers for DevServer
    │   │   ├── reconciler.py      # Core reconciliation logic
    │   │   └── resources/         # Builders for Kubernetes objects
    │   ├── devserveruser/         # Logic for the DevServerUser CRD
    │   │   ├── handler.py         # Kopf handlers for DevServerUser
    │   │   └── reconciler.py      # Core reconciliation logic
    │   └── operator.py            # Main operator entrypoint
    ├── cli/                       # Command-line interface
    │   ├── main.py                # CLI entry point with click
    │   └── handlers/              # Implementations for each CLI command
    ├── crds/                      # Python models for CRDs
    └── utils/                     # Shared utility functions
```
