# syntax=docker/dockerfile:1
# To build and push the multi-arch image, use the following command with Docker buildx:
#
# docker buildx build --platform linux/amd64,linux/arm64 -t seemethere/devserver-base:latest --push .
#
# Base development environment for DevServers.
#
# This image provides a standardized, CPU-based environment with essential
# tools for development. It is based on the latest Ubuntu LTS and includes:
# - build-essential: For compiling C/C++ and other code.
# - curl: For downloading files and making web requests.
# - uv: A fast Python package installer.
#
# This image can be extended to create more specialized environments, such as
# those with CUDA support for GPU-based development.

FROM ubuntu:24.04

# Install build-essential, curl, and other dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    build-essential \
    curl \
    lsb-release \
    procps \
    util-linux \
    --no-install-recommends

# Copy MOTD script
COPY generate_motd.sh /usr/local/bin/generate_motd.sh
RUN chmod +x /usr/local/bin/generate_motd.sh

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set a default working directory
WORKDIR /workspace

ENTRYPOINT ["/bin/sh"]
