# DevServer Operator

A Kubernetes-native operator for managing development servers, particularly designed for PyTorch and ML development workloads. This project provides both a Kubernetes operator and a CLI tool for creating, managing, and accessing development environments.

> **📍 Current Status**: This project is under active development.

## 🚀 Features

- **Kubernetes-Native**: Built using the [Kopf](https://kopf.readthedocs.io/) framework for Python.
- **Resource Templates**: `DevServerFlavor` CRDs define t-shirt sized resource configurations.
- **User Management**: `DevServerUser` CRDs for managing user access and SSH keys.
- **Lifecycle Management**: Automatic shutdown and expiration.
- **CLI Tool**: `devctl` for easy interaction with DevServers.
- **SSH Agent Forwarding**: Seamlessly forward your SSH agent to the DevServer.
- **YAML Configuration**: Configure `devctl` using `~/.config/devctl/config.yaml`.
- **Test-Driven Development**: Comprehensive test suite using `pytest` and `k3d`.

## 📋 Prerequisites

- Python 3.9+
- Docker
- [uv](https://github.com/astral-sh/uv)
- [k3d](https://k3d.io/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- A Kubernetes cluster (local k3d or remote)

## 🏃 Quick Start

### 1. Set Up Local Development Environment

```bash
# Create a local k3d cluster
k3d cluster create devserver-cluster
```

### 2. Deploy the CRDs and Flavors

```bash
# Apply the Custom Resource Definitions and Flavors
make install-crds
```

### 3. Run the Operator

```bash
# Start the operator in development mode
make run
```

### 4. Use the CLI

In a new terminal:

```bash
# Create a development server
uv run devctl create --name mydev --flavor cpu-small

# List your servers
uv run devctl list

# Add a user
uv run devctl user add --name test-user --public-key-file ~/.ssh/id_rsa.pub

# Create a server with GPU support (see dev/eks/README.md for setup)
uv run devctl create --name my-gpu-dev --flavor gpu-small --image fedora:latest

# Delete a server
uv run devctl delete mydev
```

## 📚 Documentation

For more detailed documentation, please see the following `README.md` files:

-   **[Source Code & Architecture](./src/README.md)**
-   **[Operator & CRDs](./src/devservers/operator/README.md)**
-   **[CLI Reference](./src/devservers/cli/README.md)**
-   **[Testing](./tests/README.md)**

## 🤝 Contributing

Contributions are welcome! Please see the `PROJECT.md` for the development plan.

Before submitting a pull request, please run the pre-commit checks to ensure your changes adhere to the project's coding standards:

```bash
make pre-commit
```

1.  Fork the repository.
2.  Create a feature branch.
3.  Make your changes with tests.
4.  Run the test suite: `make test`
5.  Submit a pull request.

## 📄 License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

## Remote Development

For a faster development loop, you can run the operator inside your Kubernetes cluster and sync your local changes to it.

### Prerequisites

1.  **Install `kubectl-rsync`:** This `kubectl` plugin is required for syncing files. You can install it via `krew`:
    ```bash
    kubectl krew install rsync
    ```

2.  **Docker Image:** The remote development setup uses the `ghcr.io/seemethere/devservers:main` image, which is built from the `main` branch.

### Usage

Run the following command to bootstrap the remote development environment:

```bash
make dev-bootstrap
```

This will:
1.  Create a namespace `default` if it doesn't exist (you can override with `-n <namespace>`).
2.  Set up the necessary RBAC (ServiceAccount, Role, RoleBinding).
3.  Create a Deployment for the operator.
4.  Sync your local `src/` directory to the pod.
5.  Restart the `kopf` process in the pod to apply changes.

You can then view the operator logs with:
```bash
kubectl logs -f -n <namespace> -l app=devserver-operator-dev
```

Any subsequent changes you make locally can be synced by running `make dev-bootstrap` again.
