# Kubernetes Operator for PyTorch Development Servers

## Project Overview
Build a Kubernetes operator to manage development servers for developers on AWS EKS, supporting both standalone development and distributed PyTorch training. The operator will be built using Ansible Operator SDK and integrated with Kueue for resource quotas.

## Core Requirements

### Infrastructure
- **Platform**: AWS EKS
- **Operator Framework**: Ansible Operator SDK
- **Resource Management**: Kueue for quotas
- **Storage**:
  - EBS volumes for persistent user home directories (`/home/dev/`)
  - EFS shared volume across user's servers (`/shared`)
- **ML Framework**: PyTorch only
- **Access Method**: CLI initially

### Key Features
1. **Resource Flavors**: Predefined configurations (GPU types, memory, CPU)
2. **Distributed Training**: Support PyTorch distributed training with multiple replicas
3. **Lifecycle Management**: Create, update, delete, auto-shutdown
4. **User Isolation**: Per-user namespaces with RBAC
5. **Persistent Storage**: Home directories preserved across restarts

## Architecture Design

### Custom Resource Definitions (CRDs)

#### DevServer CRD
```yaml
apiVersion: devops.yourcompany.com/v1
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
apiVersion: devops.yourcompany.com/v1
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

### Phase 1: MVP (Weeks 1-2)
1. Setup Ansible Operator SDK project structure
2. Create basic CRDs (DevServer, DevServerFlavor)
3. Implement standalone server creation/deletion
4. EBS/EFS volume provisioning
5. Basic CLI wrapper for kubectl

### Phase 2: Distributed Training (Weeks 3-4)
1. Add distributed mode to DevServer CRD
2. Implement StatefulSet creation for distributed training
3. Configure PyTorch environment variables
4. Add headless service for pod discovery
5. Create PyTorch utility scripts ConfigMap

### Phase 3: User Management (Weeks 5-6)
1. Implement per-user namespaces
2. Setup RBAC roles and bindings
3. CLI authentication with kubeconfig
4. User onboarding automation
5. Integrate with corporate SSO/OIDC

### Phase 4: Resource Management (Weeks 7-8)
1. Integrate Kueue for resource quotas
2. Implement gang scheduling for distributed jobs
3. Add resource monitoring
4. Cost tracking per user
5. Auto-shutdown for idle servers

### Phase 5: Production Readiness (Weeks 9-10)
1. Add comprehensive error handling
2. Implement health checks and recovery
3. Setup logging and monitoring (Prometheus/Grafana)
4. Security hardening
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
├── watches.yaml
├── requirements.yml
├── Dockerfile
└── devctl/
    └── devctl.sh  # CLI tool
```

## CLI Commands

```bash
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
- Server creation time < 2 minutes
- Support 100+ concurrent dev servers
- 99% uptime for persistent storage
- Distributed training setup < 5 minutes
- Cost reduction via auto-shutdown > 30%

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
- EBS CSI driver
- EFS CSI driver
- Kueue installed
- Ansible Operator SDK
- NVIDIA device plugin
- Container registry for PyTorch images

## Next Steps
1. Set up development EKS cluster
2. Install operator SDK and create project scaffold
3. Implement Phase 1 MVP
4. Test with pilot user group
5. Iterate based on feedback
