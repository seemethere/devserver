# eks dev setup

1. Create a cluster with auto-mode enabled
```bash
eksctl create cluster --name=<MY_NAME> --enable-auto-mode --region <REGION>
```

2. Apply the default storage class and GPU nodepool for EKS auto mode

```bash
# assuming from the root directory
kubectl apply -f dev/eks/
```

## GPU Nodepool
The `gpu-nodepool.yml` configures a GPU-accelerated nodepool using Karpenter with:
- NVIDIA GPU instance types (g6e and g6 families)
- Taint `nvidia.com/gpu:NoSchedule` to ensure only GPU workloads schedule on these nodes

To use GPU nodes in your pods, add:
```yaml
spec:
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
  resources:
    limits:
      nvidia.com/gpu: 1
```

## TODO
- [ ] Add some sample EFS storage to this setup for shared folders
