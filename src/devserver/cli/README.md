# devctl - DevServer CLI

The `devctl` CLI provides a simple interface for managing DevServers.

## Commands

| Command | Description |
| --- | --- |
| `devctl create` | Create a new DevServer. |
| `devctl list` | List all DevServers. |
| `devctl flavors`| List available DevServerFlavors. |
| `devctl delete <name>` | Delete a DevServer. |

### `devctl create`

Creates a new DevServer.

**Usage:**

```bash
devctl create [OPTIONS]
```

**Options:**

| Option | Description | Default |
| --- | --- | --- |
| `--name TEXT` | The name of the DevServer. | `dev` |
| `--flavor TEXT` | **(Required)** The flavor of the DevServer. | |
| `--image TEXT`| The container image to use. | |
| `--ssh-public-key-file TEXT` | Path to the SSH public key file. | `~/.ssh/id_rsa.pub` |
| `--time, --ttl TEXT` | The time to live for the DevServer (e.g., `8h`, `30m`). | `4h` |
