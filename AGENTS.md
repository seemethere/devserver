# Agent Instructions

This document provides guidance for AI agents on how to perform common tasks within this repository.

## Agent Planning

* When planning tasks always ensure that you think about tests and whether or not you need new tests or need to modify existing tests.
* Ensure that testing is part of your plan.

## Testing

Prior to running tests it would be good to check if you have any existing kopf processes running since multiple kopf operators running
could affect test results.

The preferred way of testing is to run individual tests with:

    ```bash
    # To sync your uv environment
    uv sync
    # uv run pytest -v <path_to_test>
    uv run tests/test_ssh.py::test_ssh_config_with_kubeconfig_path # for individual tests
    uv run tests/test_ssh.py # for whole test files
    ```

You can also run the entire test suite with but this will take a long time:

    ```bash
    make test
    ```

## Updating Documentation

To ensure documentation is up-to-date with recent code changes, follow these steps:

1.  Run the `dev/docs/generate_doc_updates.py` script. This script will analyze all `README.md` files and report on recent commits in their respective directories since the documentation was last updated. This provides context on what might be outdated.

    ```bash
    uv run dev/docs/generate_doc_updates.py
    ```

2.  Review the output from the script. For each `README.md` that has recent changes in its directory, use the commit information as context to update the file.

3.  Use the following prompt when performing the update:

    > Update the documentation with the provided context. Prioritize factuality, do not overhaul docs if you do not have to.
