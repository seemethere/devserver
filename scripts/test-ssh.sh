#!/bin/bash

# Demo test script for Phase 1 bastion
# Uses the demo SSH key to fully test end-to-end functionality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
NAMESPACE="devserver-bastion"
USERNAME="testuser"
DEMO_KEY="$PROJECT_ROOT/.demo-keys/bastion_demo"

echo "🧪 Full End-to-End Demo Test - Phase 1"
echo "Using demo SSH key for authentication"
echo

# Auto-generate demo key if it doesn't exist
if [ ! -f "$DEMO_KEY" ]; then
    echo "🔑 Generating demo SSH key for testing..."
    mkdir -p "$(dirname "$DEMO_KEY")"
    ssh-keygen -t rsa -b 2048 -f "$DEMO_KEY" -N '' -C 'bastion-demo-key'
    echo "✅ Demo SSH key generated at $DEMO_KEY"
    echo
fi

# Check if deployment is ready
echo "🔍 Checking bastion deployment..."
if ! kubectl get deployment bastion -n "$NAMESPACE" &>/dev/null; then
    echo "❌ Bastion deployment not found. Please run ./scripts/deploy-bastion.sh first."
    exit 1
fi

READY_REPLICAS=$(kubectl get deployment bastion -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
DESIRED_REPLICAS=$(kubectl get deployment bastion -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')

if [ "$READY_REPLICAS" != "$DESIRED_REPLICAS" ]; then
    echo "❌ Bastion deployment not ready ($READY_REPLICAS/$DESIRED_REPLICAS replicas)"
    exit 1
fi

echo "✅ Bastion deployment ready ($READY_REPLICAS/$DESIRED_REPLICAS replicas)"

# Detect cluster type for connection method
CLUSTER_NAME=$(kubectl config current-context)
if [[ "$CLUSTER_NAME" == k3d-* ]] || [[ "$CLUSTER_NAME" == kind-* ]]; then
    echo "🌐 Local cluster detected - setting up port-forward..."
    
    # Start port-forward in background
    kubectl port-forward service/bastion -n "$NAMESPACE" 2222:22 &
    PF_PID=$!
    
    # Cleanup function
    cleanup() {
        if [ -n "$PF_PID" ]; then
            echo "🧹 Stopping port-forward..."
            kill $PF_PID 2>/dev/null || true
        fi
    }
    trap cleanup EXIT
    
    # Wait for port-forward to be ready
    echo "⏳ Waiting for port-forward to be ready..."
    sleep 3
    
    SSH_HOST="localhost"
    SSH_PORT="2222"
else
    echo "🌐 Production cluster detected - using LoadBalancer..."
    # For production clusters, try to get LoadBalancer IP/hostname
    LB_IP=$(kubectl get service bastion -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    LB_HOSTNAME=$(kubectl get service bastion -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    
    if [ -n "$LB_IP" ] && [ "$LB_IP" != "null" ]; then
        SSH_HOST="$LB_IP"
        SSH_PORT="22"
    elif [ -n "$LB_HOSTNAME" ] && [ "$LB_HOSTNAME" != "null" ]; then
        SSH_HOST="$LB_HOSTNAME"
        SSH_PORT="22"
    else
        echo "❌ LoadBalancer not ready. Using port-forward as fallback..."
        kubectl port-forward service/bastion -n "$NAMESPACE" 2222:22 &
        PF_PID=$!
        trap 'kill $PF_PID 2>/dev/null || true' EXIT
        sleep 3
        SSH_HOST="localhost"
        SSH_PORT="2222"
    fi
fi

echo "🔗 Testing SSH connection to $SSH_HOST:$SSH_PORT"

# Test basic SSH connectivity
echo "🔌 Testing basic SSH connectivity..."
if ! timeout 10 bash -c "</dev/tcp/$SSH_HOST/$SSH_PORT"; then
    echo "❌ Cannot reach SSH port"
    exit 1
fi
echo "✅ SSH port reachable"

# Test SSH authentication and devctl CLI
echo "🔐 Testing SSH authentication and devctl CLI..."
echo "Command: ssh -i $DEMO_KEY -o ConnectTimeout=10 -o StrictHostKeyChecking=no $USERNAME@$SSH_HOST -p $SSH_PORT 'devctl status'"

echo "🔍 Running SSH command..."
SSH_OUTPUT=$(ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'devctl status' 2>&1)
SSH_EXIT_CODE=$?

echo "SSH exit code: $SSH_EXIT_CODE"
if [ $SSH_EXIT_CODE -ne 0 ]; then
    echo "SSH output:"
    echo "$SSH_OUTPUT"
fi

if [ $SSH_EXIT_CODE -eq 0 ]; then
    echo "✅ SSH authentication successful!"
    echo
    echo "📋 DevCtl CLI Output:"
    echo "$SSH_OUTPUT"
    echo
    
    # Test additional commands
    echo "🧪 Testing additional CLI commands..."
    
    echo "→ devctl info:"
    ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'devctl info' 2>/dev/null
    
    echo
    echo "→ devctl test-k8s:"
    ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'devctl test-k8s' 2>/dev/null
    
    echo
    echo "🎉 Full end-to-end test successful!"
    echo
    echo "✅ Summary:"
    echo "  - Bastion deployment: Ready"
    echo "  - SSH connectivity: Working"
    echo "  - SSH authentication: Working"
    echo "  - DevCtl CLI: Working"
    echo "  - Kubernetes access: Working"
    echo
    echo "🚀 Phase 1 bastion infrastructure is fully functional!"
    
else
    echo "❌ SSH authentication failed"
    echo "SSH output:"
    echo "$SSH_OUTPUT"
    echo
    echo "🔍 Troubleshooting:"
    echo "  - Check if the demo key is properly configured in the deployment"
    echo "  - Verify the bastion pods are running: kubectl get pods -n $NAMESPACE"
    echo "  - Check bastion logs: kubectl logs -f deployment/bastion -n $NAMESPACE"
    exit 1
fi
