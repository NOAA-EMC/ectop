<!-- If you modify features, API, or usage, you MUST update the documentation immediately. -->
# Contributing to ectop

Thank you for your interest in improving `ectop`!

## Development Environment

We recommend using Conda or Mamba to manage the development environment, as it simplifies the installation of the `ecflow` dependency.

```bash
# Clone the repository
git clone https://github.com/bbakernoaa/ectop.git
cd ectop

# Create the environment
conda env create -f environment.yml
conda activate ectop

# Install the package in editable mode with dev dependencies
pip install -e .[dev]
```

## Coding Standards

- **Python Version**: Required 3.11+.
- **Type Hints**: All function signatures must include type hints.
- **Documentation**: We use **Google-style** docstrings.
- **Formatting**: We use `ruff` for linting and formatting.

### Pre-commit Hooks

We use `pre-commit` to ensure code quality. Install the hooks with:

```bash
pre-commit install
```

## Running Tests

`ectop` uses `pytest` and `pytest-asyncio` for testing.

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src
```

Note: Some tests mock the `ecflow` client to avoid requiring a running server.

## Building Documentation

Documentation is built with `mkdocs` and the `mkdocs-material` theme.

```bash
# Install doc dependencies
pip install -e .[docs]

# Serve the documentation locally
mkdocs serve
```

## Pull Request Process

1.  Create a new branch for your feature or bugfix.
2.  Ensure all tests pass and linting is clean.
3.  Include unit tests for any new functionality.
4.  Update the documentation if you change the API or usage.
5.  Submit a Pull Request to the `main` branch.

### Semantic Versioning and Releases

Use a Conventional Commit title for every pull request. The title becomes the release input when the pull request is merged to `main`:

| Title prefix | Release impact |
| --- | --- |
| `fix:` or `perf:` | Patch version |
| `feat:` | Minor version |
| `type(scope)!:` or a `BREAKING CHANGE:` footer | Major version |
| `docs:`, `test:`, `ci:`, `refactor:`, `build:`, `chore:`, `revert:`, or `style:` | No version bump by itself |

The `Validate semantic-release PR title` CI check enforces the title format. Squash-merge pull requests so the validated title becomes the commit message that semantic release reads; if you use another merge method, keep each commit title conventional too. After merge, the release job runs only when linting and the Python/ecFlow test matrix pass. Python Semantic Release updates the version in `pyproject.toml` and `src/ectop/__init__.py`, updates `CHANGELOG.md`, builds distributions, tags the commit as `vX.Y.Z`, and creates a GitHub Release with the wheel and source archive attached. Publishing to PyPI is not configured.

The repository must allow the workflow's `GITHUB_TOKEN` to push its version commit and tag to `main` and create releases. If branch protection blocks workflow pushes, configure an Actions bypass for this release job before expecting automatic releases. Require the PR-title check in branch protection to prevent nonconventional titles from bypassing version selection.
