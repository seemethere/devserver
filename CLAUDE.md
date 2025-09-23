# Kubernetes Operator for PyTorch Development Servers

## Project Overview
Build a Kubernetes operator to manage development servers for developers on AWS EKS, supporting both standalone development and distributed PyTorch training. Users access the platform through a centralized bastion server that provides a secure, audited interface to the Kubernetes cluster. The operator will be built using Ansible Operator SDK and integrated with Kueue for resource quotas.

## Core Requirements

### Infrastructure
- **Platform**: AWS EKS
- **Operator Framework**: Ansible Operator SDK
- **Resource Management**: Kueue for quotas
- **Access Method**: Centralized bastion server with SSH access
- **Storage**:
  - EBS volumes for persistent user home directories (`/home/dev/`)
  - EFS shared volume across user's servers (`/shared`)
- **ML Framework**: PyTorch only

### Key Features
1. **Resource Flavors**: Predefined configurations (GPU types, memory, CPU)
2. **Distributed Training**: Support PyTorch distributed training with multiple replicas
3. **Lifecycle Management**: Create, update, delete, auto-shutdown
4. **User Isolation**: Per-user namespaces with RBAC
5. **Persistent Storage**: Home directories preserved across restarts

## Architecture Design

### Bastion Server Access

Users access the development server platform through a centralized bastion server:

- **SSH Entry Point**: Users SSH to `bastion.devservers.company.com`
- **Python CLI**: The `devctl` CLI is pre-installed on the bastion server
- **Namespace Isolation**: Each user is automatically scoped to their `dev-<username>` namespace
- **No Local kubectl**: Users never receive direct cluster credentials
- **Audit Trail**: All commands are logged centrally for security and compliance

```bash
# User workflow
ssh username@bastion.devservers.company.com
devctl create mydev gpu-large
devctl ssh mydev
```

**Security Benefits:**
- Single point of access control
- No kubectl credentials distributed to users
- Centralized command auditing
- Network isolation of development servers
- Automated user namespace management

### Custom Resource Definitions (CRDs)

#### DevServer CRD
```yaml
apiVersion: devservers.io/v1
kind: DevServer
metadata:
  name: <server-name>
  namespace: dev-<username>
spec:
  owner: <user>@company.com
  flavor: gpu-large  # References DevServerFlavor
  image: company/pytorch-dev:latest
  mode: standalone  # or distributed

  # For distributed training only
  distributed:
    worldSize: 4
    nprocsPerNode: 1
    backend: nccl
    ncclSettings:
      NCCL_DEBUG: INFO
      NCCL_SOCKET_IFNAME: eth0

  persistentHomeSize: 100Gi
  sharedVolumeClaimName: <username>-shared-efs
  enableSSH: true

  lifecycle:
    idleTimeout: 3600
    autoShutdown: true
```

#### DevServerFlavor CRD
```yaml
apiVersion: devservers.io/v1
kind: DevServerFlavor
metadata:
  name: gpu-large
spec:
  resources:
    requests:
      memory: 32Gi
      cpu: 8
      nvidia.com/gpu: 1
    limits:
      memory: 64Gi
      cpu: 16
      nvidia.com/gpu: 1
  nodeSelector:
    instance-type: g4dn.xlarge
```

### Kubernetes Resources Created

#### For Standalone Mode
- **Pod/Deployment**: Single development server
- **PVC (EBS)**: Home directory
- **PVC (EFS)**: Shared volume
- **Service**: For SSH/port access

#### For Distributed Mode
- **StatefulSet**: Ordered pods for training nodes
- **Headless Service**: Pod discovery for PyTorch
- **ConfigMap**: PyTorch utility scripts
- **PVC (EBS)**: Home directory per pod
- **PVC (EFS)**: Shared volume across all pods

## Implementation Plan

### Phase 1: Bastion Infrastructure (Weeks 1-2)
1. Build bastion container image with Python CLI
2. Deploy bastion server with HA configuration
3. Setup SSH authentication and user management
4. Configure Network Load Balancer and DNS
5. Test user onboarding and basic CLI access

### Phase 2: MVP Operator (Weeks 3-4)
1. Setup Ansible Operator SDK project structure
2. Create basic CRDs (DevServer, DevServerFlavor)
3. Implement standalone server creation/deletion
4. EBS/EFS volume provisioning
5. Integrate operator with bastion CLI

### Phase 3: Distributed Training (Weeks 5-6)
1. Add distributed mode to DevServer CRD
2. Implement StatefulSet creation for distributed training
3. Configure PyTorch environment variables
4. Add headless service for pod discovery
5. Create PyTorch utility scripts ConfigMap

### Phase 4: User Management & Security (Weeks 7-8)
1. Enhanced per-user namespace isolation
2. Advanced RBAC roles and bindings
3. SSH key rotation and management
4. User onboarding automation
5. Integrate with corporate SSO/OIDC

### Phase 5: Resource Management (Weeks 9-10)
1. Integrate Kueue for resource quotas
2. Implement gang scheduling for distributed jobs
3. Add resource monitoring and cost tracking
4. Auto-shutdown for idle servers
5. Capacity planning dashboards

### Phase 6: Production Readiness (Weeks 11-12)
1. Add comprehensive error handling
2. Implement health checks and recovery
3. Setup logging and monitoring (Prometheus/Grafana)
4. Security hardening and penetration testing
5. Documentation and training materials

## Project Structure

```
pytorch-dev-operator/
├── config/
│   ├── crd/
│   │   ├── devserver_crd.yaml
│   │   └── devserverflavor_crd.yaml
│   ├── rbac/
│   │   ├── role.yaml
│   │   └── role_binding.yaml
│   └── manager/
│       └── kustomization.yaml
├── roles/
│   └── devserver/
│       ├── tasks/
│       │   ├── main.yml
│       │   ├── create_standalone.yml
│       │   ├── create_distributed.yml
│       │   ├── delete.yml
│       │   └── update.yml
│       ├── templates/
│       │   ├── deployment.yaml.j2
│       │   ├── statefulset-pytorch.yaml.j2
│       │   ├── pvc-home.yaml.j2
│       │   ├── pvc-shared.yaml.j2
│       │   ├── service.yaml.j2
│       │   ├── service-headless.yaml.j2
│       │   └── configmap-pytorch-utils.yaml.j2
│       └── defaults/
│           └── main.yml
├── bastion/
│   ├── Dockerfile          # Bastion container image
│   ├── deployment.yaml     # Bastion HA deployment
│   ├── rbac.yaml          # Bastion service account & permissions
│   ├── devctl.py          # Python CLI script
│   ├── profile.d/         # User environment setup
│   │   └── devserver.sh
│   └── motd               # Welcome message
├── watches.yaml
├── requirements.yml
└── Dockerfile             # Operator image
```

## CLI Commands

Users access the Python CLI through the bastion server via SSH:

```bash
# SSH to bastion server
ssh username@bastion.devservers.company.com

# CLI is pre-installed and configured
# Create standalone dev server
devctl create my-dev --flavor gpu-large

# Create distributed training cluster
devctl create training-job --flavor gpu-large --distributed --replicas 4

# SSH into server (or specific replica)
devctl ssh my-dev [--replica 0]

# Run distributed training
devctl run training-job train.py --batch-size 32

# Monitor resources
devctl monitor training-job

# Delete server
devctl delete my-dev
```

## Key Technical Decisions

### Storage Strategy
- **EBS** for home directories: Better performance, per-pod isolation
- **EFS** for shared data: Dataset sharing, checkpoints, code
- **EmptyDir** with Memory medium for `/dev/shm`: Critical for PyTorch DataLoader performance

### Networking
- **Headless Service** for PyTorch distributed discovery
- **NCCL** environment variables properly configured
- Port range 29500-29510 reserved for distributed communication

### PyTorch Optimizations
- Single GPU per pod for simplicity (can be extended)
- Proper RANK/WORLD_SIZE environment variables
- NCCL backend for GPU communication
- Utility scripts for easy `torchrun` usage

### Security & Access
- Per-user namespaces for isolation
- RBAC for user permissions
- Optional SSH access for development
- Service accounts for CLI authentication

## Success Metrics
- Bastion server availability > 99.9%
- SSH connection time to bastion < 2 seconds
- Server creation time < 2 minutes
- Support 100+ concurrent users on bastion
- Support 100+ concurrent dev servers
- 99% uptime for persistent storage
- Distributed training setup < 5 minutes
- Cost reduction via auto-shutdown > 30%
- Zero direct kubectl access for end users

## Future Enhancements
- Web UI dashboard
- VS Code remote development integration
- Jupyter notebook support
- Automated checkpoint management
- Multi-GPU per pod support
- Spot instance support for cost optimization
- Integration with MLflow/Weights & Biases

## Dependencies
- AWS EKS cluster with GPU nodes
- Network Load Balancer for bastion access
- EBS CSI driver
- EFS CSI driver
- Kueue installed
- Ansible Operator SDK
- NVIDIA device plugin
- Container registry for PyTorch and bastion images
- DNS management for bastion endpoint
- SSH key management system (GitHub/LDAP/IAM)

## Next Steps
1. Set up development EKS cluster with GPU nodes
2. Build and deploy bastion infrastructure (Phase 1)
3. Setup DNS and user SSH access
4. Implement basic operator and CLI integration (Phase 2)
5. Test with pilot user group
6. Iterate based on feedback and expand features
