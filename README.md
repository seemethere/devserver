# DevServer Operator

A Kubernetes-native operator for managing development servers, particularly designed for PyTorch and ML development workloads. This project provides both a Kubernetes operator and a CLI tool for creating, managing, and accessing development environments.

> **📍 Current Status**: This project is under active development. Core functionality is implemented (✅) while advanced features are in progress (🚧). See feature status indicators below.

## 🚀 Features

- **Kubernetes-Native**: Built using the Kopf framework for Python ✅
- **Resource Templates**: DevServerFlavor CRDs define t-shirt sized resource configurations ✅
- **Lifecycle Management**: Automatic shutdown, expiration, and scaling capabilities 🚧 *In Progress*
- **Distributed Training**: Support for both standalone and distributed ML training scenarios 🚧 *In Progress*
- **Test-Driven Development**: Comprehensive test suite using pytest and k3d ✅
- **Cloud-Agnostic**: Pluggable provider architecture for different cloud platforms 🚧 *In Progress*
- **Unified Codebase**: Single repository for both operator and CLI components ✅

## 📋 Prerequisites

- Python 3.8+
- Docker
- k3d (for local development)
- kubectl
- A Kubernetes cluster (local k3d or remote)

## 🏃 Quick Start

### 1. Set Up Local Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd devserver2

# Create a local k3d cluster
make up

# Install Python dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Deploy the CRDs

```bash
# Apply the Custom Resource Definitions
kubectl apply -f crds/
```

### 3. Create a DevServerFlavor

```bash
# Create a sample flavor for development
kubectl apply -f - <<EOF
apiVersion: devserver.io/v1
kind: DevServerFlavor
metadata:
  name: cpu-small
spec:
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2"
      memory: "4Gi"
  nodeSelector:
    kubernetes.io/arch: amd64
EOF
```

### 4. Run the Operator

```bash
# Start the operator (in development mode)
python -m src.devserver_operator.operator
```

### 5. Use the CLI

```bash
# Create a development server
devctl create mydev --flavor cpu-small

# List your servers
devctl list

# Get connection details
devctl show mydev

# Delete a server
devctl delete mydev
```

## 🏗️ Architecture

### Core Components

```
devserver2/
├── src/
│   ├── devserver_operator/    # Kubernetes operator implementation
│   │   └── operator.py        # Main operator logic with Kopf handlers
│   └── cli/                   # Command-line interface
│       ├── main.py           # CLI entry point with argparse
│       └── handlers.py       # CLI command implementations
├── crds/                     # Custom Resource Definitions
│   ├── devserver.io_devservers.yaml
│   └── devserver.io_devserverflavors.yaml
└── tests/                    # Test suite
    ├── test_operator.py      # Integration tests for operator
    ├── test_cli.py          # CLI tests
    └── test_crds.py         # CRD validation tests
```

### Custom Resources

#### DevServer
Represents an individual development server instance:

```yaml
apiVersion: devserver.io/v1
kind: DevServer
metadata:
  name: my-dev-server
  namespace: default
spec:
  owner: user@example.com
  flavor: cpu-small
  image: ubuntu:22.04
  mode: standalone  # or distributed
  enableSSH: true
  lifecycle:
    idleTimeout: 3600
    autoShutdown: true
```

#### DevServerFlavor
Defines resource templates and configurations:

```yaml
apiVersion: devserver.io/v1
kind: DevServerFlavor
metadata:
  name: gpu-large
spec:
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
      nvidia.com/gpu: "1"
    limits:
      cpu: "8"
      memory: "32Gi"
      nvidia.com/gpu: "1"
  nodeSelector:
    node-type: gpu-node
```

## 🧪 Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
make test

# Run specific test categories
python -m pytest tests/test_operator.py -v
python -m pytest tests/test_cli.py -v
python -m pytest tests/test_crds.py -v
```

### Local Development Workflow

1. **Start k3d cluster**: `make up`
2. **Apply CRDs**: `kubectl apply -f crds/`
3. **Run operator**: `python -m src.devserver_operator.operator`
4. **Test CLI**: `devctl create test-server --flavor cpu-small`
5. **Run tests**: `make test`
6. **Clean up**: `make down`

### Project Commands

```bash
# Cluster management
make up          # Create k3d cluster
make down        # Delete k3d cluster
make kubeconfig  # Get kubeconfig for cluster

# Development
make test        # Run test suite
```

## 📚 CLI Reference

### Basic Commands

```bash
# Server Management
devctl create <name> --flavor <flavor>     # Create a new dev server ✅
devctl list                                 # List all servers ✅
devctl show <name>                         # Show detailed server info 🚧
devctl delete <name>                       # Delete a server ✅

# Available Flavors
devctl flavors                             # List available resource flavors 🚧
```

### Advanced Usage

```bash
# Custom Images
devctl create mydev --flavor cpu-small --image pytorch/pytorch:latest  # 🚧 In Progress

# Distributed Training
devctl create distributed-job --flavor gpu-large --mode distributed     # 🚧 In Progress

# Lifecycle Management
devctl create temp-server --flavor cpu-small --time 2h                  # 🚧 In Progress
devctl extend mydev --time 4h                                           # 🚧 In Progress
```

## 🔧 Configuration

### Environment Variables

- `KUBECONFIG`: Path to Kubernetes configuration file
- `DEVSERVER_NAMESPACE`: Default namespace for DevServer resources (default: `default`)
- `DEVSERVER_IMAGE`: Default container image for dev servers

### Operator Configuration

The operator uses your local `kubeconfig` for authentication and cluster access. No additional configuration is required for local development.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with tests
4. Run the test suite: `make test`
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

### Test-Driven Development

This project follows TDD principles:

1. Write tests first for new functionality
2. Implement the minimal code to make tests pass
3. Refactor while keeping tests green
4. All changes must include appropriate tests

## 📄 License

[Add your license information here]

## 🆘 Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: Additional docs in the `/docs` directory
- **Development**: See the `PROJECT.md` file for detailed development plans

## 🛠️ Technology Stack

- **Language**: Python 3.8+
- **Operator Framework**: [Kopf](https://kopf.readthedocs.io/)
- **CLI Framework**: argparse (Python standard library)
- **Testing**: pytest with k3d for Kubernetes integration tests
- **Kubernetes Client**: Official Python Kubernetes client
- **Container Runtime**: Docker
- **Local Development**: k3d for lightweight Kubernetes clusters
