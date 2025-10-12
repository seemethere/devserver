# Agent Instructions

This document provides guidance for AI agents on how to perform common tasks within this repository.

## Updating Documentation

To ensure documentation is up-to-date with recent code changes, follow these steps:

1.  First, ensure you have an active virtual environment. If not, you can set one up by following the instructions in the main `README.md`. A common way to activate it is:
    ```bash
    source .venv/bin/activate
    ```

2.  Run the `dev/docs/generate_doc_updates.py` script. This script will analyze all `README.md` files and report on recent commits in their respective directories since the documentation was last updated. This provides context on what might be outdated.

    ```bash
    .venv/bin/python3 dev/docs/generate_doc_updates.py
    ```

3.  Review the output from the script. For each `README.md` that has recent changes in its directory, use the commit information as context to update the file.

4.  Use the following prompt when performing the update:

    > Update the documentation with the provided context. Prioritize factuality, do not overhaul docs if you do not have to.
