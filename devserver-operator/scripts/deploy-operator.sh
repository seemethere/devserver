#!/bin/bash

# Deploy script for DevServer operator - Phase 3
# Complete operator deployment with environment detection

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
IMAGE_NAME="devserver-operator:latest"
NAMESPACE="devserver-operator-system"

# Parse command line options
FORCE_CLEANUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force-cleanup)
            FORCE_CLEANUP=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force-cleanup   Force cleanup of stuck resources (grace-period=0)"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                Normal deployment (cleans up existing by default)"
            echo "  $0 --force-cleanup Force cleanup stuck resources and redeploy"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Cleanup function
cleanup() {
    if [ -n "$TEMP_DEPLOY" ] && [ -f "$TEMP_DEPLOY" ]; then
        echo "🧹 Cleaning up temporary files..."
        rm -f "$TEMP_DEPLOY"
    fi
}

# Set trap for cleanup on exit/error
trap cleanup EXIT

# Kubernetes cleanup functions
cleanup_k8s_resources() {
    echo "🧹 Cleaning up existing operator resources..."

    # Delete existing operator deployment
    if kubectl get deployment devserver-operator-controller-manager -n "$NAMESPACE" &>/dev/null; then
        echo "  → Deleting existing operator deployment..."
        kubectl delete deployment devserver-operator-controller-manager -n "$NAMESPACE" --ignore-not-found=true
    fi

    # Clean up stuck pods if force cleanup is requested
    if [ "$FORCE_CLEANUP" = true ]; then
        echo "  → Force cleaning stuck pods..."
        kubectl delete pods -n "$NAMESPACE" --field-selector=status.phase=Failed --ignore-not-found=true
        kubectl delete pods -n "$NAMESPACE" --field-selector=status.phase=Pending --ignore-not-found=true

        # Force delete any remaining operator pods
        if kubectl get pods -n "$NAMESPACE" 2>/dev/null | grep -q controller-manager; then
            echo "  → Force deleting remaining operator pods..."
            kubectl delete pods -n "$NAMESPACE" -l control-plane=controller-manager --grace-period=0 --force --ignore-not-found=true
        fi
    fi

    # Clean up existing test DevServers
    echo "  → Cleaning up test DevServers..."
    if kubectl get crd devservers.apps.devservers.io &> /dev/null; then
        echo "    → Deleting DevServer resources..."
        kubectl delete devservers --all --ignore-not-found=true
    fi
    if kubectl get crd devserverflavors.apps.devservers.io &> /dev/null; then
        echo "    → Deleting DevServerFlavor resources..."
        kubectl delete devserverflavors --all --ignore-not-found=true
    fi

    # Wait for cleanup to complete
    echo "  → Waiting for cleanup to complete..."
    kubectl wait --for=delete pods -n "$NAMESPACE" -l control-plane=controller-manager --timeout=30s 2>/dev/null || true

    echo "✅ Cleanup complete!"
}

echo "🚀 Deploying DevServer Operator - Phase 3"
echo "Project root: $PROJECT_ROOT"
echo "Namespace: $NAMESPACE"

if [ "$FORCE_CLEANUP" = true ]; then
    echo "Force cleanup requested: $FORCE_CLEANUP"
fi
echo

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl and configure cluster access."
    exit 1
fi

# Check cluster connectivity
echo "🔍 Checking cluster connectivity..."
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

CLUSTER_NAME=$(kubectl config current-context)
echo "✅ Connected to cluster: $CLUSTER_NAME"

# Detect cluster type
CLUSTER_TYPE="unknown"
if [[ "$CLUSTER_NAME" == k3d-* ]]; then
    CLUSTER_TYPE="k3d"
elif [[ "$CLUSTER_NAME" == kind-* ]]; then
    CLUSTER_TYPE="kind"
elif kubectl get nodes -o jsonpath='{.items[0].spec.providerID}' | grep -q "aws://"; then
    CLUSTER_TYPE="eks"
elif kubectl cluster-info | grep -q "minikube"; then
    CLUSTER_TYPE="minikube"
fi

echo "Detected cluster type: $CLUSTER_TYPE"
echo

# Always clean up existing deployment for smooth iteration
cleanup_k8s_resources
echo

# Build Docker image
echo "🏗️  Building operator Docker image..."
make docker-build IMG="$IMAGE_NAME"
echo "✅ Docker image built successfully"
echo

# Handle image loading based on cluster type
case "$CLUSTER_TYPE" in
    "eks")
        echo "🏗️  EKS detected - you need to push image to ECR first!"
        echo "   Quick setup:"
        echo "   1. aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com"
        echo "   2. docker tag $IMAGE_NAME <account>.dkr.ecr.<region>.amazonaws.com/$IMAGE_NAME"
        echo "   3. docker push <account>.dkr.ecr.<region>.amazonaws.com/$IMAGE_NAME"
        echo "   4. Set IMG=<ecr-uri> when running this script"
        echo
        echo "   Or for testing, use imagePullPolicy: Never with a pre-pulled image"
        ;;
    "k3d")
        if command -v k3d &> /dev/null; then
            CLUSTER_SIMPLE_NAME="$(echo $CLUSTER_NAME | sed 's/k3d-//')"
            echo "🔄 Loading image to k3d cluster: $CLUSTER_SIMPLE_NAME..."
            k3d image import "$IMAGE_NAME" -c "$CLUSTER_SIMPLE_NAME" || true
        fi
        ;;
    "kind")
        if command -v kind &> /dev/null; then
            echo "🔄 Loading image to kind cluster..."
            kind load docker-image "$IMAGE_NAME" --name "$(echo $CLUSTER_NAME | sed 's/kind-//')" || true
        fi
        ;;
    "minikube")
        if command -v minikube &> /dev/null; then
            echo "🔄 Loading image to minikube..."
            minikube image load "$IMAGE_NAME" || true
        fi
        ;;
    *)
        echo "⚠️  Unknown cluster type - skipping image loading"
        echo "   Make sure your image is available in a registry the cluster can access"
        ;;
esac

# Install CRDs
echo "📋 Installing Custom Resource Definitions..."
make install
echo "✅ CRDs installed successfully"
echo

# Deploy operator
echo "🚀 Deploying DevServer operator..."

# Create temporary deployment with correct image settings
TEMP_DEPLOY=$(mktemp -t operator-deploy.XXXXXX.yaml)
make build-installer IMG="$IMAGE_NAME"

# Use the generated installer but patch for local clusters
cp dist/install.yaml "$TEMP_DEPLOY"

# Update imagePullPolicy for local clusters
if [[ "$CLUSTER_TYPE" == "k3d" || "$CLUSTER_TYPE" == "kind" || "$CLUSTER_TYPE" == "minikube" ]]; then
    echo "  (Using imagePullPolicy: Never for local cluster)"
    # Add imagePullPolicy: Never after the image line for local clusters
    # More robust approach: replace image line with image + imagePullPolicy
    sed -i '' 's|image: devserver-operator:latest|image: devserver-operator:latest\
        imagePullPolicy: Never|' "$TEMP_DEPLOY"
fi

kubectl apply -f "$TEMP_DEPLOY"
echo "✅ Operator deployed successfully"
echo

# Wait for operator to be ready
echo "⏳ Waiting for operator to be ready..."
if ! kubectl rollout status deployment/devserver-operator-controller-manager -n "$NAMESPACE" --timeout=300s; then
    echo
    echo "❌ Operator deployment failed or timed out!"
    echo
    echo "🔍 Quick diagnostics:"
    echo "Pod status:"
    kubectl get pods -n "$NAMESPACE"
    echo
    echo "Recent events:"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -5
    echo
    echo "💡 Common fixes:"
    echo "  • Image pull issues: Try rebuilding with make docker-build"
    echo "  • Stuck resources: Run with --force-cleanup flag"
    echo "  • Check logs: kubectl logs -f deployment/devserver-operator-controller-manager -n $NAMESPACE"
    echo
    exit 1
fi

echo "✅ Operator is ready!"
echo

# Deploy default DevServerFlavors (cluster-scoped)
echo "📝 Creating default DevServerFlavors..."

# Create default flavors with sensible local development configurations
kubectl apply -f - <<EOF
apiVersion: apps.devservers.io/v1
kind: DevServerFlavor
metadata:
  name: cpu-small
  labels:
    devserver.io/managed-by: "deploy-script"
    devserver.io/default: "true"
spec:
  resources:
    requests:
      memory: 512Mi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 2
---
apiVersion: apps.devservers.io/v1
kind: DevServerFlavor
metadata:
  name: cpu-medium
  labels:
    devserver.io/managed-by: "deploy-script"
    devserver.io/default: "true"
spec:
  resources:
    requests:
      memory: 2Gi
      cpu: 1
    limits:
      memory: 8Gi
      cpu: 4
---
apiVersion: apps.devservers.io/v1
kind: DevServerFlavor
metadata:
  name: cpu-large
  labels:
    devserver.io/managed-by: "deploy-script"
    devserver.io/default: "true"
spec:
  resources:
    requests:
      memory: 4Gi
      cpu: 2
    limits:
      memory: 16Gi
      cpu: 8
EOF

echo "✅ Default DevServerFlavors created"
echo

# Show status
echo "📊 Operator Status:"
kubectl get all -n "$NAMESPACE"
echo

echo "🎯 Testing Instructions:"
echo "  Check DevServer status: kubectl describe devserver mydev"
echo "  Access development environment: kubectl exec -it deployment/mydev -- bash"
echo "  Watch reconciliation: kubectl logs -f deployment/devserver-operator-controller-manager -n $NAMESPACE"
echo "  Delete test resources: kubectl delete devserver mydev && kubectl delete devserverflavor cpu-small"
echo "  Cleanup operator: kubectl delete namespace $NAMESPACE"
echo

echo "🎉 DevServer Operator deployment complete!"
