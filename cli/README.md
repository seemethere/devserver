# devctl CLI

`devctl` is a command-line interface for managing `DevServer` resources. It is designed to be run inside the bastion host and provides a simplified, user-friendly alternative to `kubectl`.

## Overview

`devctl` is a Python-based CLI built with the `click` and `rich` libraries. It interacts with the Kubernetes API to manage the lifecycle of `DevServer` resources, providing a streamlined experience for creating, accessing, and deleting development environments.

## Commands

| Command                               | Description                                         |
| ------------------------------------- | --------------------------------------------------- |
| `devctl status`                       | Show environment and DevServer status               |
| `devctl info`                         | Show information about available commands           |
| `devctl test-k8s`                     | Test Kubernetes connectivity and permissions        |
| `devctl create <name> --flavor <flavor>` | Create a new development server                  |
| `devctl list`                         | List your development servers                       |
| `devctl describe <name>`              | Show detailed information about a DevServer         |
| `devctl ssh <name>`                   | SSH into a development server (interactive shell)   |
| `devctl exec <name> -- <command>`     | Execute a command in a development server           |
| `devctl delete <name>`                | Delete a development server                         |
| `devctl flavors`                      | List available `DevServerFlavor`s                   |
| `devctl --help`                       | Show detailed help for a command                    |

## Getting Started

`devctl` is pre-installed in the bastion host environment. To use it, simply SSH into the bastion and run the desired command.

```bash
# SSH into the bastion
ssh -i .demo-keys/bastion_demo testuser@localhost -p 2222

# Inside the bastion, you can now use devctl
devctl status
```
