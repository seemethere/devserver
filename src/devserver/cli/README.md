# devctl - DevServer CLI

The `devctl` command-line interface provides a simple way to manage your DevServers.

## Commands

### `create`

Create a new DevServer.

```bash
devctl create --name my-server --flavor cpu-small
```

### `delete`

Delete a DevServer.

```bash
devctl delete my-server
```

### `describe`

Get detailed information about a DevServer.

```bash
devctl describe my-server
```

### `list`

List all running DevServers.

```bash
devctl list
```

### `ssh`

Connect to a DevServer with SSH.

```bash
devctl ssh my-server
```

This command also provides a seamless SSH integration. On first use, it will ask for permission to add an `Include` directive to your `~/.ssh/config` file. Once approved, you can connect to any devserver using the standard `ssh` command, which also enables integration with tools like VS Code Remote-SSH.

```bash
# After the one-time setup, this just works:
ssh my-server
```

### `config`

Manage `devctl` configuration.

**`config ssh-include [enable|disable]`**

Manually enable or disable the automatic SSH config management.

```bash
# Manually enable the feature
devctl config ssh-include enable

# Manually disable the feature
devctl config ssh-include disable
```
