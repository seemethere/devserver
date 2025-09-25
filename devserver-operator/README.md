# DevServer Operator

This directory contains the Go-based Kubernetes operator for managing `DevServer` and `DevServerFlavor` custom resources.

## Overview

The DevServer Operator is built with the Kubebuilder framework and is responsible for reconciling `DevServer` resources. When a user creates a `DevServer`, the operator will provision the necessary Kubernetes resources to create a development environment, including:

- A **Deployment** to run the development container.
- A **PersistentVolumeClaim** for the user's home directory (`/home/dev`).
- A **Service** to provide SSH access to the container.

## Custom Resource Definitions (CRDs)

### DevServer

A `DevServer` represents a single development environment. Key fields in the `spec` include:

- `flavor`: The name of a `DevServerFlavor` to use for resource allocation.
- `image`: The container image to use for the development environment.
- `storage`: The size of the persistent volume for the home directory.

### DevServerFlavor

A `DevServerFlavor` is a reusable template for `DevServer` resources. It defines the CPU and memory requests and limits for a development environment. `DevServerFlavor`s are cluster-scoped, so they can be used by any user in any namespace.

The operator deployment automatically creates three default flavors: `cpu-small`, `cpu-medium`, and `cpu-large`.

## Getting Started

The operator is typically deployed as part of the platform's main `Makefile`. However, you can also deploy it manually.

```bash
make deploy
```

This will:
1. Build the operator container image.
2. Load the image into your local cluster (if using `k3d` or `kind`).
3. Install the `DevServer` and `DevServerFlavor` CRDs.
4. Deploy the operator to the `devserver-operator-system` namespace.
5. Create the default `DevServerFlavor`s.

### Local Development

To run the operator locally for development and debugging, use the `run` target:

```bash
make run
```

This will run the operator on your local machine, using your local `kubeconfig` to connect to the cluster.

## Testing

The operator includes both unit and end-to-end tests.

**Unit Tests:**

```bash
make unit-test
```

**End-to-End Tests:**

The end-to-end tests use a `kind` cluster to test the full reconciliation lifecycle.

```bash
make test-e2e
```

