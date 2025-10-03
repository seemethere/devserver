# Testing

This project follows a Test-Driven Development (TDD) approach, with a strong emphasis on integration testing. The test suite uses `pytest` and a local `k3d` cluster to ensure the operator and CLI behave correctly in a real Kubernetes environment.

See `PROJECT.md` in the root directory for more details on the development plan.

## Running Tests

The test suite includes comprehensive integration tests that run the operator and verify its functionality against a real Kubernetes cluster.

**Prerequisites:**

-   Docker
-   `k3d`

### Test Execution

```bash
# First, ensure Python dependencies are installed
pip install -e ".[dev]"

# Create a local k3d cluster for testing
make up

# Run all tests
make test

# Clean up the cluster when you're done
make down
```

## Test Philosophy

-   **Integration by Default**: Most tests are integration tests that interact with a real Kubernetes API server.
-   **Real Resources**: Tests create, manage, and delete real `DevServer` custom resources and verify that the operator creates the expected `StatefulSets`, `Services`, etc.
-   **CLI Integration**: The test suite also runs `devctl` commands as subprocesses to verify the CLI's behavior against the running operator.
-   **Session-Scoped Fixtures**: A `k3d` cluster and the running operator are managed by `pytest` session-scoped fixtures for efficiency, meaning they are set up once per test run.
