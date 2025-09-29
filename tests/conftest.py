"""
This file contains shared fixtures for all tests.
"""

import pytest
from kubernetes import client, config, utils


@pytest.fixture(scope="session", autouse=True)
def apply_crds():
    """
    Pytest fixture to apply the CRDs to the cluster before any tests run,
    and clean them up after the entire test session is complete.
    """
    config.load_kube_config()
    k8s_client = client.ApiClient()

    # Apply CRDs using server-side apply for idempotency
    utils.create_from_yaml(k8s_client, "crds/devserver.io_devservers.yaml", apply=True)
    utils.create_from_yaml(
        k8s_client, "crds/devserver.io_devserverflavors.yaml", apply=True
    )

    yield

    # Teardown: Delete CRDs after all tests in the session are done
    api_extensions_v1 = client.ApiextensionsV1Api()
    try:
        api_extensions_v1.delete_custom_resource_definition(
            name="devservers.devserver.io"
        )
    except client.ApiException as e:
        if e.status != 404:
            raise
    try:
        api_extensions_v1.delete_custom_resource_definition(
            name="devserverflavors.devserver.io"
        )
    except client.ApiException as e:
        if e.status != 404:
            raise
