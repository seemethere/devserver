# This Dockerfile builds fully static sshd and doas binaries for amd64 and arm64.
#
# Note: Using doas instead of sudo for simplicity. If compatibility issues arise,
# we may switch to sudo in the future.
#
# To build and push the multi-arch image, use the following command with Docker buildx:
#
# docker buildx build --platform linux/amd64,linux/arm64 -t seemethere/devserver-static-dependencies:latest --push .
#

# --- SSH Builder Stage ---
FROM ubuntu:latest AS sshd-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    zlib1g-dev \
    libssl-dev \
    --no-install-recommends

# Set version
ARG OPENSSH_VERSION=9.7p1

# Download and extract OpenSSH
ARG OPENSSH_URL=https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-${OPENSSH_VERSION}.tar.gz
RUN wget --no-check-certificate -q -O openssh.tar.gz ${OPENSSH_URL} && \
    tar -xzf openssh.tar.gz && \
    rm openssh.tar.gz

# Configure and build OpenSSH statically
WORKDIR /openssh-${OPENSSH_VERSION}
RUN ./configure \
    --without-pie \
    --with-privsep-path=/var/empty \
    --with-zlib \
    --with-ssl-dir=/usr \
    LDFLAGS="-static" && \
    make sshd scp sftp-server ssh-keygen -j$(nproc)

# --- Doas Builder Stage ---
FROM ubuntu:latest AS doas-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    bison \
    flex \
    --no-install-recommends

# Set version
ARG DOAS_VERSION=6.8.2

# Download and extract OpenDoas
ARG DOAS_URL=https://github.com/Duncaen/OpenDoas/archive/refs/tags/v${DOAS_VERSION}.tar.gz
RUN wget --no-check-certificate -q -O doas.tar.gz ${DOAS_URL} && \
    tar -xzf doas.tar.gz && \
    rm doas.tar.gz

# Configure and build doas statically
WORKDIR /OpenDoas-${DOAS_VERSION}
RUN ./configure \
    --without-pam \
    --without-timestamp \
    --enable-static && \
    make -j$(nproc)

# --- Final Stage ---
# NOTE DO NOT CHANGE THIS TO scratch, it will break the init container
FROM ubuntu:latest

# Copy the static binaries from the builder stages
COPY --from=sshd-builder /openssh-9.7p1/sshd /usr/local/bin/sshd
COPY --from=sshd-builder /openssh-9.7p1/scp /usr/local/bin/scp
COPY --from=sshd-builder /openssh-9.7p1/sftp-server /usr/local/bin/sftp-server
COPY --from=sshd-builder /openssh-9.7p1/ssh-keygen /usr/local/bin/ssh-keygen
COPY --from=doas-builder /OpenDoas-6.8.2/doas /usr/local/bin/doas

ENTRYPOINT ["/bin/sh"]
