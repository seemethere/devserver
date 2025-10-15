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

It also supports SSH agent forwarding, which can be enabled by adding `--forward-agent` to the `devctl ssh` command or by configuring it in your `~/.ssh/config`.

```bash
# After the one-time setup, this just works:
ssh my-server
```

### `ssh-proxy`

Connect to a DevServer via an SSH proxy. This is useful for environments where direct SSH access is not possible.

```bash
devctl ssh-proxy my-server
```

### `user`

Manage DevServer users.

**`user add --name <user-name> --public-key-file <path-to-public-key>`**

Adds a new user with their public SSH key.

```bash
devctl user add --name test-user --public-key-file ~/.ssh/id_rsa.pub
```

**`user remove --name <user-name>`**

Removes a user.

```bash
devctl user remove --name test-user
```

**`user list`**

Lists all users.

```bash
devctl user list
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

## Global Flags

### `--namespace`

You can specify the Kubernetes namespace for most commands using the `--namespace` or `-n` flag.

```bash
devctl list --namespace dev-team
```

## Configuration

`devctl` can be configured via a YAML file located at `~/.config/devctl/config.yaml`. The first time you run `devctl`, a default configuration file will be created if one does not already exist.

### Default Configuration

Here is the default configuration:

```yaml
ssh:
  public_key_file: "~/.ssh/id_rsa.pub"
  private_key_file: "~/.ssh/id_rsa"
  forward_agent: false
devctl_ssh_config_dir: "~/.config/devctl/ssh/"
```

### Options

*   `ssh.public_key_file`: Path to your SSH public key.
*   `ssh.private_key_file`: Path to your SSH private key.
*   `ssh.forward_agent`: Whether to enable SSH agent forwarding by default.
*   `devctl_ssh_config_dir`: Directory where `devctl` stores its generated SSH configuration files.
