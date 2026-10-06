# Tutorial: Mastering ectop

This tutorial will guide you through using `ectop` to monitor and manage a realistic ecFlow suite.

## Prerequisites

1.  **ecFlow Server**: Ensure you have an ecFlow server running.
    ```bash
    ecflow_server --port 3141 &
    ```
2.  **ectop**: Installed and ready to use.

## Step 1: Initialize the Demo Environment

We provide a comprehensive demo script in `examples/ectop_demo.py` that sets up a suite with various features (limits, triggers, and expected failures).

1.  **Load the demo suite**:
    ```bash
    python examples/ectop_demo.py --port 3141 --load
    ```
    This script will:
    - Create a suite named `ectop_demo`.
    - Generate all necessary task scripts in `./ectop_demo_home`.
    - Load the definition into your local server and begin playback.

## Step 2: Launch ectop

Start `ectop` to monitor the demo suite:

```bash
ectop --port 3141
```

You should see the `ectop_demo` suite in the tree on the left.

![ectop main view](assets/main_view.svg)

---

## 🛠️ Core Interactions

### 🌳 Navigating the Tree
- Use **Arrow Keys** to move up and down.
- Press **Enter** to expand or collapse families and suites.
- Icons indicate node status:
    - 🔵 **Queued**: Waiting for its turn.
    - 🔥 **Active**: Currently running.
    - 🟢 **Complete**: Finished successfully.
    - 🔴 **Aborted**: Failed.
    - 🟠 **Suspended**: Paused by a user.

### 📄 Viewing Node Content
Select a task (e.g., `ectop_demo/operational/batch/process_1`) and press `l` to **Load**.
- **Output Tab**: View the live log output.
- **Script Tab**: See the `.ecf` source script.
- **Job Tab**: Inspect the generated job file sent to the scheduler.

### ⚡ Node Operations
Manage your workflow with simple keypresses:
- **Suspend (`s`) / Resume (`u`)**: Pause or unpause nodes.
- **Kill (`k`)**: Terminate an active task.
- **Execute (`x`)**: Immediately run a task, bypassing its triggers.
- **Force Complete (`f`) / Aborted (`a`)**: Manually mark a task as successful or failed.
- **Requeue (`Shift + R`)**: Reset a node and its children to the Queued state.

---

## 🔍 Advanced Features

### ❓ Why is it Queued?
If a task is stuck in the `Queued` state, select it and press `w` to open the **Why Inspector**. It will show you exactly what is blocking the node, such as:
- Unmet trigger expressions (e.g., `task_a == complete`).
- Resource limits (e.g., `max_jobs` limit reached).
- Time dependencies.

![Why Inspector](assets/why_inspector.svg)

### 🕵️ Searching the Suite
In large deployments, finding a node can be difficult.
1. Press `/` to open the **Search Box**.
2. Type part of a node name or path. Search runs across the synchronized definitions, including collapsed branches.
3. The tree selects the match for the latest query. Press **Enter** to search for the next matching path from the current selection.
4. Press **Escape** to clear and close search. Clearing the input or moving focus away also invalidates pending results, so an older query cannot move the tree afterward.

### 🎭 Filtering by Status
Focus on what matters by filtering the tree.
- **Cycle Filter (`Shift + F`)**: Cycle through status filters like `Aborted`, `Active`, or `Suspended`.
- **Focus Mode (`Shift + H`)**: A quick toggle to hide all `complete` nodes from the tree, allowing you to focus on work that is still in progress.

### 🧟 Zombie Management
Orphaned tasks (zombies) can sometimes clog your scheduler. Press `Shift + Z` to open the **Zombie Dashboard**.
- View all zombies across the server with their process IDs and creation times.
- Select a zombie and use `f` to **Fob**, `F` to **Fail**, or `a` to **Adopt** it.

### 📊 Performance Timeline
To identify bottlenecks in your workflow, check the **Timeline** tab in the main content area (available after pressing `l` on a family or task).

> If you modify features, API, or usage, you MUST update the documentation immediately.
- Visualizes the relative state-change times of sibling tasks.
- Helps identify which tasks in a family are taking the longest to start or finish.

### 📝 Managing Variables
Select any node and press `v` to open the **Variable Tweaker**.
- View **User**, **Generated**, and **Inherited** variables.
- Press **Edit** to modify an existing variable.
- Press **Add** to create a new variable (useful for overriding inherited values).

![Variable Tweaker](assets/variable_tweaker.svg)

### ✍️ On-the-fly Script Editing
Need to fix a bug in a script?
1. Select the task and press `e`.
2. Your local `$EDITOR` opens with the script content.
3. Save and exit with status 0. `EDITOR` may include quoted arguments, for example `EDITOR='code --wait' ectop`.
4. `ectop` atomically updates the task's `.ecf` source only when the content changed. The source path from `ECF_SCRIPT`, `ECF_FILES`, or `ECF_HOME` must be accessible and writable from the machine running ectop. A non-zero editor exit leaves the source unchanged, and the temporary file is removed on all exit paths.
5. After an update, `ectop` offers to **Requeue** the task to apply the fix immediately.

### 🔄 Automatic Refresh
The `--refresh` interval updates the node tree and server status whether or not live logs are enabled. Live output polling remains controlled by the `t` toggle. If a refresh is still running when another interval arrives, ectop records at most one follow-up refresh. An error leaves the last tree visible and marks the status bar with a sync error.

### 🧵 File retrieval
Press `l` to request output, script, and processed job files. Each file view reports its result independently, so one unavailable file does not hide the other successful files. You can continue navigating while these requests run; ectop discards results after the selected node changes. Calls on the shared ecFlow client remain serialized for native client safety.

### ⚙️ Connection settings
`--host` and `ECF_HOST` accept a non-empty hostname or IP address. `--port` and `ECF_PORT` accept TCP ports from 1 through 65535. `--refresh` and `ECTOP_REFRESH` require a finite number greater than zero. Command-line values override environment values; invalid values report which setting needs correction.

---

## 🎮 Server Management

`ectop` also allows you to control the ecFlow server itself:
- **Halt Server (`Shift + X`)**: Stops the server from scheduling new tasks.
- **Start Server (`Shift + S`)**: Resumes scheduling.
- **Begin Suite (`b`)**: Starts playback of the selected suite.
- **Load New Definitions (`Shift + L`)**: Load additional `.def` files without leaving the TUI.

---

## Next Steps

- Explore the [**Architecture**](architecture.md) to understand how `ectop` maintains performance.
- Check the [**Options**](options.md) for a full list of configuration environment variables.
