from typing import Any, Dict


def build_statefulset(
    name: str, namespace: str, spec: Dict[str, Any], flavor: Dict[str, Any]
) -> Dict[str, Any]:
    """Builds the StatefulSet for the DevServer."""
    image = spec.get("image", "ubuntu:latest")
    statefulset_spec = {
        "replicas": 1,
        "serviceName": f"{name}-headless",
        "selector": {"matchLabels": {"app": name}},
        "template": {
            "metadata": {"labels": {"app": name}},
            "spec": {
                "nodeSelector": flavor["spec"].get("nodeSelector"),
                "initContainers": [
                    {
                        "name": "install-sshd",
                        "image": "seemethere/devserver-sshd-static:latest",
                        "imagePullPolicy": "Always",
                        "command": ["/bin/sh", "-c"],
                        "args": [
                            """
                            set -ex
                            echo "[INIT] Copying portable binaries..."
                            cp /usr/local/bin/sshd /opt/bin/
                            cp /usr/local/bin/scp /opt/bin/
                            cp /usr/local/bin/sftp-server /opt/bin/
                            cp /usr/local/bin/ssh-keygen /opt/bin/
                            chmod +x /opt/bin/sshd
                            echo "[INIT] Binaries copied."
                            """
                        ],
                        "volumeMounts": [{"name": "bin", "mountPath": "/opt/bin"}],
                    },
                    {
                        "name": "init",
                        "image": "alpine:latest",
                        "command": ["/bin/sh", "-c"],
                        "args": [
                            f"""
                            set -ex
                            echo "[INIT] Setting up dev user and SSH keys..."
                            adduser -D -u 1000 -s /bin/bash dev
                            mkdir -p /home/dev/.ssh
                            echo '{spec["ssh"]["publicKey"]}' > /home/dev/.ssh/authorized_keys
                            chown -R 1000:1000 /home/dev
                            chmod 700 /home/dev/.ssh
                            chmod 600 /home/dev/.ssh/authorized_keys
                            echo "[INIT] Setup complete."
                            """
                        ],
                        "volumeMounts": [{"name": "home", "mountPath": "/home/dev"}],
                    },
                ],
                "containers": [
                    {
                        "name": "devserver",
                        "image": image,
                        "command": ["/bin/sh", "-c"],
                        "args": [
                            """
                            set -ex
                            echo "[STARTUP] Configuring sshd environment..."
                            # Create a user and group for privilege separation
                            addgroup --system sshd
                            adduser --system --no-create-home --ingroup sshd sshd
                            # Create the privilege separation directory
                            mkdir -p /var/empty
                            echo "[STARTUP] Starting sshd..."
                            exec /opt/bin/sshd -D -e -f /etc/ssh/sshd_config
                            """
                        ],
                        "ports": [{"containerPort": 22}],
                        "volumeMounts": [
                            {"name": "home", "mountPath": "/home/dev"},
                            {"name": "bin", "mountPath": "/opt/bin"},
                            {
                                "name": "sshd-config",
                                "mountPath": "/etc/ssh",
                                "readOnly": True,
                            },
                            {
                                "name": "host-keys",
                                "mountPath": "/etc/ssh/hostkeys",
                                "readOnly": True,
                            },
                        ],
                        "resources": flavor["spec"]["resources"],
                    }
                ],
                "volumes": [
                    {"name": "bin", "emptyDir": {}},
                    {
                        "name": "sshd-config",
                        "configMap": {"name": f"{name}-sshd-config"},
                    },
                    {
                        "name": "host-keys",
                        "secret": {
                            "secretName": f"{name}-host-keys",
                            "defaultMode": 0o600,
                        },
                    },
                ],
            },
        },
        "volumeClaimTemplates": [
            {
                "metadata": {"name": "home"},
                "spec": {
                    "accessModes": ["ReadWriteOnce"],
                    "resources": {
                        "requests": {"storage": spec.get("persistentHomeSize", "10Gi")}
                    },
                },
            }
        ],
    }

    # Remove nodeSelector if it is None
    if not statefulset_spec["template"]["spec"]["nodeSelector"]:
        del statefulset_spec["template"]["spec"]["nodeSelector"]

    # Add shared volume if specified
    if "sharedVolumeClaimName" in spec:
        pvc_name = spec["sharedVolumeClaimName"]
        # Add the volume that points to the existing PVC
        statefulset_spec["template"]["spec"]["volumes"].append(
            {"name": "shared", "persistentVolumeClaim": {"claimName": pvc_name}}
        )
        # Mount the volume into the container
        statefulset_spec["template"]["spec"]["containers"][0]["volumeMounts"].append(
            {"name": "shared", "mountPath": "/shared"}
        )

    return {
        "apiVersion": "apps/v1",
        "kind": "StatefulSet",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": statefulset_spec,
    }
