#!/bin/bash
#
# Generates a kubeconfig file for a given DevServerUser by creating a token
# for the user's operator-managed ServiceAccount.
#
# Usage:
#   ./scripts/generate-user-kubeconfig.sh <devserver-user-name>
#
# Example:
#   ./scripts/generate-user-kubeconfig.sh test-user > test-user.kubeconfig
#   export KUBECONFIG=./test-user.kubeconfig
#   kubectl get pods

set -euo pipefail

USERNAME=$1
if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <devserver-user-name>"
    exit 1
fi

# --- 1. Get User's Namespace ---
echo "🔎 Fetching namespace for user '$USERNAME'..." >&2
NAMESPACE=$(kubectl get devserveruser "$USERNAME" -o jsonpath='{.status.namespace}')
if [ -z "$NAMESPACE" ]; then
    echo "❌ Error: Could not find namespace in DevServerUser '$USERNAME'. Is the operator running and the user created?" >&2
    exit 1
fi
echo "✅ Found namespace: $NAMESPACE" >&2

# --- 2. Get Cluster Info and Token ---
SA_NAME="$USERNAME-sa"
echo "🔑 Generating token for ServiceAccount '$SA_NAME' and fetching cluster info..." >&2
TOKEN=$(kubectl create token "$SA_NAME" -n "$NAMESPACE")
if [ -z "$TOKEN" ]; then
    echo "❌ Error: Failed to create token for ServiceAccount '$SA_NAME'." >&2
    echo "   Please ensure the ServiceAccount exists and you have permission to create tokens." >&2
    exit 1
fi

CURRENT_CONTEXT=$(kubectl config current-context)
CURRENT_CLUSTER=$(kubectl config view -o jsonpath="{.contexts[?(@.name==\"$CURRENT_CONTEXT\")].context.cluster}")
SERVER=$(kubectl config view -o jsonpath="{.clusters[?(@.name==\"$CURRENT_CLUSTER\")].cluster.server}")
CA_DATA=$(kubectl config view --raw -o jsonpath="{.clusters[?(@.name==\"$CURRENT_CLUSTER\")].cluster.certificate-authority-data}")

# --- 3. Generate Kubeconfig ---
echo "📄 Assembling kubeconfig..." >&2

cat <<EOF
apiVersion: v1
kind: Config
current-context: $USERNAME
clusters:
- name: $CURRENT_CLUSTER
  cluster:
    server: $SERVER
    certificate-authority-data: $CA_DATA
contexts:
- name: $USERNAME
  context:
    cluster: $CURRENT_CLUSTER
    namespace: $NAMESPACE
    user: $USERNAME
users:
- name: $USERNAME
  user:
    token: $TOKEN
EOF

echo "✅ Kubeconfig generated successfully for user '$USERNAME'." >&2
echo "   - To use, redirect output to a file: $0 $USERNAME > $USERNAME.kubeconfig" >&2
echo "   - Then run: export KUBECONFIG=\$PWD/$USERNAME.kubeconfig" >&2
