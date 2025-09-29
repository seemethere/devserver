import kopf
from kubernetes import client

# Constants
CRD_GROUP = "devserver.io"
CRD_VERSION = "v1"
FINALIZER = f"finalizer.{CRD_GROUP}"


@kopf.on.create(CRD_GROUP, CRD_VERSION, "devservers")
def create_devserver(spec, name, namespace, logger, patch, **kwargs):
    """
    Handle the creation of a new DevServer resource.
    """
    logger.info(f"Creating DevServer '{name}' in namespace '{namespace}'...")

    # Get the DevServerFlavor to determine resources
    custom_objects_api = client.CustomObjectsApi()
    try:
        flavor = custom_objects_api.get_cluster_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            plural="devserverflavors",
            name=spec["flavor"],
        )
    except client.ApiException as e:
        if e.status == 404:
            logger.error(f"DevServerFlavor '{spec['flavor']}' not found.")
            raise kopf.PermanentError(f"Flavor '{spec['flavor']}' not found.")
        raise

    # Define the Deployment
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": {"app": name}},
                "spec": {
                    "containers": [
                        {
                            "name": "devserver",
                            "image": spec.get("image", "ubuntu:latest"),
                            "resources": flavor["spec"]["resources"],
                            # Keep the container running
                            "command": ["sleep"],
                            "args": ["infinity"],
                        }
                    ]
                },
            },
        },
    }

    # Set owner reference
    kopf.adopt(deployment)

    # Create the Deployment in Kubernetes, but only if it doesn't exist
    apps_v1 = client.AppsV1Api()
    try:
        apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
        logger.info(f"Deployment '{name}' already exists. Skipping creation.")
    except client.ApiException as e:
        if e.status == 404:
            apps_v1.create_namespaced_deployment(
                body=deployment,
                namespace=namespace,
            )
            logger.info(f"Deployment '{name}' created for DevServer.")
        else:
            raise

    # Update the status
    patch.status["phase"] = "Running"
    patch.status["message"] = f"Deployment '{name}' created successfully."

    return {"status": "DeploymentCreated", "phase": "Running"}


@kopf.on.delete(CRD_GROUP, CRD_VERSION, "devservers")
def delete_devserver(name, namespace, logger, **kwargs):
    """
    Handle the deletion of a DevServer resource.

    This handler will be called when the resource is marked for deletion.
    We perform our cleanup (deleting the Deployment) and then kopf
    will automatically remove the finalizer.
    """
    logger.info(f"DevServer '{name}' in namespace '{namespace}' is being deleted.")

    # The Deployment is owned by the DevServer and should be garbage collected.
    # However, for more complex scenarios (e.g., external resources),
    # this is where you would put explicit cleanup logic.
    # For now, we just log and let the owner reference handle it.

    return {"status": "DeletionHandled"}
