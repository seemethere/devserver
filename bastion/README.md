# Bastion Host

The bastion host is a secure SSH gateway that provides access to the Kubernetes cluster. It includes a user-provisioning sidecar that automatically creates a dedicated namespace and RBAC permissions for each new user who connects via SSH.

## Features

- **Automated User Provisioning**: On a user's first SSH connection, a sidecar controller creates a `dev-<username>` namespace, a service account, and a role binding with permissions to manage `DevServer` resources.
- **Secure by Default**: Users are confined to their own namespaces, preventing them from accessing or interfering with other users' resources.
- **Pre-configured Environment**: The bastion container comes with the `devctl` CLI and a configured `kubeconfig` file, providing a ready-to-use environment out-of-the-box.

## Getting Started

The bastion is typically deployed as part of the platform's main `Makefile`. However, you can also deploy it manually.

**Build the Bastion Image:**

```bash
make build
```

**Deploy to Your Cluster:**

```bash
make deploy
```

The deployment script will automatically detect your cluster type (`k3d`, `kind`, `EKS`, etc.) and configure the deployment accordingly. For local clusters, it will load the Docker image directly into the cluster.

## SSH Access

The `make deploy` command will generate a demo SSH keypair in the `.demo-keys/` directory.

**For Local Clusters (`k3d`, `kind`):**

The bastion service is exposed via a port-forward.

```bash
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222
```

**For Cloud Clusters (EKS):**

The bastion service is exposed via a LoadBalancer. You can get the hostname with:

```bash
kubectl get service bastion -n devserver-bastion -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

Then connect via SSH:

```bash
ssh -i .demo-keys/bastion_demo testuser@<loadbalancer-hostname>
```

### Using Your Own SSH Key

To use your own SSH key, replace the `BASTION_TEST_SSH_KEY` environment variable in `bastion/k8s/deployment.yaml` with your public key.

## Environment-Specific Setup

### k3d

For the best experience with `k3d`, create your cluster with a port-mapping for the SSH service:

```bash
k3d cluster create devserver --port "8022:22@loadbalancer"
```

This will allow you to access the bastion directly on `localhost:8022` without needing `kubectl port-forward`.
