# DevServer Operator

A Kubernetes-native operator for managing development servers, particularly designed for PyTorch and ML development workloads. This project provides both a Kubernetes operator and a CLI tool for creating, managing, and accessing development environments.

> **📍 Current Status**: This project is under active development.

## 🚀 Features

- **Kubernetes-Native**: Built using the [Kopf](https://kopf.readthedocs.io/) framework for Python.
- **Resource Templates**: `DevServerFlavor` CRDs define t-shirt sized resource configurations.
- **Lifecycle Management**: Automatic shutdown and expiration.
- **CLI Tool**: `devctl` for easy interaction with DevServers.
- **Test-Driven Development**: Comprehensive test suite using `pytest` and `k3d`.

## 📋 Prerequisites

- Python 3.8+
- Docker
- [k3d](https://k3d.io/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- A Kubernetes cluster (local k3d or remote)

## 🏃 Quick Start

### 1. Set Up Local Development Environment

```bash
# Create a local k3d cluster
make up

# Install Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Deploy the CRDs and Flavors

```bash
# Apply the Custom Resource Definitions
kubectl apply -f crds/

# Create a sample flavor
kubectl apply -f examples/flavors/cpu-small.yaml
```

### 3. Run the Operator

```bash
# Start the operator in development mode
kopf run -m devserver.operator
```

### 4. Use the CLI

In a new terminal, activate the virtual environment: `source .venv/bin/activate`

```bash
# Create a development server
devctl create --name mydev --flavor cpu-small

# List your servers
devctl list

# Delete a server
devctl delete mydev
```

## 📚 Documentation

For more detailed documentation, please see the following `README.md` files:

-   **[Source Code & Architecture](./src/README.md)**
-   **[Operator & CRDs](./src/devserver/operator/README.md)**
-   **[CLI Reference](./src/devserver/cli/README.md)**
-   **[Testing](./tests/README.md)**

## 🤝 Contributing

Contributions are welcome! Please see the `PROJECT.md` for the development plan.

1.  Fork the repository.
2.  Create a feature branch.
3.  Make your changes with tests.
4.  Run the test suite: `make test`
5.  Submit a pull request.

## 📄 License

[Add your license information here]
