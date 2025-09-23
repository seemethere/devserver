#!/bin/bash

# DevServer Environment Setup - Phase 1
# Sourced by bash/shell for all users

# Set environment variables for devctl
export DEVCTL_PHASE="1"
export DEVCTL_VERSION="0.1.0-phase1"
export DEVCTL_CLUSTER_NAME="${CLUSTER_NAME:-development}"

# Default user namespace (automatically scoped)
export DEVCTL_USER_NAMESPACE="dev-$(whoami)"

# Color support for CLI
export FORCE_COLOR=1
export TERM="${TERM:-xterm-256color}"

# Kubernetes context and namespace
if [ -f ~/.kube/config ]; then
    # Set default namespace to user's dev namespace
    export KUBECONFIG=~/.kube/config
    
    # Helper alias to quickly switch to user namespace
    alias k="kubectl -n \$DEVCTL_USER_NAMESPACE"
    alias kubectl-dev="kubectl -n \$DEVCTL_USER_NAMESPACE"
fi

# Helpful aliases
alias ll='ls -la'
alias la='ls -la'
alias dev='devctl'

# Quick status function
function dev-status() {
    echo "🚀 DevServer Platform Status"
    echo "User: $(whoami)"
    echo "Namespace: $DEVCTL_USER_NAMESPACE"
    echo "Phase: $DEVCTL_PHASE"
    echo
    devctl status
}

# Quick help function
function dev-help() {
    echo "🔧 Quick DevServer Commands:"
    echo "  devctl status    - Show full environment status"
    echo "  devctl info      - List all available commands"
    echo "  devctl test-k8s  - Test Kubernetes connectivity"
    echo "  dev-status       - Quick status summary"
    echo "  k get pods       - List pods in your namespace"
    echo
    echo "📚 Use 'devctl --help' for detailed help"
}

# Show quick welcome message (shorter than MOTD)
if [ -n "$PS1" ] && [ -z "$DEVCTL_WELCOME_SHOWN" ]; then
    export DEVCTL_WELCOME_SHOWN=1
    echo
    echo "🚀 Welcome to PyTorch DevServer Bastion (Phase 1)"
    echo "   Type 'dev-help' for quick commands or 'devctl info' for full help"
    echo
fi
