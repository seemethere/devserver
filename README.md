# PyTorch Development Server Platform - Phase 3 ✅

## Overview

This is the **PyTorch Development Server Platform** with **Phase 3 Complete** - featuring a production-ready Golang operator for managing development servers. The platform now includes centralized SSH access via bastion infrastructure AND a fully functional DevServer operator with CRDs for managing standalone development environments.

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

## Phase 2 Goals ✅

- [x] Secure user provisioning with sidecar controller
- [x] Namespace-scoped kubectl access for users
- [x] Zero-trust security model implementation
- [x] Enhanced bastion with user controller integration
- [x] Automated user onboarding and resource provisioning

## Phase 3 Goals ✅

- [x] **Golang Operator SDK (Kubebuilder) project setup**
- [x] **DevServer and DevServerFlavor CRDs with comprehensive validation**
- [x] **Standalone development server creation and management**
- [x] **Production-ready reconciliation controller**
- [x] **Smart container lifecycle management (sleep infinity injection)**
- [x] **Error-free PVC and resource management**
- [x] **Real-time status tracking and SSH endpoint provisioning**
- [x] **Local development workflow (k3d compatibility)**
- [x] **🚀 Enhanced devctl CLI with modular architecture**
- [x] **🚀 Cluster-scoped DevServerFlavors with automatic defaults**
- [x] **🚀 Complete user workflow: SSH → devctl create → devctl ssh**
- [x] **🚀 Enterprise-grade RBAC with cluster and namespace scoped resources**

## What's Working (All Phases Complete)

### Phase 1 ✅ - Bastion Infrastructure
- 🚀 **Bastion Server**: SSH-accessible container with proper user environment
- 🔧 **DevCtl CLI**: `devctl status`, `devctl info`, `devctl test-k8s` - fully functional
- ☸️ **Kubernetes Integration**: Service account, RBAC, namespace management
- 🔐 **Security**: SSH key authentication, auto-generated demo keys for testing
- 📊 **Monitoring**: Health checks, readiness probes, HA deployment (2 replicas)
- 🎯 **Environment Detection**: Auto-detects k3d, kind, minikube, EKS clusters
- 🔄 **Automated Deployment**: Smart scripts with cleanup, image loading, SSH key injection
- 🧪 **End-to-End Testing**: SSH authentication verification and CLI validation
- 🛠️ **Developer Experience**: One-command build, deploy, test workflow

### Phase 2 ✅ - Secure User Provisioning  
- 🔒 **User Controller**: Automatic namespace and ServiceAccount provisioning
- 👤 **Zero-Trust Security**: Namespace-scoped kubectl access only
- 🛡️ **RBAC Separation**: Controller vs user permissions properly isolated
- 🔑 **Token Management**: Secure user-owned token files with proper permissions
- 📋 **User Registry**: JSON-based user tracking and status management

### Phase 3 ✅ - DevServer Operator & Complete User Experience
- ⚙️ **Golang Operator**: Production-ready Kubebuilder-based operator
- 📋 **Custom Resources**: DevServer and DevServerFlavor CRDs with full validation
- 🔄 **Smart Reconciliation**: Error-free loops with proper resource management
- 💾 **Storage Management**: Intelligent PVC handling with immutable spec support
- 🐳 **Container Lifecycle**: Auto-injection of sleep commands for any base image with full container access
- 📊 **Status Tracking**: Real-time phase monitoring and SSH endpoint provisioning
- 🏠 **Local Development**: Optimized for k3d clusters with appropriate sizing
- 🎯 **Enterprise Resource Management**: Cluster-scoped DevServerFlavors with automatic defaults
- 🖥️ **Complete CLI Experience**: Modular devctl with create, list, describe, delete, exec, ssh, flavors
- 🎨 **Rich UI**: Beautiful tables, panels, and progress spinners for enhanced user experience
- 🔐 **Enhanced RBAC**: Proper permissions for cluster-scoped resources and container access
- 🔧 **End-to-End Workflow**: From SSH login to DevServer creation to container access - all seamless

## Quick Start

### Prerequisites

- Kubernetes cluster (EKS, kind, minikube, k3d, etc.)
- `kubectl` configured and connected
- Docker for building images (for bastion)
- SSH client for testing bastion

### Option A: Complete DevServer Platform (Phase 3) - Recommended

**Deploy the complete platform with operator, bastion, and CLI:**

**Full Platform Deployment:**
```bash
# 1. Deploy DevServer operator with automatic default flavors
cd devserver-operator && make deploy
# Creates: Operator + Default flavors (cpu-small, cpu-medium, cpu-large)

# 2. Deploy bastion with enhanced user provisioning  
cd ../bastion && make deploy
# Creates: SSH-accessible bastion with secure user auto-provisioning

# 3. Test complete integration
make test
```

**End-to-End User Workflow:**
```bash
# 1. SSH to bastion (auto-provisioned with namespace + RBAC)
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222

# 2. Inside bastion - Complete DevServer lifecycle via enhanced devctl
devctl status           # Shows environment + cluster-wide flavors
devctl flavors          # Lists cpu-small, cpu-medium, cpu-large  
devctl create mydev --flavor cpu-small --wait  # Creates with progress tracking
devctl list             # Shows your DevServers with status
devctl ssh mydev        # Interactive shell in development container
devctl describe mydev   # Detailed information and resource status
devctl delete mydev     # Clean up when done
```

**Operator-Only Deployment (Development):**
```bash
# 1. Deploy operator only for kubectl-based development
cd devserver-operator && make deploy

# 2. Create DevServers via kubectl
kubectl create namespace dev-$(whoami)
kubectl apply -f config/samples/devservers_v1_devserver.yaml

# 3. Access via kubectl
kubectl exec -it deployment/mydev -- bash
```

### Option B: Bastion Only (Phase 1+2)

**Deploy just the bastion infrastructure for SSH access:**

```bash
# Build bastion container
make -C bastion build

# Deploy with environment auto-detection and SSH key generation
make -C bastion deploy

# Test full end-to-end SSH connectivity and CLI
make -C bastion test
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
make -C bastion build
make -C bastion deploy

# 3. Test automatically uses port-forward for local clusters
make -C bastion test

# 4. Manual SSH access (using auto-generated demo key)
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222
```

### EKS (Production)
```bash
# 1. Ensure you have an ECR repository
aws ecr create-repository --repository-name devserver/bastion

# 2. Build and push to ECR
make -C bastion build
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com
docker tag devserver/bastion:phase1 <account>.dkr.ecr.us-west-2.amazonaws.com/devserver/bastion:phase1
docker push <account>.dkr.ecr.us-west-2.amazonaws.com/devserver/bastion:phase1

# 3. Update deployment image URI and deploy
# Edit bastion/k8s/deployment.yaml to use ECR image
make -C bastion deploy

# 4. Access via AWS NLB (takes 2-3 minutes to provision)
ssh testuser@<nlb-hostname>
```

### kind/minikube (Local Development)
```bash
# Standard workflow - scripts auto-detect and load images
make -C bastion build
make -C bastion deploy

# Test handles port-forward automatically
make -C bastion test

# Manual SSH access (using auto-generated demo key)
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222
```

## Directory Structure

```
├── devserver-operator/    # ✅ Phase 3 - DevServer Operator (Golang)
│   ├── api/v1/           # CRD Go structs and schemas
│   │   ├── devserver_types.go
│   │   ├── devserverflavor_types.go
│   │   ├── groupversion_info.go
│   │   └── zz_generated.deepcopy.go
│   ├── config/           # Kubernetes manifests and kustomize
│   │   ├── crd/bases/    # Generated CRD YAML files
│   │   ├── samples/      # Example DevServer and DevServerFlavor
│   │   ├── rbac/         # Operator permissions
│   │   └── manager/      # Deployment configuration
│   ├── internal/controller/ # Reconciliation logic
│   │   ├── devserver_controller.go
│   │   └── devserverflavor_controller.go
│   ├── scripts/          # Deployment automation (bastion-style)
│   │   ├── deploy-operator.sh  # Build and deploy operator
│   │   └── test-operator.sh    # Test operator functionality
│   ├── Makefile          # Build, deploy, test commands
│   └── Dockerfile        # Operator container image
├── cli/                  # ✅ Phase 3 - Complete DevServer Management CLI
│   ├── devctl/
│   │   ├── main.py      # ✅ Modular CLI with complete DevServer lifecycle
│   │   ├── commands/    # ✅ Separated command modules (status, devserver, test, info)
│   │   ├── api/         # ✅ Kubernetes API operations (kubectl, devserver)
│   │   ├── ui/          # ✅ Rich console utilities (tables, panels, progress)
│   │   ├── config/      # ✅ Configuration and settings
│   │   └── __init__.py
│   └── pyproject.toml
├── bastion/             # Phase 1+2 Bastion infrastructure  
│   ├── Dockerfile       # SSH server + user controller sidecar
│   ├── entrypoint.sh    # User setup and SSH configuration
│   ├── user-controller.py # Secure user provisioning sidecar
│   ├── config/
│   │   ├── motd         # Welcome message
│   │   ├── sshd_config  # SSH security settings
│   │   └── profile.d/
│   │       └── devserver.sh # User environment setup
│   ├── k8s/             # Kubernetes manifests
│   │   ├── namespace.yaml
│   │   ├── rbac.yaml    # Service account and permissions
│   │   ├── deployment.yaml # HA bastion deployment
│   │   └── service.yaml # LoadBalancer for SSH access
│   └── scripts/         # Bastion automation
│       ├── deploy-bastion.sh # Deploy bastion infrastructure
│       └── test-ssh.sh      # Test SSH connectivity
└── README.md            # This file
```

## Testing the DevServer Operator

### 1. Check Operator Status

```bash
kubectl get all -n devserver-operator-system
```

### 2. Check DevServer Resources

```bash
# Check CRDs are installed
kubectl get crd | grep devserver

# Check sample resources
kubectl get devserverflavors,devservers

# Check created infrastructure
kubectl get pods,pvc,svc,deployments -l app=devserver
```

### 3. Access Development Environment

```bash
# Get pod name
kubectl get pods -l app=devserver

# Execute commands in development server
kubectl exec -it deployment/mydev -- bash

# Test volume mounts
kubectl exec deployment/mydev -- ls -la /home/dev
```

### 4. Operator Commands

```bash
# Build, deploy, and test (one command)
cd devserver-operator && make test

# Build and deploy only  
make deploy

# Clean up everything
make clean

# Run operator locally (development)
make run
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
make -C bastion test
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
make -C bastion deploy  # Redeploy with your key
```

**Option 2: Edit deployment directly**
1. Edit `bastion/k8s/deployment.yaml`
2. Update the `BASTION_TEST_SSH_KEY` environment variable with your public key
3. Redeploy: `make -C bastion deploy`

**For production**: SSH keys should come from ConfigMaps/Secrets, not environment variables.

## Current Limitations

With **Phase 3 Enhanced Complete**, the core platform is production-ready for local/generic Kubernetes. AWS-specific features needed for Phase 4:

- 🔄 **AWS Storage**: Currently uses generic PVCs, needs EBS/EFS integration for production
- 🔄 **GPU Support**: No GPU node support or NVIDIA device plugin configuration  
- 🔄 **Production Authentication**: Still using demo SSH keys, needs AWS IAM/SSO integration
- 🔄 **AWS Networking**: Needs Network Load Balancer and proper VPC configuration
- 🔄 **Container Registry**: Needs ECR integration for production image management
- 🔄 **Cost Management**: No AWS cost tracking or resource usage monitoring
- 🔄 **Infrastructure as Code**: No Terraform/CDK for automated EKS provisioning

For Phase 5 (Distributed Training):
- 🔄 **Multi-Node Training**: StatefulSet support for distributed PyTorch
- 🔄 **Advanced Lifecycle**: Auto-shutdown, idle detection, resource quotas

## What's Next - Phase 4: AWS Production Implementation

- 🏭 **AWS Storage Integration**: EBS CSI driver for persistent home directories, EFS CSI for shared volumes
- 🎯 **GPU Support**: NVIDIA device plugin, AWS GPU instance types (p3, p4, g4dn)
- 🔧 **AWS-Specific Flavors**: DevServerFlavors for GPU instances with proper resource configurations
- 🌐 **Production Networking**: Network Load Balancer for bastion, ECR integration for images
- 🔐 **AWS IAM Integration**: Replace demo SSH keys with AWS IAM/SSO authentication
- 📊 **Cost Tracking**: AWS cost monitoring and resource usage tracking
- 🏗️ **Infrastructure**: Terraform/CDK for EKS cluster provisioning with proper node groups

## What's Next - Phase 5: Distributed Training & Advanced Features

- ⚡ **Distributed Training**: StatefulSet support for multi-node PyTorch training with NCCL
- 🔧 **Training Workflow**: `devctl create job --distributed --replicas N` for multi-GPU training
- 🎯 **PyTorch Optimization**: NCCL configuration, utility scripts, and environment setup
- 📊 **Enhanced Monitoring**: Training job monitoring, progress tracking, and log aggregation
- 🏭 **Advanced Features**: Auto-shutdown, Kueue integration, gang scheduling

## Troubleshooting

### Bastion Pods Not Starting

```bash
kubectl describe pods -n devserver-bastion
kubectl logs deployment/bastion -n devserver-bastion
```

### SSH Connection Issues

```bash
# Test basic connectivity
make -C bastion test

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

## Success Criteria ✅

### Phase 1 - Bastion Infrastructure ✅
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

### Phase 2 - Secure User Provisioning ✅
- [x] **Automatic namespace provisioning per user**
- [x] **Namespace-scoped kubectl access only**
- [x] **Zero-trust security model implementation**
- [x] **User controller sidecar pattern**
- [x] **Secure token management and file permissions**

### Phase 3 - DevServer Operator & Complete Platform ✅
- [x] **Golang operator with Kubebuilder framework**
- [x] **DevServer and DevServerFlavor CRDs working (cluster-scoped flavors)**
- [x] **Standalone development server creation and management**
- [x] **Automatic PVC, Deployment, and Service provisioning**
- [x] **Container lifecycle management (sleep infinity) with full access**
- [x] **Error-free reconciliation loops**
- [x] **Real-time status tracking and SSH endpoints**
- [x] **Local k3d cluster compatibility**
- [x] **🚀 Complete devctl CLI with modular architecture**
- [x] **🚀 Enterprise resource management (cluster-scoped flavors)**
- [x] **🚀 Automatic default flavor creation (cpu-small, cpu-medium, cpu-large)**
- [x] **🚀 Enhanced RBAC for cluster and namespace scoped resources**
- [x] **🚀 End-to-end user workflow: SSH → create → access → cleanup**
- [x] **🚀 pods/exec permissions for devctl ssh and container access**
- [x] **🚀 Rich UI with progress tracking and beautiful console output**

## Architecture Notes

### Bastion Infrastructure (Phase 1+2)
- **Ubuntu 22.04** base image for stability
- **OpenSSH** server with security hardening
- **Python 3** with Click and Rich for CLI
- **kubectl** for Kubernetes connectivity
- **Service Account** with appropriate RBAC
- **Network LoadBalancer** for high availability
- **User Controller** sidecar for secure provisioning

### DevServer Operator (Phase 3)
- **Golang** with Kubebuilder framework for robust operator development
- **Custom Resource Definitions** for DevServer and DevServerFlavor
- **Controller-Runtime** for efficient reconciliation and event handling
- **Finalizer Pattern** for safe resource cleanup and deletion
- **Owner References** for automatic garbage collection
- **Status Subresource** for real-time state tracking

This foundation now supports full development server lifecycle management with a production-ready operator.
