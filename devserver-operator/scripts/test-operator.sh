#!/bin/bash

# Test script for DevServer operator - Phase 3
# Validates operator functionality and DevServer creation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
NAMESPACE="devserver-operator-system"
TEST_TIMEOUT=120

echo "🧪 Testing DevServer Operator - Phase 3"
echo "Project root: $PROJECT_ROOT"
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
echo

# Test 1: Check operator is running
echo "🔍 Test 1: Checking operator deployment..."
if ! kubectl get deployment devserver-operator-controller-manager -n "$NAMESPACE" &>/dev/null; then
    echo "❌ Operator deployment not found. Run 'make deploy' first."
    exit 1
fi

if ! kubectl rollout status deployment/devserver-operator-controller-manager -n "$NAMESPACE" --timeout=30s; then
    echo "❌ Operator is not ready. Check logs with:"
    echo "   kubectl logs -f deployment/devserver-operator-controller-manager -n $NAMESPACE"
    exit 1
fi
echo "✅ Operator is running and ready"
echo

# Test 2: Check CRDs are installed
echo "🔍 Test 2: Checking Custom Resource Definitions..."
if ! kubectl get crd devservers.apps.devservers.io &>/dev/null; then
    echo "❌ DevServer CRD not found. Run 'make install' first."
    exit 1
fi

if ! kubectl get crd devserverflavors.apps.devservers.io &>/dev/null; then
    echo "❌ DevServerFlavor CRD not found. Run 'make install' first."
    exit 1
fi
echo "✅ CRDs are installed correctly"
echo

# Test 3: Check sample resources exist
echo "🔍 Test 3: Checking sample DevServerFlavor..."
if ! kubectl get devserverflavor cpu-small &>/dev/null; then
    echo "❌ Sample DevServerFlavor 'cpu-small' not found."
    echo "   Apply with: kubectl apply -f config/samples/devservers_v1_devserverflavor.yaml"
    exit 1
fi
echo "✅ DevServerFlavor 'cpu-small' exists"

echo "🔍 Test 4: Checking sample DevServer..."
if ! kubectl get devserver mydev &>/dev/null; then
    echo "❌ Sample DevServer 'mydev' not found."
    echo "   Apply with: kubectl apply -f config/samples/devservers_v1_devserver.yaml"
    exit 1
fi
echo "✅ DevServer 'mydev' exists"
echo

# Test 5: Wait for DevServer to be ready
echo "🔍 Test 5: Waiting for DevServer to be ready..."
echo "  → Waiting up to ${TEST_TIMEOUT}s for pod to be running..."

for i in $(seq 1 $TEST_TIMEOUT); do
    POD_STATUS=$(kubectl get pods -l app=devserver -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")
    POD_READY=$(kubectl get pods -l app=devserver -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
    
    if [ "$POD_STATUS" = "Running" ] && [ "$POD_READY" = "True" ]; then
        echo "✅ DevServer pod is running and ready!"
        break
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        echo "  → Still waiting... (${i}s) Pod status: $POD_STATUS"
    fi
    
    sleep 1
done

if [ "$POD_STATUS" != "Running" ] || [ "$POD_READY" != "True" ]; then
    echo "❌ DevServer pod failed to become ready after ${TEST_TIMEOUT}s"
    echo
    echo "🔍 Diagnostics:"
    kubectl get pods -l app=devserver
    echo
    kubectl describe devserver mydev
    exit 1
fi
echo

# Test 6: Check created resources
echo "🔍 Test 6: Verifying created resources..."

# Check PVC
if ! kubectl get pvc mydev-home &>/dev/null; then
    echo "❌ PVC 'mydev-home' not created"
    exit 1
fi
echo "  ✅ PVC 'mydev-home' exists"

# Check Service
if ! kubectl get service mydev-ssh &>/dev/null; then
    echo "❌ Service 'mydev-ssh' not created"
    exit 1
fi
echo "  ✅ Service 'mydev-ssh' exists"

# Check Deployment
if ! kubectl get deployment mydev &>/dev/null; then
    echo "❌ Deployment 'mydev' not created"
    exit 1
fi
echo "  ✅ Deployment 'mydev' exists"
echo

# Test 7: Test container access
echo "🔍 Test 7: Testing container access..."
POD_NAME=$(kubectl get pods -l app=devserver -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "❌ No DevServer pod found"
    exit 1
fi

echo "  → Testing command execution in pod: $POD_NAME"
if ! kubectl exec "$POD_NAME" -- whoami &>/dev/null; then
    echo "❌ Cannot execute commands in DevServer pod"
    exit 1
fi

USER_IN_POD=$(kubectl exec "$POD_NAME" -- whoami 2>/dev/null)
echo "  ✅ Command execution works! Running as: $USER_IN_POD"

# Test volume mount
echo "  → Testing volume mounts..."
if ! kubectl exec "$POD_NAME" -- ls -la /home/dev &>/dev/null; then
    echo "❌ Home directory volume not mounted correctly"
    exit 1
fi
echo "  ✅ Home directory volume mounted at /home/dev"
echo

# Test 8: Check DevServer status
echo "🔍 Test 8: Checking DevServer status..."
DEV_SERVER_PHASE=$(kubectl get devserver mydev -o jsonpath='{.status.phase}' 2>/dev/null)
DEV_SERVER_READY=$(kubectl get devserver mydev -o jsonpath='{.status.ready}' 2>/dev/null)

if [ "$DEV_SERVER_PHASE" != "Running" ]; then
    echo "❌ DevServer phase is '$DEV_SERVER_PHASE', expected 'Running'"
    kubectl describe devserver mydev
    exit 1
fi

if [ "$DEV_SERVER_READY" != "true" ]; then
    echo "❌ DevServer ready status is '$DEV_SERVER_READY', expected 'true'"
    kubectl describe devserver mydev
    exit 1
fi

echo "✅ DevServer status is healthy (Phase: $DEV_SERVER_PHASE, Ready: $DEV_SERVER_READY)"
echo

# Summary
echo "🎉 All Tests Passed!"
echo
echo "📊 Final Status:"
echo "  Operator: $(kubectl get deployment devserver-operator-controller-manager -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')/$(kubectl get deployment devserver-operator-controller-manager -n "$NAMESPACE" -o jsonpath='{.spec.replicas}') ready"
echo "  DevServer: $DEV_SERVER_PHASE and ready"
echo "  Pod: $POD_NAME running"
echo "  Resources: PVC + Deployment + Service created"
echo
echo "🔗 Next Steps:"
echo "  • Access dev environment: kubectl exec -it $POD_NAME -- bash"
echo "  • Check operator logs: kubectl logs -f deployment/devserver-operator-controller-manager -n $NAMESPACE"
echo "  • View DevServer status: kubectl describe devserver mydev"
echo "  • Cleanup: kubectl delete devserver mydev"
echo
echo "✅ DevServer Operator is fully functional!"
