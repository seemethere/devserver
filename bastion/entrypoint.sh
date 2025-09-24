#!/bin/bash

# Bastion server entrypoint - Phase 2
# Handles dynamic user creation and SSH setup with secure token management

set -e

echo "Starting Bastion Server - Phase 2 (Secure User Provisioning)"

# SSH host keys are generated during build, just verify they exist
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    echo "Warning: SSH host keys missing, SSH may not work properly"
fi

# Create shared directories for user controller communication
mkdir -p /shared/user-tokens
chmod 755 /shared

# Phase 2: Handle test user (for development)
USERNAME="${BASTION_TEST_USER:-testuser}"

echo "Setting up SSH access for user: $USERNAME (Phase 2 - secure provisioning)"

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

# Register user with controller for provisioning
register_user() {
    local username="$1"
    echo "Registering user: $username"
    
    # Create or update user registry
    python3 << EOF
import json
import os
from datetime import datetime

registry_file = "/shared/user-registry.json"
registry = {}

# Load existing registry
if os.path.exists(registry_file):
    try:
        with open(registry_file, 'r') as f:
            registry = json.load(f)
    except:
        pass

# Add/update user
now = datetime.utcnow().isoformat() + 'Z'
if "$username" not in registry:
    registry["$username"] = {
        "firstSeen": now,
        "status": "pending"
    }

registry["$username"]["lastLogin"] = now

# Save registry
with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)

print(f"User $username registered successfully")
EOF
}

# Wait for user provisioning
wait_for_provisioning() {
    local username="$1"
    local max_wait=60  # 60 seconds timeout
    local count=0
    
    echo "Waiting for user $username to be provisioned..."
    
    while [ $count -lt $max_wait ]; do
        # Check if token file exists
        if [ -f "/shared/user-tokens/$username/token" ]; then
            echo "User $username provisioned successfully!"
            return 0
        fi
        
        # Check registry status
        status=$(python3 -c "
import json
try:
    with open('/shared/user-registry.json', 'r') as f:
        registry = json.load(f)
    print(registry.get('$username', {}).get('status', 'unknown'))
except:
    print('unknown')
")
        
        if [ "$status" = "failed" ]; then
            echo "ERROR: User provisioning failed"
            return 1
        fi
        
        sleep 1
        count=$((count + 1))
    done
    
    echo "ERROR: Timeout waiting for user provisioning"
    return 1
}

# Setup secure kubectl config for user
setup_user_kubeconfig() {
    local username="$1"
    local kube_dir="/home/$username/.kube"
    
    echo "Setting up secure kubeconfig for $username"
    
    # Create .kube directory
    mkdir -p "$kube_dir"
    chown "$username:$username" "$kube_dir"
    
    # Wait for user token to be available
    if ! wait_for_provisioning "$username"; then
        echo "WARNING: Failed to provision $username, using fallback config"
        return 1
    fi
    
    # Create secure kubeconfig using user's ServiceAccount token
    cat > "$kube_dir/config" << EOF
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
    namespace: dev-$username
    user: user-$username
  name: default-context
current-context: default-context
users:
- name: user-$username
  user:
    tokenFile: /shared/user-tokens/$username/token
EOF
    
    chown "$username:$username" "$kube_dir/config"
    chmod 600 "$kube_dir/config"
    
    echo "Secure kubeconfig created for $username"
}

# Register user and setup secure access
register_user "$USERNAME"
setup_user_kubeconfig "$USERNAME"

echo "Bastion setup complete - Phase 2"

# Execute the main command
exec "$@"
