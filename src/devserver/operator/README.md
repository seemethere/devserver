# DevServer Operator

The DevServer Operator is a Kubernetes operator built with the [Kopf](https://kopf.readthedocs.io/) framework. It manages the lifecycle of `DevServer` and `DevServerFlavor` custom resources.

## Custom Resources

The operator introduces two Custom Resource Definitions (CRDs):

-   `DevServer`: Represents an individual development server instance.
-   `DevServerFlavor`: Defines reusable templates for `DevServer` configurations.

### DevServer

When a `DevServer` resource is created, the operator provisions the necessary Kubernetes objects to run the development environment, including:

-   A `StatefulSet` to manage the pod.
-   `Services` for network access (including SSH).
-   A `Secret` for SSH host keys.
-   A `ConfigMap` for the SSH daemon configuration.

**Example `DevServer`:**

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
  ssh:
    publicKey: "ssh-rsa AAAA..."
  lifecycle:
    timeToLive: "8h"
```

### DevServerFlavor

`DevServerFlavor` resources are used to define "t-shirt sizes" for DevServers, specifying resource requests, limits, and node selectors.

**Example `DevServerFlavor`:**

```yaml
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
    kubernetes.ioio/arch: amd64
```

## Lifecycle Management

The operator automatically handles the expiration of `DevServer` resources based on the `spec.lifecycle.timeToLive` field. When a DevServer expires, the operator deletes the corresponding `DevServer` resource, and Kubernetes garbage collection removes the associated objects.
