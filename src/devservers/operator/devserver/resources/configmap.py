from typing import Any, Dict

def build_configmap(name: str, namespace: str) -> Dict[str, Any]:
    """Builds the ConfigMap for the DevServer's sshd_config."""
    
    sshd_config = """
# This file is managed by the devserver operator

Port 22
PermitRootLogin no
PasswordAuthentication no
ChallengeResponseAuthentication no
PrintMotd no 
ForceCommand /devserver-login/user_login.sh
Subsystem sftp /opt/bin/sftp-server
AuthorizedKeysFile /home/dev/.ssh/authorized_keys
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
AllowAgentForwarding yes
    """

    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": f"{name}-sshd-config",
            "namespace": namespace,
        },
        "data": {
            "sshd_config": sshd_config,
        },
    }


def build_startup_configmap(name: str, namespace: str, script_content: str) -> Dict[str, Any]:
    """Builds the ConfigMap for the startup script."""
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": f"{name}-startup-script",
            "namespace": namespace,
        },
        "data": {
            "startup.sh": script_content,
        },
    }

def build_login_configmap(name: str, namespace: str, user_login_script_content: str) -> Dict[str, Any]:
    """Builds the ConfigMap for the login script."""
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": f"{name}-login-script",
            "namespace": namespace,
        },
        "data": {
            "user_login.sh": user_login_script_content,
        },
    }