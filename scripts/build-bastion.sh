#!/bin/bash

# Build script for bastion container - Phase 1
# Quick iteration script for development and testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
IMAGE_NAME="devserver/bastion"
IMAGE_TAG="phase1"
FULL_IMAGE="$IMAGE_NAME:$IMAGE_TAG"

echo "🔨 Building Bastion Container - Phase 1"
echo "Project root: $PROJECT_ROOT"
echo "Image: $FULL_IMAGE"
echo

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

# Build the container
echo "📦 Building container image..."
cd "$PROJECT_ROOT"

docker build \
    -t "$FULL_IMAGE" \
    -f bastion/Dockerfile \
    .

echo
echo "✅ Build complete!"
echo "Image: $FULL_IMAGE"
echo

# Show image info
echo "📋 Image Information:"
docker images "$IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo
echo "🚀 Next steps:"
echo "  1. Deploy to cluster: ./scripts/deploy-bastion.sh"
echo "  2. Test SSH access: ./scripts/test-ssh.sh"
echo "  3. Or run locally: docker run -it --rm -p 2222:22 $FULL_IMAGE"
