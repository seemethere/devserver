# Bastion server for PyTorch development server platform  
# Phase 2: Secure user provisioning with sidecar controller

FROM ubuntu:22.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    python3 \
    python3-pip \
    curl \
    vim \
    git \
    htop \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Setup SSH
RUN mkdir /var/run/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
RUN sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Generate SSH host keys during build (remove existing keys first)
RUN rm -f /etc/ssh/ssh_host_*_key* \
    && ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key -N '' \
    && ssh-keygen -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key -N '' \
    && ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N ''

# Create bastion marker file for CLI detection
RUN touch /.bastion-marker

# Create the test user during build (instead of runtime)
ARG TEST_USER=testuser
ARG TEST_UID=1000
RUN useradd -m -u $TEST_UID -s /bin/bash "$TEST_USER" \
    && usermod -aG sudo "$TEST_USER" \
    && mkdir -p "/home/$TEST_USER/.ssh" \
    && chmod 700 "/home/$TEST_USER/.ssh" \
    && chown -R "$TEST_USER:$TEST_USER" "/home/$TEST_USER"

# Install devctl CLI
COPY cli/ /opt/devctl/
# Upgrade pip and install build tools for pyproject.toml support
RUN pip3 install --upgrade pip setuptools wheel
RUN cd /opt/devctl && pip3 install --no-cache-dir .

# Copy configuration files
COPY bastion/config/motd /etc/motd
COPY bastion/config/profile.d/devserver.sh /etc/profile.d/
COPY bastion/config/sshd_config /etc/ssh/sshd_config.d/devserver.conf

# Copy user controller sidecar
COPY bastion/user-controller.py /usr/local/bin/user-controller.py
RUN chmod +x /usr/local/bin/user-controller.py

# Create entrypoint script
COPY bastion/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose SSH port
EXPOSE 22

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD service ssh status

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/sbin/sshd", "-D"]
