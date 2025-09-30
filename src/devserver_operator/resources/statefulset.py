def build_statefulset(name, namespace, spec, flavor):
    """Builds the StatefulSet for the DevServer."""
    statefulset_spec = {
        "replicas": 1,
        "serviceName": f"{name}-headless",
        "selector": {"matchLabels": {"app": name}},
        "template": {
            "metadata": {"labels": {"app": name}},
            "spec": {
                "initContainers": [
                    {
                        "name": "ssh-setup",
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
                    }
                ],
                "containers": [
                    {
                        "name": "devserver",
                        "image": spec.get("image", "ubuntu:latest"),
                        "resources": flavor["spec"]["resources"],
                        "command": ["/bin/bash", "-c"],
                        "args": [
                            f"""
                            set -ex
                            echo "[STARTUP] Starting devserver container..."

                            # Setup user and SSH
                            id dev &>/dev/null || useradd -u 1000 -m -s /bin/bash dev
                            usermod -aG sudo dev
                            echo 'dev ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/dev
                            
                            # Initialize shared storage if it exists
                            if [ -d "/shared" ]; then
                                echo "[STARTUP] Shared storage detected. Initializing..."
                                USER_DIR=$(echo "{spec.get('owner', 'default')}" | cut -d'@' -f1)
                                mkdir -p "/shared/$USER_DIR"
                                chown dev:dev "/shared/$USER_DIR"
                                echo "[STARTUP] Shared storage setup for user $USER_DIR at /shared/$USER_DIR."
                            fi

                            # Start SSH server
                            mkdir -p /run/sshd
                            /usr/sbin/sshd -D -e &

                            echo "[STARTUP] SSH Server started."
                            echo "[STARTUP] Container is ready."

                            # Keep container running
                            sleep infinity
                            """
                        ],
                        "ports": [{"containerPort": 22}],
                        "volumeMounts": [{"name": "home", "mountPath": "/home/dev"}],
                    }
                ],
                "volumes": [],
            },
        },
        "volumeClaimTemplates": [
            {
                "metadata": {"name": "home"},
                "spec": {
                    "accessModes": ["ReadWriteOnce"],
                    "resources": {
                        "requests": {
                            "storage": spec.get("persistentHomeSize", "10Gi")
                        }
                    },
                },
            }
        ],
    }

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
