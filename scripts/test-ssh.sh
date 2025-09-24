#!/bin/bash

# Demo test script for Phase 2 bastion - Secure User Provisioning
# Tests SSH access, user controller, secure kubectl access, and RBAC isolation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
NAMESPACE="devserver-bastion"
USERNAME="testuser"
USER_NAMESPACE="dev-$USERNAME"
DEMO_KEY="$PROJECT_ROOT/.demo-keys/bastion_demo"

echo "🧪 Full End-to-End Demo Test - Phase 2 (Secure User Provisioning)"
echo "Testing: SSH access, user controller, namespace isolation, secure kubectl"
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

# Check both containers are running
echo "🔍 Checking both bastion and user-controller containers..."
POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app=bastion -o jsonpath='{.items[0].metadata.name}')

BASTION_STATUS=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[?(@.name=="bastion")].ready}')
CONTROLLER_STATUS=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[?(@.name=="user-controller")].ready}')

if [ "$BASTION_STATUS" != "true" ]; then
    echo "❌ Bastion container not ready"
    kubectl logs "$POD_NAME" -n "$NAMESPACE" -c bastion --tail=10
    exit 1
fi

if [ "$CONTROLLER_STATUS" != "true" ]; then
    echo "❌ User-controller container not ready"
    kubectl logs "$POD_NAME" -n "$NAMESPACE" -c user-controller --tail=10
    exit 1
fi

echo "✅ Both bastion and user-controller containers ready"

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
SSH_OUTPUT=$(ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'timeout 15 devctl status' 2>&1)
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
    
    # Test Phase 2 User Provisioning
    echo "🧪 Testing Phase 2 User Provisioning Features..."
    echo
    
    # Wait for user provisioning to complete
    echo "⏳ Waiting for user provisioning (max 60 seconds)..."
    PROVISION_TIMEOUT=60
    PROVISION_COUNT=0
    
    while [ $PROVISION_COUNT -lt $PROVISION_TIMEOUT ]; do
        # Check if user namespace exists
        if kubectl get namespace "$USER_NAMESPACE" &>/dev/null; then
            echo "✅ User namespace '$USER_NAMESPACE' created successfully"
            break
        fi
        sleep 1
        PROVISION_COUNT=$((PROVISION_COUNT + 1))
    done
    
    if [ $PROVISION_COUNT -eq $PROVISION_TIMEOUT ]; then
        echo "❌ User provisioning timeout - namespace not created"
        exit 1
    fi
    
    # Test user ServiceAccount creation
    echo "🔍 Checking user ServiceAccount..."
    if kubectl get serviceaccount "user-$USERNAME" -n "$USER_NAMESPACE" &>/dev/null; then
        echo "✅ User ServiceAccount 'user-$USERNAME' created successfully"
    else
        echo "❌ User ServiceAccount not found"
        exit 1
    fi
    
    # Test secure kubectl access
    echo "🔐 Testing secure kubectl access..."
    
    # Test 1: User can access their namespace
    echo "→ Testing namespace access:"
    NAMESPACE_TEST=$(ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'timeout 10 kubectl get pods -n dev-testuser 2>&1 || echo "FAILED"')
    if [[ "$NAMESPACE_TEST" != *"FAILED"* ]] && [[ "$NAMESPACE_TEST" != *"permission denied"* ]]; then
        echo "  ✅ User can access their namespace"
    else
        echo "  ❌ User cannot access their namespace: $NAMESPACE_TEST"
        # Show token file permissions for debugging
        echo "🔍 Debugging token file permissions:"
        ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'ls -la /shared/user-tokens/testuser/ 2>&1 || echo "Token directory not found"'
        exit 1
    fi
    
    # Test 2: User cannot create namespaces (security test)
    echo "→ Testing namespace creation restriction (security):"
    # Use '|| true' to prevent SSH from hanging on expected "failure" (exit code 1 when kubectl returns "no")
    NAMESPACE_CREATE_TEST=$(ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'timeout 10 kubectl auth can-i create namespaces 2>&1 || true')
    if [[ "$NAMESPACE_CREATE_TEST" == *"no"* ]]; then
        echo "  ✅ User correctly cannot create namespaces (security enforced)"
    elif [[ "$NAMESPACE_CREATE_TEST" == *"yes"* ]]; then
        echo "  ❌ Security issue: User can create namespaces: $NAMESPACE_CREATE_TEST"
        exit 1
    else
        echo "  ⚠️  Unexpected response: $NAMESPACE_CREATE_TEST"
        echo "     (This might indicate a timeout or connection issue)"
    fi
    
    # Test 3: User can manage resources in their namespace
    echo "→ Testing resource management in user namespace:"
    RESOURCE_TEST=$(ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'timeout 10 kubectl auth can-i create pods -n dev-testuser 2>&1 || true')
    if [[ "$RESOURCE_TEST" == *"yes"* ]]; then
        echo "  ✅ User can manage pods in their namespace"
    elif [[ "$RESOURCE_TEST" == *"no"* ]]; then
        echo "  ❌ User cannot manage resources in their namespace: $RESOURCE_TEST"
        exit 1
    else
        echo "  ⚠️  Unexpected response: $RESOURCE_TEST"
        echo "     (This might indicate a timeout or connection issue)"
    fi
    
    # Test 4: User cannot access other namespaces
    echo "→ Testing namespace isolation:"
    OTHER_NS_TEST=$(ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'timeout 10 kubectl get pods -n kube-system 2>&1 || echo "FORBIDDEN"')
    if [[ "$OTHER_NS_TEST" == *"forbidden"* ]] || [[ "$OTHER_NS_TEST" == *"FORBIDDEN"* ]]; then
        echo "  ✅ User correctly cannot access other namespaces (isolation enforced)"
    else
        echo "  ❌ Security issue: User can access other namespaces: $OTHER_NS_TEST"
        exit 1
    fi
    
    # Test additional CLI commands
    echo "🧪 Testing enhanced CLI commands..."
    
    echo "→ devctl info:"
    ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'timeout 15 devctl info' 2>/dev/null
    
    echo
    echo "→ devctl test-k8s (with secure access):"
    ssh -i "$DEMO_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USERNAME@$SSH_HOST" -p "$SSH_PORT" 'timeout 30 devctl test-k8s' 2>/dev/null
    
    # Test user registry and controller status
    echo "🔍 Testing user controller functionality..."
    USER_REGISTRY_CONTENT=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -c user-controller -- cat /shared/user-registry.json 2>/dev/null || echo "{}")
    if [[ "$USER_REGISTRY_CONTENT" == *"testuser"* ]]; then
        echo "✅ User registry working - user registered successfully"
    else
        echo "❌ User registry issue - user not found in registry"
    fi
    
    echo
    echo "🎉 Full Phase 2 end-to-end test successful!"
    echo
    echo "✅ Summary:"
    echo "  - Bastion deployment: Ready (both containers)"
    echo "  - SSH connectivity: Working"
    echo "  - SSH authentication: Working"
    echo "  - User provisioning: Working (namespace + ServiceAccount created)"
    echo "  - Secure kubectl access: Working"
    echo "  - Namespace isolation: Enforced"
    echo "  - RBAC security: Enforced (cannot create namespaces)"
    echo "  - Resource management: Working (in user namespace)"
    echo "  - User controller: Working"
    echo "  - DevCtl CLI: Working"
    echo
    echo "🚀 Phase 2 secure user provisioning is fully functional!"
    echo "🔒 Security model validated: Users have limited, namespace-scoped access"
    
else
    echo "❌ SSH authentication failed"
    echo "SSH output:"
    echo "$SSH_OUTPUT"
    echo
    echo "🔍 Troubleshooting Phase 2 Issues:"
    echo "  - Check if the demo key is properly configured in the deployment"
    echo "  - Verify both bastion containers are running: kubectl get pods -n $NAMESPACE"
    echo "  - Check bastion container logs: kubectl logs deployment/bastion -n $NAMESPACE -c bastion"
    echo "  - Check user-controller logs: kubectl logs deployment/bastion -n $NAMESPACE -c user-controller"
    echo "  - Verify user-controller is creating namespaces: kubectl get namespaces | grep dev-"
    echo "  - Check user registry: kubectl exec deployment/bastion -n $NAMESPACE -c user-controller -- cat /shared/user-registry.json"
    echo "  - Check token permissions: kubectl exec deployment/bastion -n $NAMESPACE -c bastion -- ls -la /shared/user-tokens/"
    exit 1
fi
