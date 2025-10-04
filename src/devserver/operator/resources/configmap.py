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
Subsystem sftp /opt/bin/sftp-server
AuthorizedKeysFile /home/dev/.ssh/authorized_keys
HostKey /etc/ssh/hostkeys/ssh_host_rsa_key
HostKey /etc/ssh/hostkeys/ssh_host_ecdsa_key
HostKey /etc/ssh/hostkeys/ssh_host_ed25519_key
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
