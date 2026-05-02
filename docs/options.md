# Configuration & Options

`ectop` can be configured via command-line arguments, environment variables, and interactive key bindings.

## Command-Line Options

You can pass the following arguments when starting `ectop` from the terminal:

| Option | Description | Default |
|--------|-------------|---------|
| `--host <string>` | The hostname or IP address of the ecFlow server. | `localhost` |
| `--port <int>` | The port number the ecFlow server is listening on. | `3141` |
| `--refresh <float>` | The interval (in seconds) for automatic tree and log updates. | `2.0` |

Example:
```bash
ectop --host my-ecflow-server --port 3500 --refresh 5.0
```

## Environment Variables

`ectop` respects the following environment variables, which can be used instead of CLI arguments:

| Variable | Description | Default |
|----------|-------------|---------|
| `ECF_HOST` | The hostname of the ecFlow server. | `localhost` |
| `ECF_PORT` | The port number of the ecFlow server. | `3141` |
| `ECTOP_REFRESH` | The automatic refresh interval in seconds. | `2.0` |
| `EDITOR` | The text editor used for editing node scripts on the fly. | `vi` |

## Key Bindings

Once `ectop` is running, you can use the following keys to interact with the application:

### Navigation & General

| Key | Action | Description |
|-----|--------|-------------|
| `q` | **Quit** | Exits the application immediately. |
| `p` | **Command Palette** | Opens a searchable list of all available commands. |
| `r` | **Refresh Tree** | Manually triggers a full synchronization of the suite tree from the server. |
| `/` | **Search** | Opens the live search box to find nodes by name or path. |
| `c` | **Copy Path** | Copies the absolute ecFlow path of the selected node to the system clipboard. |

### Node Operations

| Key | Action | Description |
|-----|--------|-------------|
| `s` | **Suspend** | Suspends (pauses) the selected node. |
| `u` | **Resume** | Resumes the selected suspended node. |
| `k` | **Kill** | Kills the currently running task. |
| `f` | **Force Complete** | Manually sets the selected node to the `complete` state. |
| `R` (Shift+R) | **Requeue** | Resets the selected node and its children to the `queued` state. |

### Inspection & Editing

| Key | Action | Description |
|-----|--------|-------------|
| `l` | **Load Node** | Fetches the latest Logs, Script, and Job files for the selected node. |
| `w` | **Why?** | Opens the "Why?" inspector to analyze why a node is waiting or blocked. |
| `v` | **Variables** | Opens the Variable Tweaker to view, edit, or add node variables. |
| `e` | **Edit Script** | Opens the task script in your `$EDITOR`. Saving and exiting will update it on the server. |
| `t` | **Toggle Live Log** | Toggles periodic updates for the currently viewed output log. |
| `Z` (Shift+Z) | **Zombies** | Opens the Zombie Management Dashboard to view and resolve orphaned jobs. |
| `Ctrl+F` | **Search Content** | Allows searching for specific text within the currently displayed log or script. |

### Tree Filtering

| Key | Action | Description |
|-----|--------|-------------|
| `F` (Shift+F) | **Cycle Filter** | Cycles through status filters: `All`, `Aborted`, `Active`, `Queued`, `Submitted`, `Suspended`. |
| `H` (Shift+H) | **Focus Mode** | Toggles hiding of nodes with a `complete` state to declutter the tree. |

### Server Control

| Key | Action | Description |
|-----|--------|-------------|
| `S` (Shift+S) | **Start Server** | Restarts the ecFlow server's scheduling (Sets server state to `RUNNING`). |
| `H` (Shift+H) | **Halt Server** | Halts the ecFlow server's scheduling (Sets server state to `HALT`). |
