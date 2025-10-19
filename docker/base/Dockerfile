# syntax=docker/dockerfile:1
ARG NEOVIM_VERSION=v0.11.4
# To build and push the multi-arch image, use the following command with Docker buildx:
#
# For final image (without CUDA)
# docker buildx build --target final--platform linux/amd64,linux/arm64 -t seemethere/devserver-base:latest --push .
#
# For CUDA image (with CUDA)
# docker buildx build --target cuda-final--platform linux/amd64,linux/arm64 -t seemethere/devserver-base:latest --push .
#
# Base development environment for DevServers.
#
# This image provides a standardized, environment with essential
# tools for development. It is based on the latest Ubuntu LTS and includes:
# - build-essential: For compiling C/C++ and other code.
# - curl: For downloading files and making web requests.
# - uv: A fast Python package installer.
#
# This image can be extended to create more specialized environments, such as
# those with CUDA support for GPU-based development.



FROM ubuntu:24.04 AS base

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
    file \
    gnupg \
    iproute2 \
    lsb-release \
    ninja-build \
    openssh-client \
    openssh-server \
    procps \
    python3 \
    python3-pip \
    sudo \
    tmux \
    unzip \
    util-linux \
    wget \
    zsh \
    --no-install-recommends

# Set a default working directory
WORKDIR /workspace

CMD ["/bin/bash"]

FROM base AS neovim
ARG NEOVIM_VERSION

RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lib,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    gettext \
    --no-install-recommends

RUN git clone --branch ${NEOVIM_VERSION} --depth 1 https://github.com/neovim/neovim.git /tmp/neovim
WORKDIR /tmp/neovim
RUN make CMAKE_BUILD_TYPE=Release CMAKE_INSTALL_PREFIX=/opt/nvim && make install

FROM base AS uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

FROM base AS final

COPY --from=neovim /opt/nvim/ /usr/local/
COPY --from=uv /root/.local/bin/uv /usr/local/bin/uv
COPY --from=uv /root/.local/bin/uvx /usr/local/bin/uvx

# Create dev user with consistent UID (1000)
RUN if getent passwd 1000 >/dev/null 2>&1; then USER_TO_DELETE=$(getent passwd 1000 | cut -d: -f1); userdel -r $USER_TO_DELETE; fi && \
    useradd -u 1000 -m -s /usr/bin/zsh dev && \
    echo 'Defaults lecture=never' >> /etc/sudoers.d/dev && \
    echo 'Defaults !lecture' >> /etc/sudoers.d/dev

# Switch back to root for final configuration
USER root

# Copy MOTD script to /etc/update-motd.d/00-custom
COPY motd_script /etc/update-motd.d/00-custom
RUN chmod +x /etc/update-motd.d/00-custom

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

FROM final as cuda-final

COPY --from=nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 /usr/local/cuda-12 /usr/local/cuda-12
COPY --from=nvidia/cuda:13.0.1-cudnn-devel-ubuntu24.04 /usr/local/cuda-13 /usr/local/cuda-13

RUN ln -sf /usr/local/cuda-13 /usr/local/cuda
ENV CUDA_HOME=/usr/local/cuda
