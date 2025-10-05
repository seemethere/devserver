from typing import Any, Dict


def build_statefulset(
    name: str, namespace: str, spec: Dict[str, Any], flavor: Dict[str, Any]
) -> Dict[str, Any]:
    """Builds the StatefulSet for the DevServer."""
    image = spec.get("image", "ubuntu:latest")

    # Get the public key from the spec
    ssh_public_key = spec.get("ssh", {}).get("publicKey", "")
    statefulset_spec = {
        "replicas": 1,
        "serviceName": f"{name}-headless",
        "selector": {"matchLabels": {"app": name}},
        "template": {
            "metadata": {"labels": {"app": name}},
            "spec": {
                "nodeSelector": flavor["spec"].get("nodeSelector"),
                "tolerations": flavor["spec"].get("tolerations"),
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
                ],
                "containers": [
                    {
                        "name": "devserver",
                        "image": image,
                        "command": ["/bin/sh", "-c"],
                        "args": ["/devserver/startup.sh"],
                        "ports": [{"containerPort": 22}],
                        "volumeMounts": [
                            {"name": "home", "mountPath": "/home/dev"},
                            {"name": "bin", "mountPath": "/opt/bin"},
                            {
                                "name": "startup-script",
                                "mountPath": "/devserver",
                                "readOnly": True,
                            },
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
                        "env": [
                            {
                                "name": "SSH_PUBLIC_KEY",
                                "value": ssh_public_key,
                            },
                        ],
                    }
                ],
                "volumes": [
                    {"name": "bin", "emptyDir": {}},
                    {
                        "name": "startup-script",
                        "configMap": {
                            "name": f"{name}-startup-script",
                            "defaultMode": 0o755,
                        },
                    },
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
    if not statefulset_spec["template"]["spec"].get("nodeSelector"):
        del statefulset_spec["template"]["spec"]["nodeSelector"]

    # Remove tolerations if it is None
    if not statefulset_spec["template"]["spec"].get("tolerations"):
        del statefulset_spec["template"]["spec"]["tolerations"]

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
