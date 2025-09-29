# Project Plan: Python DevServer Operator (TDD Edition)

This document outlines the plan for building a Python-based Kubernetes operator and an accompanying CLI to manage `DevServer` custom resources. This project emphasizes a Test-Driven Development (TDD) approach using `pytest` and a local `k3d` cluster for a robust and maintainable codebase.

## Core Tenets

*   **Operator Framework**: `kopf` (Python)
*   **CLI Framework**: `argparse` (Python standard library)
*   **Codebase**: A single, unified repository for the operator and the CLI.
*   **Testing**: A strong emphasis on TDD with `pytest` and `k3d` for local cluster testing.

---

## The Plan

### Phase 1: Development Environment & TDD Setup
Before we write any application code, we'll establish a solid, repeatable development and testing environment.

*   **Task 1: Local Kubernetes Cluster Setup:** Define and script the setup for a local Kubernetes cluster using `k3d`. This will serve as our primary environment for developing and testing the operator.
*   **Task 2: `pytest` Integration:** Set up the project with `pytest`, including creating a `tests/` directory and a basic configuration. This ensures we can write and run tests from day one.

### Phase 2: Project Scaffolding & Foundation
This phase is about creating the project's skeleton, now with testing in mind.

*   **Task 3: Initialize Project Structure:** Create the Python project with `pyproject.toml` for dependency management. The structure will include modules for the operator (`devserver_operator`), CLI (`cli`), and a directory for CRD YAML files (`crds/`).
*   **Task 4: Define Dependencies:** Add the core project dependencies: `kopf`, the official `kubernetes` Python client, and `pytest`.
*   **Task 5: Extract and Test CRDs:** Extract the `DevServer` and `DevServerFlavor` CRD schemas from `CLAUDE.md` into YAML files. We will also write our first simple tests to ensure these YAML files can be loaded and parsed correctly.

### Phase 3: Core Operator Logic (TDD Approach)
We will build the operator's reconciliation logic by writing tests first, then implementing the code to make them pass.

*   **Task 6: Write Operator Integration Tests:** Using `pytest`, write tests that create `DevServer` custom resources in our `k3d` cluster and then assert that the correct corresponding Kubernetes objects (`Deployment`, `Service`, `PVC`) are created by the operator.
*   **Task 7: Implement `kopf` Handlers:** Implement the `kopf` creation, update, and deletion handlers for the `DevServer` resource. The initial implementation will be just enough to pass the tests defined in the previous step.
*   **Task 8: Implement Status Management & Tests:** Extend the operator to update the `DevServer` resource's `status` field. We will write tests first to verify that the status is updated correctly after resources are provisioned.

### Phase 4: `devctl` CLI with `argparse` (TDD Approach)
Next, we'll build the CLI using `argparse`, again following a test-driven methodology.

*   **Task 9: Write CLI Unit Tests:** Start by writing unit tests for the command-line argument parsing logic to ensure all commands and flags are recognized correctly.
*   **Task 10: Implement `argparse` CLI Structure:** Build out the command structure for `devctl` using Python's `argparse` module.
*   **Task 11: Write CLI Integration Tests:** Write tests that execute the CLI commands and verify they correctly interact with the Kubernetes API to manage `DevServer` resources in our `k3d` cluster.

### Phase 5: Packaging and Deployment
With a fully tested operator and CLI, the final step is to package it for deployment.

*   **Task 12: Containerize the Operator:** Write a `Dockerfile` to build a container image for our operator.
*   **Task 13: Create Deployment Manifests:** Create the necessary Kubernetes manifests (`Deployment`, `ServiceAccount`, `ClusterRole`, `ClusterRoleBinding`) to deploy and run the operator in-cluster.
*   **Task 14: End-to-End Testing:** Create a final end-to-end test script that deploys the operator to `k3d` from its manifests, then uses the CLI to create and delete a `DevServer`, verifying the entire system works as expected from start to finish.
