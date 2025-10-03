# This Dockerfile builds a fully static sshd binary for amd64 and arm64.
#
# To build and push the multi-arch image, use the following command with Docker buildx:
#
# docker buildx build --platform linux/amd64,linux/arm64 -t seemethere/devserver-sshd-static:latest --push .
#

# --- Build Stage ---
FROM ubuntu:latest AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    zlib1g-dev \
    libssl-dev \
    --no-install-recommends

# Set versions
ARG OPENSSH_VERSION=9.7p1

# Download and extract OpenSSH
ARG OPENSSH_URL=https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-${OPENSSH_VERSION}.tar.gz
RUN wget --no-check-certificate -q -O openssh.tar.gz ${OPENSSH_URL} && \
    tar -xzf openssh.tar.gz && \
    rm openssh.tar.gz

# Configure and build OpenSSH statically
WORKDIR openssh-${OPENSSH_VERSION}
RUN ./configure \
    --without-pie \
    --with-privsep-path=/var/empty \
    --with-zlib \
    --with-ssl-dir=/usr \
    LDFLAGS="-static" && \
    make sshd scp sftp-server ssh-keygen -j$(nproc)

# --- Final Stage ---
# NOTE DO NOT CHANGE THIS TO scrach, it will break the init container
FROM ubuntu:latest

# Copy the static binaries from the builder stage
COPY --from=builder /openssh-9.7p1/sshd /usr/local/bin/sshd
COPY --from=builder /openssh-9.7p1/scp /usr/local/bin/scp
COPY --from=builder /openssh-9.7p1/sftp-server /usr/local/bin/sftp-server
COPY --from=builder /openssh-9.7p1/ssh-keygen /usr/local/bin/ssh-keygen

ENTRYPOINT ["/bin/sh"]
