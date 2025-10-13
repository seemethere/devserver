# Helper Docker Images

This directory contains `Dockerfile` definitions for various helper images used by the devserver operator.

These images are typically built and pushed to a container registry, then referenced by the operator when it creates Kubernetes resources.

## Images

-   `base/`: The default, CPU-based development environment. It includes `build-essential`, `curl`, and `uv` on top of a base Ubuntu LTS image. This image is intended to be a general-purpose starting point for most development work.
-   `static-dependencies/`: Contains the `Dockerfile` for building multi-architecture, fully static binaries for `sshd`, `scp`, `sftp-server`, `ssh-keygen`, and `doas`. These are used by an `initContainer` to provide a consistent SSH server and privilege escalation tool to all devserver environments.
