<!-- If you modify features, API, or usage, you MUST update the documentation immediately. -->
# Architecture

`ectop` is built using the [Textual](https://textual.textualize.io/) framework, providing a modern and responsive TUI experience.

## Design Goals

1.  **Responsiveness**: The UI should never freeze, even when performing long-running network operations or fetching large files.
2.  **Simplicity**: Provide a clean wrapper around the `ecflow` Python API.
3.  **Extensibility**: Modular widget design for easy expansion of features.

## Core Components

### App (`ectop.app.Ectop`)
The main application class that coordinates the UI, handles global key bindings, and manages the lifecycle of the application. It uses Textual's `Screen` and `Worker` systems to handle concurrency.

### Client (`ectop.client.EcflowClient`)
A thin wrapper around `ecflow.Client`. It provides:
- Simplified API for common operations.
- Centralized error handling and conversion of `RuntimeError` into more informative exceptions.
- Mapping of node states to visual icons.

### Widgets (`ectop.widgets`)
The UI is decomposed into several modular widgets:
- **SuiteTree**: A customized `Tree` widget that displays the hierarchical structure of ecFlow suites. It uses **lazy loading** to only fetch and render nodes as they are expanded, ensuring high performance for large trees.
- **StatusBar**: Displays real-time server connection status and the timestamp of the last successful synchronization.
- **MainContent**: A `TabbedContent` widget that hosts the Log, Script, and Job views.
- **SearchBox**: A specialized input for live-filtering the suite tree.
- **Modals**: Lightweight screens for confirmation (`ConfirmModal`), variable editing (`VariableTweaker`), and "Why" inspection (`WhyInspector`).

## Concurrency and Workers

To maintain a smooth UI, all blocking calls to the ecFlow server (which involve network I/O) are offloaded to **Textual Workers** using the `@work` decorator.

- **Thread-safe Updates**: Workers produce plain results and deliver them through the running app's UI thread. Delivery is discarded after shutdown; a worker never calls a widget directly as a fallback.
- **Worker Groups**: Search, tree building, child loading, and refresh use separate named groups so an exclusive worker cannot cancel unrelated work.
- **Definition Snapshots**: A refresh generation is projected into immutable plain node records. Search, filter visibility, and lazy tree expansion read this snapshot; widgets are only read or changed on the UI thread.
- **Filter Indexes**: Status-to-path and ancestor visibility sets are computed once per snapshot. Filter and Focus Mode changes reuse those indexes, keep required ancestors visible, and restore the selected path when it remains in view. The 10,000-node target is below one second at the 95th percentile.
- **Latest Search Wins**: Search input is debounced, searches all paths including collapsed branches, and applies a result only when both its query and definition generations are current. Clearing, cancelling, or leaving the search field invalidates pending results.
- **Serialized ecFlow Client**: Calls through the shared `ecflow.Client` remain protected by one lock because the ecFlow API does not document safe concurrent access.
- **Exclusive Workers**: Operations that supersede earlier work use `exclusive=True` within their own named group.
- **Node Files**: Output, script, and processed-job requests are submitted as separate background calls. Each view receives its own success or error, while the shared client lock continues to serialize native ecFlow calls. The app tracks the selected path across asynchronous tree refreshes; results for a different current node are dropped.
- **Script Editing**: `$EDITOR` is split into an executable and arguments with shell-style quoting, then launched without a shell. Only a successful process that changes the file atomically replaces its ecFlow `.ecf` source. ectop resolves the source from `ECF_SCRIPT`, `ECF_FILES`, or `ECF_HOME`; the source must be accessible and writable on the machine running ectop. The temporary edit file is removed for success, failure, and cancellation. ecFlow locates scripts using these variables and directory search rules ([official file-location algorithm](https://ecflow.readthedocs.io/en/5.13.0/glossary.html#ecf-file-location-algorithm)).
- **Textual Support Floor**: ectop supports Textual 0.70.0 and newer. CI tests the declared minimum and the latest release; older versions are outside the supported range.

## Event Loop

`ectop` uses the configured interval for tree and server-status refresh independently of live-log retrieval. Log polling remains conditional on the "Live" toggle and the active output tab. A refresh already in progress coalesces timer ticks rather than building an unbounded queue. A failed refresh updates the connection status and keeps the last definitions snapshot visible.

> If you modify features, API, or usage, you MUST update the documentation immediately.
