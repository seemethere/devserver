# DevServer Operator

The DevServer Operator is a Kubernetes operator built with the [Kopf](https://kopf.readthedocs.io/) framework. It manages the lifecycle of `DevServer` and `DevServerFlavor` custom resources.

## Custom Resources

The operator introduces two Custom Resource Definitions (CRDs):

-   `DevServer`: Represents an individual development server instance.
-   `DevServerFlavor`: Defines reusable templates for `DevServer` configurations.
-   `DevServerUser`: Manages user access and public SSH keys.

### DevServer

When a `DevServer` resource is created, the operator provisions the necessary Kubernetes objects to run the development environment, including:

-   A `StatefulSet` to manage the pod.
-   `Services` for network access (including SSH).
-   A `Secret` for SSH host keys. The operator will automatically generate this secret if it doesn't exist.
-   A `ConfigMap` for the SSH daemon configuration.

### Container Startup Script

The operator injects a `startup.sh` script into the `DevServer` container. This script is responsible for:

-   **User Creation**: It creates a non-root `dev` user with UID/GID `1000`. The script is designed to be idempotent and work across different Linux distributions (e.g., Debian-based and Red Hat-based) by handling cases where a user or group with that ID already exists.
-   **Privilege Escalation**: The environment includes `doas` as a lightweight `sudo` replacement (if sudo is not already available). The `dev` user is configured with passwordless access to run commands as root (e.g., `doas apt-get update`).
-   **SSH Setup**: It configures the `dev` user's `authorized_keys` with the public key from the `DevServer` spec.
-   **SSHD Execution**: It starts the SSH daemon (`sshd`) as the final step, allowing the user to connect.

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

Tolerations can also be specified to allow DevServers to be scheduled on nodes with matching taints, such as GPU nodes.

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
    kubernetes.io/arch: amd64
  tolerations:
    - key: "nvidia.com/gpu"
      operator: "Exists"
      effect: "NoSchedule"
```

### DevServerUser

`DevServerUser` resources manage users and their associated permissions within the cluster. The operator sets up RBAC roles and resource quotas based on the spec. This CRD does not manage SSH keys directly; instead, SSH access is handled by the `devctl` CLI when creating or managing a `DevServer`.

**Example `DevServerUser`:**

```yaml
apiVersion: devserver.io/v1
kind: DevServerUser
metadata:
  name: test-user
spec:
  username: test-user
```

## Lifecycle Management

The operator automatically handles the expiration of `DevServer` resources based on the `spec.lifecycle.timeToLive` field. When a DevServer expires, the operator deletes the corresponding `DevServer` resource, and Kubernetes garbage collection removes the associated objects.
