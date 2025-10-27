# DevServer Source Code

This directory contains the core source code for the DevServer project, organized into the following components:

-   [`cli/`](./cli/README.md): The `devctl` command-line interface for managing DevServers.
-   [`crds/`](./crds/): Python models for the `DevServer` Custom Resource Definition (CRD).
-   [`operator/`](./operator/README.md): The Kubernetes operator that manages the lifecycle of DevServer resources.
-   [`utils/`](./utils/): Shared utility functions used by both the operator and the CLI.

For more detailed information on each component, please refer to the `README.md` files within their respective directories.
