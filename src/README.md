# Source Code

This directory contains the Python source code for the DevServer project.

## Architecture

The project is divided into two main components:

-   [`operator/`](./operator/README.md): A Kubernetes operator responsible for managing the lifecycle of `DevServer` custom resources.
-   [`cli/`](./cli/README.md): A command-line interface (`devctl`) for users to interact with and manage their DevServers.

### Core Components

```
src/
└── devserver/
    ├── operator/                  # Kubernetes operator implementation
    │   ├── operator.py            # Main operator logic with Kopf handlers
    │   ├── reconciler.py          # Core reconciliation logic for DevServers
    │   ├── user_reconciler.py     # Reconciliation logic for DevServerUsers
    │   └── resources/             # Builders for Kubernetes objects
    └── cli/                       # Command-line interface
        ├── main.py                # CLI entry point with click
        └── handlers/              # Implementations for each CLI command
```

For more detailed information, please see the `README.md` files within each component's directory.
