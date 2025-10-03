# Helper Docker Images

This directory contains `Dockerfile` definitions for various helper images used by the devserver operator.

These images are typically built and pushed to a container registry, then referenced by the operator when it creates Kubernetes resources.

## Images

-   `sshd/`: Contains the `Dockerfile` for building a multi-architecture, fully static `sshd` binary. This is used by an `initContainer` to provide a consistent SSH server to all devserver environments.
