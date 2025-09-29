# Migration Plan: `reservation_processor` Lambda to Kubernetes Operator

This document outlines the plan to migrate the functionality from the `reservation_processor` AWS Lambda function into the `devserver-operator`. The primary goals are to centralize the control plane within Kubernetes, remove dependencies on external services like AWS SQS and DynamoDB for core logic, and create a modular, cloud-agnostic architecture.

## Proposed Architecture

The operator will be structured to separate concerns, with a core that is agnostic to the underlying infrastructure. Cloud-specific (or environment-specific) logic will be handled by pluggable `Provider` modules.

```
devserver_operator/
├── operator.py         # Main reconciliation logic for the DevServer CRD
├── scheduler.py        # Handles queuing and resource availability
├── build.py            # Manages creating and monitoring BuildKit jobs
└── providers/
    ├── __init__.py
    ├── base.py         # Defines the generic `Provider` interface
    ├── local.py        # Default provider for local/non-cloud environments
    └── aws.py            # AWS-specific implementation
```

-   **`Provider` Interface (`base.py`):** An abstract class defining methods for environment-specific operations (e.g., `manage_persistent_storage()`, `get_node_info()`).
-   **`LocalProvider` (`local.py`):** A default implementation for local development and testing, using standard Kubernetes resources like PersistentVolumeClaims.
-   **`AWSProvider` (`aws.py`):** The implementation containing all the `boto3` logic for managing AWS resources like EBS and EFS.

## Migration Tasks

1.  **Design and Update CRDs:** Enhance the `DevServer` and `DevServerFlavor` CRDs to capture all necessary configuration from the original reservation logic. This includes fields for GPU requirements, build specifications, user info, and storage options.
2.  **Structure Operator Modules:** Create the new directory and file structure for the operator, including `scheduler.py`, `build.py`, and the `providers` module.
3.  **Define `Provider` Interface:** Implement the `Provider` abstract base class in `providers/base.py` and create the initial `LocalProvider` and `AWSProvider` class skeletons.
4.  **Implement Core Reconciliation Loop:** Rewrite the main operator logic in `operator.py` to handle the lifecycle of a `DevServer` resource. It will orchestrate calls to the scheduler, builder, and the configured provider.
5.  **Integrate BuildKit Logic:** Move the logic for creating and monitoring BuildKit jobs from `buildkit_job.py` into the `build.py` module, making it callable by the operator.
6.  **Implement Scheduling and Queuing:** Build the resource scheduler in `scheduler.py`. This component will check for available GPU resources and manage a queue of pending `DevServer` requests if resources are scarce.
7.  **Replace DynamoDB with CRD Status:** Refactor the state management logic. Instead of using DynamoDB, all state (e.g., `Pending`, `Building`, `Running`, `Queued`, `Failed`) will be stored in the `.status` field of the `DevServer` custom resource.
8.  **Add Unit and Integration Tests:** Develop a comprehensive test suite for the new operator functionality, covering the core logic and provider implementations.
