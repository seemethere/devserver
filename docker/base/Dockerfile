# syntax=docker/dockerfile:1
ARG NEOVIM_VERSION=v0.11.4
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



FROM ubuntu:24.04 as base

# Set apt to non-interactive
ENV DEBIAN_FRONTEND=noninteractive

# Install build-essential, curl, and other dependencies
RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lib,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    git \
    lsb-release \
    ninja-build \
    openssh-client \
    procps \
    python3 \
    python3-pip \
    tmux \
    unzip \
    util-linux \
    --no-install-recommends

# Set a default working directory
WORKDIR /workspace

CMD ["/bin/bash"]

FROM base as neovim
ARG NEOVIM_VERSION

RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lib,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    gettext \
    --no-install-recommends

RUN git clone --branch ${NEOVIM_VERSION} --depth 1 https://github.com/neovim/neovim.git /tmp/neovim
WORKDIR /tmp/neovim
RUN make CMAKE_BUILD_TYPE=Release CMAKE_INSTALL_PREFIX=/opt/nvim && make install

FROM base as uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

FROM base as final

COPY --from=neovim /opt/nvim/ /usr/local/
COPY --from=uv /root/.local/bin/uv /usr/local/bin/uv
COPY --from=uv /root/.local/bin/uvx /usr/local/bin/uvx

# Copy profile.sh
COPY profile.sh /etc/profile

# Copy MOTD script
COPY generate_motd.sh /usr/local/bin/generate_motd.sh
RUN chmod +x /usr/local/bin/generate_motd.sh
