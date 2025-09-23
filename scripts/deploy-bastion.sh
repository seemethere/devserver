#!/bin/bash

# Deploy script for bastion - Phase 1
# Quick deployment script for development and testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
IMAGE_NAME="devserver/bastion:phase1"
NAMESPACE="devserver-bastion"

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

# Temporary file for local deployment modifications
TEMP_DEPLOYMENT=""

# Cleanup function
cleanup() {
    if [ -n "$TEMP_DEPLOYMENT" ] && [ -f "$TEMP_DEPLOYMENT" ]; then
        echo "🧹 Cleaning up temporary files..."
        rm -f "$TEMP_DEPLOYMENT"
    fi
}

# Set trap for cleanup on exit/error
trap cleanup EXIT

# Kubernetes cleanup functions
cleanup_k8s_resources() {
    echo "🧹 Cleaning up existing Kubernetes resources..."
    
    # Delete deployment (this will clean up pods)
    if kubectl get deployment bastion -n "$NAMESPACE" &>/dev/null; then
        echo "  → Deleting existing deployment..."
        kubectl delete deployment bastion -n "$NAMESPACE" --ignore-not-found=true
    fi
    
    # Clean up stuck pods if force cleanup is requested
    if [ "$FORCE_CLEANUP" = true ]; then
        echo "  → Force cleaning stuck pods..."
        kubectl delete pods -n "$NAMESPACE" --field-selector=status.phase=Failed --ignore-not-found=true
        kubectl delete pods -n "$NAMESPACE" --field-selector=status.phase=Pending --ignore-not-found=true
        
        # Force delete any remaining pods
        if kubectl get pods -n "$NAMESPACE" 2>/dev/null | grep -q bastion; then
            echo "  → Force deleting remaining bastion pods..."
            kubectl delete pods -n "$NAMESPACE" -l app=bastion --grace-period=0 --force --ignore-not-found=true
        fi
    fi
    
    # Clean up old ReplicaSets
    echo "  → Cleaning up old ReplicaSets..."
    kubectl delete replicasets -n "$NAMESPACE" -l app=bastion --ignore-not-found=true
    
    # Wait for cleanup to complete
    echo "  → Waiting for cleanup to complete..."
    kubectl wait --for=delete pods -n "$NAMESPACE" -l app=bastion --timeout=30s 2>/dev/null || true
    
    echo "✅ Cleanup complete!"
}

echo "🚀 Deploying Bastion - Phase 1"
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

# Generate demo SSH key for testing if it doesn't exist
DEMO_KEY_DIR="$PROJECT_ROOT/.demo-keys"
DEMO_KEY="$DEMO_KEY_DIR/bastion_demo"
DEMO_PUBLIC_KEY=""

if [ ! -f "$DEMO_KEY" ]; then
    echo "🔑 Generating demo SSH key for testing..."
    mkdir -p "$DEMO_KEY_DIR"
    ssh-keygen -t rsa -b 2048 -f "$DEMO_KEY" -N '' -C 'bastion-demo-key'
    echo "✅ Demo SSH key generated for testing"
fi

# Read the public key for deployment
if [ -f "$DEMO_KEY.pub" ]; then
    DEMO_PUBLIC_KEY=$(cat "$DEMO_KEY.pub")
    echo "📋 Using demo public key: ${DEMO_PUBLIC_KEY:0:50}..."
fi
echo

# Handle image loading based on cluster type
case "$CLUSTER_TYPE" in
    "eks")
        echo "🏗️  EKS detected - you need to push image to ECR first!"
        echo "   Quick setup:"
        echo "   1. aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com"
        echo "   2. docker tag $IMAGE_NAME <account>.dkr.ecr.<region>.amazonaws.com/$IMAGE_NAME"
        echo "   3. docker push <account>.dkr.ecr.<region>.amazonaws.com/$IMAGE_NAME"
        echo "   4. Update bastion/k8s/deployment.yaml with ECR image URI"
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

# Deploy Kubernetes resources
echo "📋 Applying Kubernetes manifests..."
cd "$PROJECT_ROOT"

# Apply in order
echo "  → Namespace..."
kubectl apply -f bastion/k8s/namespace.yaml

echo "  → RBAC..."
kubectl apply -f bastion/k8s/rbac.yaml

echo "  → Deployment..."
# Create temporary deployment file with correct imagePullPolicy and SSH key
TEMP_DEPLOYMENT=$(mktemp -t bastion-deployment.XXXXXX.yaml)

# Start with the base deployment
cp bastion/k8s/deployment.yaml "$TEMP_DEPLOYMENT"

# Update imagePullPolicy for local clusters
if [[ "$CLUSTER_TYPE" == "k3d" || "$CLUSTER_TYPE" == "kind" || "$CLUSTER_TYPE" == "minikube" ]]; then
    echo "    (Using imagePullPolicy: Never for local cluster)"
    # Use portable sed syntax for both macOS and Linux
    sed -i '' 's/imagePullPolicy: Always/imagePullPolicy: Never/' "$TEMP_DEPLOYMENT"
fi

# Update SSH key if we have one
if [ -n "$DEMO_PUBLIC_KEY" ]; then
    echo "    (Using generated demo SSH key)"
    # Replace the placeholder with the actual SSH key (portable sed syntax)
    sed -i '' "s|DEMO_SSH_KEY_PLACEHOLDER|$DEMO_PUBLIC_KEY|" "$TEMP_DEPLOYMENT"
fi

kubectl apply -f "$TEMP_DEPLOYMENT"

echo "  → Service..."
kubectl apply -f bastion/k8s/service.yaml

echo
echo "⏳ Waiting for deployment to be ready..."
if ! kubectl rollout status deployment/bastion -n "$NAMESPACE" --timeout=300s; then
    echo
    echo "❌ Deployment failed or timed out!"
    echo
    echo "🔍 Quick diagnostics:"
    echo "Pod status:"
    kubectl get pods -n "$NAMESPACE" -l app=bastion
    echo
    echo "Recent pod events:"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -5
    echo
    echo "💡 Common fixes:"
    echo "  • Image pull issues: Try rebuilding with ./scripts/build-bastion.sh"
    echo "  • Stuck resources: Run with --force-cleanup flag"
    echo "  • Check logs: kubectl logs -f deployment/bastion -n $NAMESPACE"
    echo
    exit 1
fi

echo
echo "✅ Deployment complete!"
echo

# Show status
echo "📊 Deployment Status:"
kubectl get all -n "$NAMESPACE"

echo
echo "🌐 Service Information:"
kubectl get service bastion -n "$NAMESPACE" -o wide

# Show access instructions based on cluster type
echo
echo "🔗 Access Instructions:"
case "$CLUSTER_TYPE" in
    "eks")
        LB_HOSTNAME=$(kubectl get service bastion -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
        if [ -n "$LB_HOSTNAME" ] && [ "$LB_HOSTNAME" != "null" ]; then
            echo "  🎉 EKS LoadBalancer ready!"
            echo "  SSH command: ssh testuser@$LB_HOSTNAME"
            echo "  Hostname: $LB_HOSTNAME"
        else
            echo "  ⏳ AWS NLB is being created (this can take 2-3 minutes)..."
            echo "     Run: kubectl get service bastion -n $NAMESPACE -w"
            echo "     Once ready: ssh testuser@<nlb-hostname>"
        fi
        ;;
    "k3d")
        echo "  🎉 k3d cluster ready!"
        echo "  SSH command: ssh testuser@localhost -p 8022"
        echo "  (Assuming you created cluster with --port '8022:22@loadbalancer')"
        echo "  If not: kubectl port-forward service/bastion -n $NAMESPACE 2222:22"
        ;;
    *)
        LB_IP=$(kubectl get service bastion -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
        if [ -n "$LB_IP" ] && [ "$LB_IP" != "null" ]; then
            echo "  SSH command: ssh testuser@$LB_IP"
        else
            echo "  Use port-forward: kubectl port-forward service/bastion -n $NAMESPACE 2222:22"
            echo "  Then SSH: ssh testuser@localhost -p 2222"
        fi
        ;;
esac

echo
echo "🔧 Useful commands:"
echo "  Check pods: kubectl get pods -n $NAMESPACE"
echo "  View logs: kubectl logs -f deployment/bastion -n $NAMESPACE"
echo "  Port forward: kubectl port-forward service/bastion -n $NAMESPACE 2222:22"
echo "  Redeploy: $0 (always cleans up existing deployment)"
echo "  Force cleanup: $0 --force-cleanup (for stuck resources)"
echo "  Delete all: kubectl delete namespace $NAMESPACE"
