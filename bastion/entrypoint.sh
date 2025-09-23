#!/bin/bash

# Bastion server entrypoint - Phase 1
# Handles dynamic user creation and SSH setup

set -e

echo "Starting Bastion Server - Phase 1"

# SSH host keys are generated during build, just verify they exist
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    echo "Warning: SSH host keys missing, SSH may not work properly"
fi

# Phase 1: Handle single test user (user created during build)
# TODO Phase 2: Replace with dynamic user creation from ConfigMap
# TODO Phase 3: Replace with LDAP/IAM integration
USERNAME="${BASTION_TEST_USER:-testuser}"

echo "Setting up SSH access for user: $USERNAME (Phase 1 - single user only)"

# Setup SSH key if provided (for development)
if [ -n "$BASTION_TEST_SSH_KEY" ]; then
    echo "Setting up SSH key for $USERNAME"
    echo "$BASTION_TEST_SSH_KEY" > "/home/$USERNAME/.ssh/authorized_keys"
    chmod 600 "/home/$USERNAME/.ssh/authorized_keys"
    chown "$USERNAME:$USERNAME" "/home/$USERNAME/.ssh/authorized_keys"
    echo "SSH key configured successfully"
else
    echo "No SSH key provided in BASTION_TEST_SSH_KEY"
fi

# Setup kubectl config directory for the user
KUBE_DIR="/home/$USERNAME/.kube"
if [ ! -d "$KUBE_DIR" ]; then
    mkdir -p "$KUBE_DIR"
    chown "$USERNAME:$USERNAME" "$KUBE_DIR"
fi

# Copy kubeconfig if available (mounted from service account)
if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]; then
    echo "Setting up in-cluster kubeconfig for $USERNAME"
    
    cat > "$KUBE_DIR/config" << EOF
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    server: https://kubernetes.default.svc
  name: default-cluster
contexts:
- context:
    cluster: default-cluster
    namespace: dev-$USERNAME
    user: default-user
  name: default-context
current-context: default-context
users:
- name: default-user
  user:
    tokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
EOF
    
    chown "$USERNAME:$USERNAME" "$KUBE_DIR/config"
fi

echo "Bastion setup complete"

# Execute the main command
exec "$@"
