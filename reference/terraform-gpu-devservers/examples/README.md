# GPU Workload Examples

This directory contains example Kubernetes Job manifests demonstrating how to request different GPU resource types with the NVIDIA GPU Operator and MIG (Multi-Instance GPU) configuration.

## Prerequisites

- EKS cluster with NVIDIA GPU Operator deployed
- H100 nodes configured with `nvidia.com/mig.config=all-balanced` labels
- MIG strategy set to `mixed` in GPU Operator configuration

## Available GPU Resource Types

The balanced MIG configuration provides the following GPU resource types per H100 GPU:

| Resource Type | Memory | SM Cores | Description |
|---------------|--------|----------|-------------|
| `nvidia.com/mig-1g.10gb` | ~10GB | 16 | Small workloads |
| `nvidia.com/mig-2g.20gb` | ~20GB | 32 | Medium workloads |
| `nvidia.com/mig-3g.40gb` | ~40GB | 60 | Large workloads |
| `nvidia.com/gpu` | ~80GB | 132 | Full GPU |

**Total Capacity per H100 GPU:** 2x small + 1x medium + 1x large = 4 MIG slices per GPU

## Example Usage

### 1. Single Workload Examples

Apply individual workload types:

```bash
# Small workload (10GB GPU memory)
kubectl apply -f test-dynamic-small.yaml

# Medium workload (20GB GPU memory)
kubectl apply -f test-dynamic-medium.yaml

# Large workload (40GB GPU memory)
kubectl apply -f test-dynamic-large.yaml

# Full GPU workload (80GB GPU memory)
kubectl apply -f test-dynamic-full.yaml
```

### 2. Multiple Coexisting Workloads

Demonstrate multiple workloads running simultaneously:

```bash
# Run multiple different-sized workloads at once
kubectl apply -f test-coexist.yaml
```

This creates:
- 2x small MIG slice jobs (1g.10gb)
- 1x medium MIG slice job (2g.20gb)

### 3. Check Resource Allocation

Monitor current GPU resource usage:

```bash
# Check available GPU resources on nodes
kubectl describe nodes | grep -A10 "Allocatable:"

# Check current resource allocation
kubectl describe nodes | grep -A10 "Allocated resources:"

# View running pods with GPU resources
kubectl get pods -o wide | grep Running
```

## Job Specification Pattern

To request a specific GPU resource type in your job, target H100 GPUs specifically:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: your-gpu-job
spec:
  template:
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      nodeSelector:
        nvidia.com/gpu.product: NVIDIA-H100-80GB-HBM3  # Target H100 GPUs specifically
      containers:
      - name: workload
        image: your-image
        resources:
          limits:
            nvidia.com/mig-1g.10gb: 1  # Change this line for different sizes
          requests:
            nvidia.com/mig-1g.10gb: 1  # Change this line for different sizes
```

**Resource Request Options:**
- `nvidia.com/mig-1g.10gb: 1` - Small GPU slice
- `nvidia.com/mig-2g.20gb: 1` - Medium GPU slice  
- `nvidia.com/mig-3g.40gb: 1` - Large GPU slice
- `nvidia.com/gpu: 1` - Full GPU

## GPU Type Targeting

All examples include a `nodeSelector` to specifically target H100 GPUs:

```yaml
nodeSelector:
  nvidia.com/gpu.product: NVIDIA-H100-80GB-HBM3
```

This ensures workloads only run on H100 nodes and not other GPU types (like T4s) that might be in your cluster.

## Dynamic Scheduling

Jobs automatically get scheduled to H100 nodes with available resources of the requested type. No additional node labeling required - just specify the GPU type and resource size you need!

## Cleanup

Remove example jobs:

```bash
# Delete all test jobs
kubectl delete jobs -l 'job-name in (test-dynamic-small,test-dynamic-medium,test-dynamic-large,test-dynamic-full,test-coexist-small-1,test-coexist-small-2,test-coexist-medium)'

# Or delete all jobs in namespace
kubectl delete jobs --all
```