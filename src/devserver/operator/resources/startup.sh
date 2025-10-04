#!/bin/sh

set -e

# --- Logging functions ---
# Colors
C_RESET='\033[0m'
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_BLUE='\033[0;34m'
C_BOLD='\033[1m'

log_info() {
    echo -e "${C_BLUE}${C_BOLD}==>${C_RESET}${C_BOLD} $1${C_RESET}"
}

log_step() {
    echo -e "${C_YELLOW}-->${C_RESET} $1"
}

log_error() {
    echo -e "${C_RED}==>${C_RESET}${C_BOLD} ERROR: $1${C_RESET}" >&2
}
# --- End Logging functions ---


log_info "Configuring container..."

log_step "Ensuring 'dev' user and group exist with UID/GID 1000"

# --- Group management ---
# Check if a group with GID 1000 exists
if getent group 1000 >/dev/null 2>&1; then
    # Group with GID 1000 exists, check its name
    GROUP_NAME=$(getent group 1000 | cut -d: -f1)
    if [ "$GROUP_NAME" != "dev" ]; then
        log_step "Group with GID 1000 exists as '$GROUP_NAME'. Renaming to 'dev'."
        groupmod -n dev "$GROUP_NAME"
    else
        log_step "Group 'dev' with GID 1000 already exists."
    fi
# Check if group with name 'dev' exists but with different GID
elif getent group dev >/dev/null 2>&1; then
    log_error "Group 'dev' exists but with a different GID. This is an unsupported configuration."
    exit 1
# Create the group
else
    log_step "Creating group 'dev' with GID 1000."
    groupadd --gid 1000 dev
fi

# --- User management ---
# Check if a user with UID 1000 exists
if getent passwd 1000 >/dev/null 2>&1; then
    # User with UID 1000 exists, check its name
    USER_NAME=$(getent passwd 1000 | cut -d: -f1)
    if [ "$USER_NAME" != "dev" ]; then
        log_step "User with UID 1000 exists as '$USER_NAME'. Renaming to 'dev'."
        # kill processes of the user before renaming
        pkill -u "$USER_NAME" || true
        sleep 1
        usermod -l dev "$USER_NAME"
    else
        log_step "User 'dev' with UID 1000 already exists."
    fi
# Check if user with name 'dev' exists but with different UID
elif getent passwd dev >/dev/null 2>&1; then
    log_error "User 'dev' exists but with a different UID. This is an unsupported configuration."
    exit 1
# Create the user
else
    log_step "Creating user 'dev' with UID 1000."
    useradd --uid 1000 --gid 1000 -m --home-dir /home/dev --shell /bin/bash dev
fi

# --- Final configuration ---
# Ensure user's primary group is 'dev' and home directory is correct
usermod -g dev -d /home/dev dev
# Ensure home directory exists and has correct permissions
mkdir -p /home/dev
chown -R dev:dev /home/dev

log_info "Unlocking user's account to allow SSH access"
# Unlock the user's account to allow SSH access
# On some systems (like Fedora), an account created without a password is locked
# Give the user a bogus password to unlock them
# TODO: actually make this random
(
    set -x
    usermod -p my_random_password dev
)

# --- sshd user ---
if ! getent group sshd >/dev/null; then
    groupadd -r sshd
fi
if ! getent passwd sshd >/dev/null; then
    useradd -r -g sshd -c 'sshd privsep' -d /var/empty -s /sbin/nologin sshd
fi

log_step "Setting up SSH for 'dev' user"
# Set up SSH for the 'dev' user
mkdir -p /home/dev/.ssh
echo "${SSH_PUBLIC_KEY}" > /home/dev/.ssh/authorized_keys
chown -R dev:dev /home/dev/.ssh
chmod 700 /home/dev/.ssh
chmod 600 /home/dev/.ssh/authorized_keys
# Create the privilege separation directory
mkdir -p /var/empty

log_info "Starting sshd..."
if [ -n "$DEVSERVER_TEST_MODE" ]; then
    log_info "Test mode: skipping sshd execution."
    exit 0
fi

if test -f /opt/bin/sshd; then
    exec /opt/bin/sshd -D -e -f /etc/ssh/sshd_config
else
    log_error "sshd binary not found in /opt/bin/sshd"
    exit 1
fi
