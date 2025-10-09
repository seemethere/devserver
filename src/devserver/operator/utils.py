import kubernetes

def add_finalizer(name: str, finalizer: str, resource_type: str) -> None:
    """Adds a finalizer to a cluster-scoped custom object."""
    api = kubernetes.client.CustomObjectsApi()
    patch = {"metadata": {"finalizers": [finalizer]}}
    api.patch_cluster_custom_object(
        group="devserver.io",
        version="v1",
        plural=resource_type,
        name=name,
        body=patch,
    )

def remove_finalizer(name: str, finalizer: str, resource_type: str) -> None:
    """Removes a finalizer from a cluster-scoped custom object."""
    api = kubernetes.client.CustomObjectsApi()
    obj = api.get_cluster_custom_object(
        group="devserver.io",
        version="v1",
        plural=resource_type,
        name=name,
    )
    finalizers = obj.get("metadata", {}).get("finalizers", [])
    if finalizer in finalizers:
        finalizers.remove(finalizer)
        patch = {"metadata": {"finalizers": finalizers}}
        api.patch_cluster_custom_object(
            group="devserver.io",
            version="v1",
            plural=resource_type,
            name=name,
            body=patch,
        )
