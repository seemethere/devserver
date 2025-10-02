# eks dev setup

1. Create a cluster with auto-mode enabled
```bash
eksctl create cluster --name=<MY_NAME> --enable-auto-mode --region <REGION>
```

2. Apply the default storage class for the EBS auto mode CSI

```bash
# assuming from the root directory
kubectl apply -f dev/eks/
```

## TODO
- [ ] Add some example GPU node pools to this dev setup
- [ ] Add some sample EFS storage to this setup for shared folders
