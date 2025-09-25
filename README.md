# PyTorch Development Server Platform

A Kubernetes-based platform for managing GPU-enabled development environments, accessible via a secure SSH bastion and a user-friendly CLI.

## Core Features

- **Secure, Multi-Tenant Environments**: Automatic namespace and RBAC provisioning for each user on first SSH connection.
- **Simplified Dev Environment Management**: A simple `devctl` CLI for creating, managing, and accessing development servers without needing `kubectl`.
- **Customizable Server Configurations**: Use `DevServerFlavor` custom resources to define and reuse different server sizes and resource allocations (e.g., `cpu-small`, `gpu-large`).
- **Seamless Local and Cloud Experience**: Works with local clusters like `k3d` and `kind` out-of-the-box, as well as cloud-based clusters like EKS.

## Quick Start

This will deploy the `devserver-operator`, a secure SSH bastion, and default `DevServerFlavor`s to your Kubernetes cluster.

**Prerequisites:**

- A running Kubernetes cluster (`k3d`, `kind`, EKS, etc.)
- `kubectl` configured to connect to your cluster
- Docker (for building the bastion image)

**Deployment:**

```bash
# 1. Deploy the DevServer Operator and default flavors
make -C devserver-operator deploy

# 2. Deploy the Bastion
make -C bastion build
make -C bastion deploy
```

## Core Workflow

Once the platform is deployed, you can create and access your development environments.

```bash
# 1. SSH into the bastion. This will auto-provision your namespace.
# The default password for the test user is 'testpassword'.
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222

# 2. Inside the bastion, create a new dev server
devctl create my-dev-server --flavor cpu-small

# 3. Connect to your new server
devctl ssh my-dev-server

# 4. When you're done, clean up your resources
devctl delete my-dev-server
```

## Project Structure

For more detailed information, see the `README.md` files in the respective directories:

- `devserver-operator/`: Contains the Go-based Kubernetes operator and `DevServer` CRDs.
- `bastion/`: The secure SSH bastion and user-provisioning sidecar.
- `cli/`: The `devctl` command-line interface.
