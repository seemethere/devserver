import pytest
from unittest.mock import MagicMock
from devservers.operator.devserverflavor.reconciler import DevServerFlavorReconciler

# --- Mocks and Test Data ---

CPU_SMALL_FLAVOR = {
    "metadata": {"name": "cpu-small"},
    "spec": {
        "resources": {"requests": {"cpu": "500m", "memory": "1Gi"}}
    }
}

AMD64_FLAVOR = {
    "metadata": {"name": "amd64-flavor"},
    "spec": {
        "nodeSelector": {"kubernetes.io/arch": "amd64"}
    }
}

UNSCHEDULABLE_FLAVOR = {
    "metadata": {"name": "unschedulable-flavor"},
    "spec": {
        "nodeSelector": {"this-label-will-never-exist": "true"}
    }
}

GPU_FLAVOR = {
    "metadata": {"name": "gpu-flavor"},
    "spec": {
        "resources": {"requests": {"nvidia.com/gpu": "1"}},
        "tolerations": [{"key": "nvidia.com/gpu", "operator": "Exists", "effect": "NoSchedule"}]
    }
}


# Mock a generic, schedulable node
GENERIC_NODE = MagicMock()
GENERIC_NODE.metadata.labels = {}
GENERIC_NODE.spec.taints = []
GENERIC_NODE.status.allocatable = {
    "cpu": "2",
    "memory": "4Gi"
}

# Mock a GPU node
GPU_NODE = MagicMock()
GPU_NODE.metadata.name = "gpu-node"
GPU_NODE.metadata.labels = {}
GPU_NODE.spec.taints = [MagicMock(key="nvidia.com/gpu", effect="NoSchedule")]
GPU_NODE.status.allocatable = {
    "cpu": "8",
    "memory": "32Gi",
    "nvidia.com/gpu": "1"
}

# Mock a pod that uses a GPU
POD_WITH_GPU = MagicMock()
POD_WITH_GPU.spec.node_name = "gpu-node"
POD_WITH_GPU.status.phase = "Running"
POD_WITH_GPU.spec.containers = [
    MagicMock(resources=MagicMock(requests={"nvidia.com/gpu": "1"}))
]


# A ready Karpenter NodePool for amd64
READY_NODEPOOL = {
    "metadata": {"name": "amd64-pool"},
    "spec": {
        "template": {
            "spec": {
                "requirements": [
                    {"key": "kubernetes.io/arch", "operator": "In", "values": ["amd64"]}
                ]
            }
        }
    },
    "status": {"conditions": [{"type": "Ready", "status": "True"}]}
}

# A not-ready Karpenter NodePool for amd64
NOT_READY_NODEPOOL = {
    "metadata": {"name": "amd64-pool-not-ready"},
    "spec": {
        "template": {
            "spec": {
                "requirements": [
                    {"key": "kubernetes.io/arch", "operator": "In", "values": ["amd64"]}
                ]
            }
        }
    },
    "status": {"conditions": [{"type": "Ready", "status": "False"}]}
}


# --- Test Cases ---

@pytest.mark.asyncio
async def test_flavor_is_schedulable_on_generic_node():
    """ Tests the 'Yes' case for a generic flavor. """
    logger = MagicMock()
    custom_objects_api = MagicMock()
    core_v1_api = MagicMock()

    custom_objects_api.list_cluster_custom_object.side_effect = [
        {"items": [CPU_SMALL_FLAVOR]},  # Flavors
        {"items": []}  # NodePools
    ]
    core_v1_api.list_node.return_value = MagicMock(items=[GENERIC_NODE])
    core_v1_api.list_pod_for_all_namespaces.return_value = MagicMock(items=[])

    reconciler = DevServerFlavorReconciler(logger, custom_objects_api=custom_objects_api, core_v1_api=core_v1_api)
    await reconciler.reconcile_all_flavors()

    custom_objects_api.patch_cluster_custom_object_status.assert_called_once()
    patched_body = custom_objects_api.patch_cluster_custom_object_status.call_args[1]['body']
    assert patched_body["status"]["schedulable"] == "Yes"

@pytest.mark.asyncio
async def test_flavor_is_autoscaled_with_matching_nodepool():
    """ Tests the 'AUTOSCALED' case. """
    logger = MagicMock()
    custom_objects_api = MagicMock()
    core_v1_api = MagicMock()

    custom_objects_api.list_cluster_custom_object.side_effect = [
        {"items": [AMD64_FLAVOR]},
        {"items": [READY_NODEPOOL]}
    ]
    core_v1_api.list_node.return_value = MagicMock(items=[])
    core_v1_api.list_pod_for_all_namespaces.return_value = MagicMock(items=[])

    reconciler = DevServerFlavorReconciler(logger, custom_objects_api=custom_objects_api, core_v1_api=core_v1_api)
    await reconciler.reconcile_all_flavors()

    custom_objects_api.patch_cluster_custom_object_status.assert_called_once()
    patched_body = custom_objects_api.patch_cluster_custom_object_status.call_args[1]['body']
    assert patched_body["status"]["schedulable"] == "AUTOSCALED"

@pytest.mark.asyncio
async def test_flavor_is_unschedulable_with_no_matching_nodes():
    """ Tests the 'No' case. """
    logger = MagicMock()
    custom_objects_api = MagicMock()
    core_v1_api = MagicMock()

    custom_objects_api.list_cluster_custom_object.side_effect = [
        {"items": [UNSCHEDULABLE_FLAVOR]},
        {"items": []}
    ]
    core_v1_api.list_node.return_value = MagicMock(items=[GENERIC_NODE])
    core_v1_api.list_pod_for_all_namespaces.return_value = MagicMock(items=[])

    reconciler = DevServerFlavorReconciler(logger, custom_objects_api=custom_objects_api, core_v1_api=core_v1_api)
    await reconciler.reconcile_all_flavors()

    custom_objects_api.patch_cluster_custom_object_status.assert_called_once()
    patched_body = custom_objects_api.patch_cluster_custom_object_status.call_args[1]['body']
    assert patched_body["status"]["schedulable"] == "No"

@pytest.mark.asyncio
async def test_flavor_is_unschedulable_with_not_ready_nodepool():
    """ Tests the 'No' case when the matching NodePool is not ready. """
    logger = MagicMock()
    custom_objects_api = MagicMock()
    core_v1_api = MagicMock()

    custom_objects_api.list_cluster_custom_object.side_effect = [
        {"items": [AMD64_FLAVOR]},
        {"items": [NOT_READY_NODEPOOL]}
    ]
    core_v1_api.list_node.return_value = MagicMock(items=[])
    core_v1_api.list_pod_for_all_namespaces.return_value = MagicMock(items=[])

    reconciler = DevServerFlavorReconciler(logger, custom_objects_api=custom_objects_api, core_v1_api=core_v1_api)
    await reconciler.reconcile_all_flavors()

    custom_objects_api.patch_cluster_custom_object_status.assert_called_once()
    patched_body = custom_objects_api.patch_cluster_custom_object_status.call_args[1]['body']
    assert patched_body["status"]["schedulable"] == "No"


@pytest.mark.asyncio
async def test_flavor_is_unschedulable_with_insufficient_resources():
    """ Tests the 'No' case when the node does not have enough resources. """
    logger = MagicMock()
    custom_objects_api = MagicMock()
    core_v1_api = MagicMock()

    custom_objects_api.list_cluster_custom_object.side_effect = [
        {"items": [GPU_FLAVOR]},
        {"items": []}
    ]
    core_v1_api.list_node.return_value = MagicMock(items=[GPU_NODE])
    core_v1_api.list_pod_for_all_namespaces.return_value = MagicMock(items=[POD_WITH_GPU])

    reconciler = DevServerFlavorReconciler(logger, custom_objects_api=custom_objects_api, core_v1_api=core_v1_api)
    await reconciler.reconcile_all_flavors()

    custom_objects_api.patch_cluster_custom_object_status.assert_called_once()
    patched_body = custom_objects_api.patch_cluster_custom_object_status.call_args[1]['body']
    assert patched_body["status"]["schedulable"] == "No"


@pytest.mark.asyncio
async def test_flavor_is_unschedulable_with_unmatched_taint():
    """ Tests the 'No' case when the node has a taint the flavor does not tolerate. """
    logger = MagicMock()
    custom_objects_api = MagicMock()
    core_v1_api = MagicMock()

    # Generic flavor without tolerations
    generic_flavor = CPU_SMALL_FLAVOR.copy()

    custom_objects_api.list_cluster_custom_object.side_effect = [
        {"items": [generic_flavor]},
        {"items": []}
    ]
    # The only available node has a taint
    core_v1_api.list_node.return_value = MagicMock(items=[GPU_NODE])
    core_v1_api.list_pod_for_all_namespaces.return_value = MagicMock(items=[])

    reconciler = DevServerFlavorReconciler(logger, custom_objects_api=custom_objects_api, core_v1_api=core_v1_api)
    await reconciler.reconcile_all_flavors()

    custom_objects_api.patch_cluster_custom_object_status.assert_called_once()
    patched_body = custom_objects_api.patch_cluster_custom_object_status.call_args[1]['body']
    assert patched_body["status"]["schedulable"] == "No"
