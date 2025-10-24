# Source Code

This directory contains the Python source code for the DevServer project.

## Architecture

The project is divided into two main components:

-   [`operator/`](./operator/README.md): A Kubernetes operator responsible for managing the lifecycle of `DevServer` custom resources.
-   [`cli/`](./cli/README.md): A command-line interface (`devctl`) for users to interact with and manage their DevServers.

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
    └── cli/                       # Command-line interface
        ├── main.py                # CLI entry point with click
        └── handlers/              # Implementations for each CLI command
```

For more detailed information, please see the `README.md` files within each component's directory.
