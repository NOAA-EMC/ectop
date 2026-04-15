[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](LICENSE)

# ectop

`ectop` is a powerful Textual-based Terminal User Interface (TUI) for monitoring and controlling [ecFlow](https://ecflow.readthedocs.io/en/latest/) servers.

## Features

- **Real-time Monitoring**: View the status of your ecFlow suites, families, and tasks in a hierarchical tree view.
- **Node Management**: Suspend, resume, kill, and force-complete nodes directly from the TUI.
- **File Inspection**: View job output logs, scripts, and job files for any node.
- **Search**: Quickly find nodes in large trees with live search and lazy loading.
- **Command Palette**: Access all features via a searchable command interface.
- **Why?**: Inspect why a node is in its current state, including triggers and limits.
- **Variable Management**: View and modify node variables on the fly.
- **Interactive Script Editing**: Edit scripts in your preferred editor and update them on the server.

## Installation

### Using Conda (Recommended)

```bash
conda env create -f environment.yml
conda activate ectop
```

### Using Pip

```bash
pip install .
```

*Note: `ecflow` must be installed on your system. It is typically available via Conda.*

## Usage

Start `ectop` by running:

```bash
ectop
```

By default, it connects to `localhost:3141`.

### Key Bindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `p` | Command Palette |
| `r` | Refresh Tree |
| `l` | Load Logs/Script for selected node |
| `s` | Suspend selected node |
| `u` | Resume selected node |
| `k` | Kill selected node |
| `f` | Force Complete selected node |
| `/` | Search nodes |
| `w` | Why? (Inspect dependencies) |
| `e` | Edit & Rerun script |
| `t` | Toggle Live Log updates |
| `v` | View/Edit Variables |

## Documentation

Full documentation is available at [https://noaa-emc.github.io/ectop/](https://noaa-emc.github.io/ectop/).

## License

This project is licensed under the [CC0 1.0 Universal License](LICENSE).

## Disclaimer
> [!IMPORTANT]
> **Disclaimer:** This software is provided "as is". Please see the full [DISCLAIMER.md](DISCLAIMER.md) for legal information regarding its use in production environments and software.
