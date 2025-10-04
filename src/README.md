# Source Code

This directory contains the Python source code for the DevServer project.

## Architecture

The project is divided into two main components:

-   [`operator/`](./operator/README.md): A Kubernetes operator responsible for managing the lifecycle of `DevServer` custom resources.
-   [`cli/`](./cli/README.md): A command-line interface (`devctl`) for users to interact with and manage their DevServers.

### Core Components

```
devserver/
├── src/
│   └── devserver/
│       ├── operator/            # Kubernetes operator implementation
│       │   ├── operator.py      # Main operator logic with Kopf handlers
│       │   └── resources/       # Builders for Kubernetes objects
│       └── cli/                 # Command-line interface
│           ├── main.py          # CLI entry point with click
│           └── handlers.py      # CLI command implementations
├── crds/                        # Custom Resource Definitions
└── tests/                       # Test suite
```

For more detailed information, please see the `README.md` files within each component's directory.
