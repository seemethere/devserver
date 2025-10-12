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

Tests run in parallel by default using 4 jobs. You can customize the number of jobs using the `MAX_JOBS` environment variable:

```bash
# Run tests with 8 parallel jobs
make test MAX_JOBS=8
```

## Test Philosophy

-   **Integration by Default**: Most tests are integration tests that interact with a real Kubernetes API server.
-   **Real Resources**: Tests create, manage, and delete real `DevServer` custom resources and verify that the operator creates the expected `StatefulSets`, `Services`, etc.
-   **Robust Polling**: To avoid flaky tests, the suite uses a set of robust helper functions in `tests/helpers.py` that poll the Kubernetes API to wait for resources to reach their expected state, rather than relying on fixed `time.sleep()` calls.
-   **CLI Integration**: The test suite also runs `devctl` commands as subprocesses to verify the CLI's behavior against the running operator.
-   **Session-Scoped Fixtures**: A `k3d` cluster and the running operator are managed by `pytest` session-scoped fixtures for efficiency, meaning they are set up once per test run.

### Startup Script Testing

A dedicated test, `test_startup_script.py`, ensures that the container's entrypoint script (`startup.sh`) works correctly across different base Docker images (e.g., `ubuntu:latest`, `fedora:latest`). This test runs the script in isolation within Docker containers to verify that user creation and environment setup are compatible with various Linux distributions.
