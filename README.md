# PyTorch Development Server Platform - Phase 1

## Overview

This is **Phase 1** of the PyTorch Development Server Platform - focused on building and testing the bastion infrastructure. This phase proves the concept of centralized SSH access to a Kubernetes-based development platform.

## Phase 1 Goals ✅

- [x] Build bastion container with SSH server
- [x] Create simple `devctl` CLI for basic operations  
- [x] Deploy bastion to Kubernetes with HA
- [x] Setup LoadBalancer for SSH access
- [x] User environment and CLI integration
- [x] Basic Kubernetes connectivity testing
- [x] **Auto-generated SSH keys for testing**
- [x] **Environment-aware deployment (k3d, EKS, kind, minikube)**
- [x] **End-to-end authentication and CLI testing**
- [x] **Repeatable developer workflow**

## What's Working in Phase 1

- 🚀 **Bastion Server**: SSH-accessible container with proper user environment
- 🔧 **DevCtl CLI**: `devctl status`, `devctl info`, `devctl test-k8s` - fully functional
- ☸️ **Kubernetes Integration**: Service account, RBAC, namespace management
- 🔐 **Security**: SSH key authentication, auto-generated demo keys for testing
- 📊 **Monitoring**: Health checks, readiness probes, HA deployment (2 replicas)
- 🎯 **Environment Detection**: Auto-detects k3d, kind, minikube, EKS clusters
- 🔄 **Automated Deployment**: Smart scripts with cleanup, image loading, SSH key injection
- 🧪 **End-to-End Testing**: SSH authentication verification and CLI validation
- 🛠️ **Developer Experience**: One-command build, deploy, test workflow

## Quick Start

### Prerequisites

- Kubernetes cluster (EKS, kind, minikube, k3d, etc.)
- `kubectl` configured and connected
- Docker for building images
- SSH client for testing

### 1. Build and Deploy

The scripts automatically detect your cluster type (k3d, kind, minikube, EKS) and handle the differences:

```bash
# Build bastion container
./scripts/build-bastion.sh

# Deploy with environment auto-detection and SSH key generation
./scripts/deploy-bastion.sh

# Test full end-to-end SSH connectivity and CLI
./scripts/test-ssh.sh
```

**What happens automatically:**
- ✅ **SSH Keys**: Demo key pair auto-generated in `.demo-keys/`
- ✅ **Environment Detection**: Scripts detect your cluster type
- ✅ **Image Loading**: Local clusters get images loaded automatically
- ✅ **Deployment Patching**: `imagePullPolicy` adjusted for local vs. cloud
- ✅ **Cleanup**: Existing deployments cleaned up before new deployment
- ✅ **Testing**: Full SSH authentication and CLI validation

## Environment-Specific Setup

The scripts automatically detect your cluster type and provide appropriate instructions:

### k3d (Local Development)
```bash
# 1. Create k3d cluster (optional port mapping)
k3d cluster create devserver --port "8022:22@loadbalancer"

# 2. Build and deploy (auto-detects k3d, loads image automatically)
./scripts/build-bastion.sh
./scripts/deploy-bastion.sh

# 3. Test automatically uses port-forward for local clusters
./scripts/test-ssh.sh

# 4. Manual SSH access (using auto-generated demo key)
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222
```

### EKS (Production)
```bash
# 1. Ensure you have an ECR repository
aws ecr create-repository --repository-name devserver/bastion

# 2. Build and push to ECR
./scripts/build-bastion.sh
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com
docker tag devserver/bastion:phase1 <account>.dkr.ecr.us-west-2.amazonaws.com/devserver/bastion:phase1
docker push <account>.dkr.ecr.us-west-2.amazonaws.com/devserver/bastion:phase1

# 3. Update deployment image URI and deploy
# Edit bastion/k8s/deployment.yaml to use ECR image
./scripts/deploy-bastion.sh

# 4. Access via AWS NLB (takes 2-3 minutes to provision)
ssh testuser@<nlb-hostname>
```

### kind/minikube (Local Development)
```bash
# Standard workflow - scripts auto-detect and load images
./scripts/build-bastion.sh
./scripts/deploy-bastion.sh

# Test handles port-forward automatically
./scripts/test-ssh.sh

# Manual SSH access (using auto-generated demo key)
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222
```

## Directory Structure

```
├── cli/                    # Phase 1 CLI (simple proof-of-concept)
│   ├── devctl/
│   │   ├── main.py        # Simple CLI with status, info, test-k8s
│   │   └── __init__.py
│   └── pyproject.toml
├── bastion/               # Bastion container and configuration
│   ├── Dockerfile         # Multi-user SSH server
│   ├── entrypoint.sh      # User setup and SSH configuration
│   ├── config/
│   │   ├── motd           # Welcome message
│   │   ├── sshd_config    # SSH security settings
│   │   └── profile.d/
│   │       └── devserver.sh # User environment setup
│   └── k8s/               # Kubernetes manifests
│       ├── namespace.yaml
│       ├── rbac.yaml      # Service account and permissions
│       ├── deployment.yaml # HA bastion deployment
│       └── service.yaml   # LoadBalancer for SSH access
├── scripts/               # Build and deployment automation
│   ├── build-bastion.sh   # Build container image
│   ├── deploy-bastion.sh  # Deploy to Kubernetes
│   └── test-ssh.sh        # Test SSH connectivity
└── README.md              # This file
```

## Testing the Bastion

### 1. Check Deployment Status

```bash
kubectl get all -n devserver-bastion
```

### 2. Get SSH Connection Info

```bash
# Get LoadBalancer IP/hostname
kubectl get service bastion -n devserver-bastion

# Or use port-forward for testing
kubectl port-forward service/bastion -n devserver-bastion 2222:22
```

### 3. SSH to Bastion

```bash
# Using auto-generated demo key (recommended for testing)
ssh -i .demo-keys/bastion_demo testuser@<LOADBALANCER-IP>

# Or via port-forward (for local clusters)
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222

# Or run the full test suite
./scripts/test-ssh.sh
```

### 4. Test CLI Inside Bastion

Once SSH'd into the bastion:

```bash
# Check environment status
devctl status

# Test Kubernetes connectivity
devctl test-k8s

# Show available commands
devctl info

# Get help
devctl --help
```

## Customizing SSH Access

The deployment automatically generates demo SSH keys for testing. To use your own key:

**Option 1: Replace demo key (recommended for testing)**
```bash
# Copy your public key to replace the generated one
cp ~/.ssh/id_rsa.pub .demo-keys/bastion_demo.pub
./scripts/deploy-bastion.sh  # Redeploy with your key
```

**Option 2: Edit deployment directly**
1. Edit `bastion/k8s/deployment.yaml`
2. Update the `BASTION_TEST_SSH_KEY` environment variable with your public key
3. Redeploy: `./scripts/deploy-bastion.sh`

**For production**: SSH keys should come from ConfigMaps/Secrets, not environment variables.

## Phase 1 Limitations

This is a **proof-of-concept** implementation with intentional limitations:

- ❌ No server creation/management (coming in Phase 2)
- ❌ No CRDs or operator (coming in Phase 2)  
- ❌ Single test user (production would use LDAP/IAM)
- ❌ Basic RBAC (production needs more granular permissions)
- ❌ Test SSH key in environment (production uses proper secret management)

## What's Next - Phase 2

- ✅ Ansible Operator SDK setup
- ✅ DevServer and DevServerFlavor CRDs
- ✅ Server creation via `devctl create`
- ✅ PyTorch development containers
- ✅ Persistent storage (EBS + EFS)

## Troubleshooting

### Bastion Pods Not Starting

```bash
kubectl describe pods -n devserver-bastion
kubectl logs deployment/bastion -n devserver-bastion
```

### SSH Connection Issues

```bash
# Test basic connectivity
./scripts/test-ssh.sh

# Check service
kubectl get service bastion -n devserver-bastion -o wide

# Check LoadBalancer
kubectl describe service bastion -n devserver-bastion
```

### CLI Issues

```bash
# Test inside a pod
kubectl exec -it deployment/bastion -n devserver-bastion -- devctl status

# Check CLI installation
kubectl exec -it deployment/bastion -n devserver-bastion -- which devctl
```

### k3d Specific Issues

```bash
# Check if image was loaded
k3d image list -c <cluster-name>

# Reload image if needed
k3d image import devserver/bastion:phase1 -c <cluster-name>

# Check k3d cluster status
k3d cluster list

# Access k3d cluster info
kubectl cluster-info --context k3d-<cluster-name>
```

## Success Criteria for Phase 1 ✅

- [x] Users can SSH to bastion server
- [x] `devctl` CLI is available and functional
- [x] Kubernetes connectivity works from bastion
- [x] User environment is properly configured
- [x] LoadBalancer provides external SSH access
- [x] Health checks and monitoring work
- [x] HA deployment with multiple bastion pods
- [x] **Auto-generated SSH keys for immediate testing**
- [x] **Environment-aware deployment scripts**
- [x] **End-to-end testing automation**
- [x] **Repeatable developer workflow**

## Architecture Notes

The bastion uses:
- **Ubuntu 22.04** base image for stability
- **OpenSSH** server with security hardening
- **Python 3** with Click and Rich for CLI
- **kubectl** for Kubernetes connectivity
- **Service Account** with appropriate RBAC
- **Network LoadBalancer** for high availability

This foundation will support the full development server platform in later phases.
