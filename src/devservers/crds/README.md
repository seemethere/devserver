# Custom Resource Definition (CRD) Clients

This module provides high-level, object-oriented clients for interacting with the `devserver.io` custom resources in a Kubernetes cluster. These classes act as a Pythonic SDK, abstracting away the raw Kubernetes API calls into a more intuitive model.

## `BaseCustomResource`

This is the foundation for all CRD clients. It provides a generic, reusable implementation of all standard CRUD (Create, Read, Update, Delete) operations, and handles the distinction between namespaced and cluster-scoped resources automatically.

## `DevServer` Client

The `DevServer` class inherits from `BaseCustomResource` and is the primary interface for managing `DevServer` custom resources.

### Example Usage

Below are examples of how to use the `DevServer` client to manage resources programmatically.

#### Prerequisites

The client will automatically attempt to load your Kubernetes configuration from a standard `kubeconfig` file or from the in-cluster service account environment.

If the configuration cannot be loaded, the client will raise a `KubeConfigError` with a helpful message.

#### Creating a DevServer

To create a new `DevServer`, you define its `ObjectMeta` and `spec`, then call the `create` classmethod. It's best practice to wrap client calls in a `try...except` block to handle potential configuration or API errors.

```python
from devservers.crds.devserver import DevServer
from devservers.crds.base import ObjectMeta
from devservers.crds.errors import KubeConfigError

# 1. Define the metadata and spec
metadata = ObjectMeta(name="my-test-server", namespace="default")
spec = {
    "flavor": "cpu-small",
    "image": "ubuntu:22.04",
    "ssh": {"publicKey": "ssh-rsa AAAA..."},
    "lifecycle": {"timeToLive": "1h"},
}

# 2. Create the resource on the cluster
try:
    devserver = DevServer.create(metadata=metadata, spec=spec)
    print(f"Successfully created '{devserver.metadata.name}' with status: {devserver.status}")
except KubeConfigError as e:
    print(f"Error: {e}")
except Exception as e:
    # Handle other potential Kubernetes API errors
    print(f"An API error occurred: {e}")

```

#### Getting and Listing DevServers

You can retrieve a single `DevServer` by name or list all servers in a namespace.

```python
# Get a specific DevServer by name
server = DevServer.get(name="my-test-server", namespace="default")
print(f"Found server: {server.metadata.name}")

# List all DevServers in the 'default' namespace
servers = DevServer.list(namespace="default")
print("Available servers:")
for s in servers:
    print(f"- {s.metadata.name}")
```

#### Updating a DevServer

You can modify a `DevServer`'s `spec` and apply the changes with the `update()` or `patch()` methods.

```python
# Get the object first
server = DevServer.get(name="my-test-server", namespace="default")

# Option 1: Replace the entire object with a full update
print(f"Old image: {server.spec.get('image')}")
server.spec["image"] = "fedora:latest"
server.update()
print(f"New image: {server.spec.get('image')}")


# Option 2: Patch a single field
server.patch({"spec": {"lifecycle": {"timeToLive": "8h"}}})
print(f"New TTL: {server.spec['lifecycle']['timeToLive']}")

```

#### Deleting a DevServer

To clean up a resource, simply call the `delete()` method.

```python
server = DevServer.get(name="my-test-server", namespace="default")
server.delete()
print(f"DevServer '{server.metadata.name}' deleted.")
```

#### Refreshing Local State

If the resource is modified on the cluster by another process (e.g., the operator updates its status), you can sync your local Python object with the `refresh()` method.

```python
server = DevServer.get(name="my-test-server", namespace="default")
# ...some time passes, and the operator changes the status...
server.refresh()
print(f"Current status phase is: {server.status.get('phase')}")
```
