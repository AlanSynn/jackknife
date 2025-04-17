# Jackknife

<img src="static/jackknife-logo.png" alt="Jackknife Logo" width="400"/>

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://codecov.io/gh/alansynn/jackknife)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **⚠️ WORK IN PROGRESS**
> This project is still in early development. Features may change, break, or be completely removed.

Jackknife is a command-line utility that allows you to run various Python tool scripts, each within its own isolated virtual environment managed by `uv`.

## Features

- **Isolated Environments**: Each tool runs in its own dedicated virtual environment
- **Fast Setup**: Uses `uv` for lightning-fast dependency installation
- **Modular Design**: Add new tools without modifying the core code
- **Easy Updates**: Update tool dependencies without affecting other tools
- **Zero Global Pollution**: No global package installations required
- **No-Boilerplate Tools**: Create tools without writing repetitive argparse code
- **Cascading Execution**: Run multiple tools in sequence with a single command
- **Environment Optimization**: Reuse compatible environments when possible to save space

## Prerequisites

- **Python**: Version 3.8 or higher
- **uv**: The extremely fast Python package installer and resolver

  ```bash
  # Linux/macOS
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  Verify installation: `uv --version`

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/alansynn/jackknife.git
   cd jackknife
   ```

2. **Install Jackknife:**
   ```bash
   # Regular installation
   pip install .

   # Development mode (for making changes)
   pip install -e .

   # Development mode with testing dependencies
   pip install -e ".[dev]"
   ```

## Usage

Jackknife now uses subcommands to organize its functionality:

### Running Tools (`run` command)

To run a single tool or a chain of tools, use the `run` subcommand:

```bash
jackknife run <tool_name | tool_chain> [tool_arguments...]
```

- `<tool_name>`: The name of the tool script (without the `.py` extension) in the `tools/` directory.
- `<tool_chain>`: A comma-separated list of tool names, optionally with arguments in brackets (see below).
- `[tool_arguments...]`: Any arguments you want to pass directly to the tool script (only applies when running a single tool).

#### Example (Single Tool)

Using the included `giftomp4` tool:

```bash
# Show help for the giftomp4 tool
jackknife run giftomp4 --help

# Convert a GIF to MP4
jackknife run giftomp4 my_animation.gif -o my_video.mp4 --fps 24 --verbose
```

#### Example (Tool Chain)

You can run multiple tools in sequence:

```bash
# Run multiple tools in sequence
jackknife run tool1,tool2,tool3

# Stop on first error (default behavior)
jackknife run tool1,tool2,tool3

# Continue even if a tool fails
jackknife run tool1,tool2,tool3 --continue-on-error
```

##### Tool-Specific Arguments in Chains

You can provide arguments for each tool in a chain using square brackets:

```bash
# Run tools with their own arguments
jackknife run "tool1[--option value],tool2[arg1 arg2],tool3[--flag]"
```

> **Note**: When using tool-specific arguments in chains, you often need to quote the entire tool chain string to prevent the brackets from being interpreted by your shell.

#### Environment Sharing

Environment sharing options are part of the `run` command:

```bash
# Run with environment sharing (default)
jackknife run mytool

# Run without environment sharing
jackknife run --no-share-environments mytool
```

You can also control this behavior globally with an environment variable:

```bash
# Disable environment sharing globally
export JACKKNIFE_SHARE_ENVIRONMENTS=false
jackknife run mytool

# Enable environment sharing globally
export JACKKNIFE_SHARE_ENVIRONMENTS=true
jackknife run mytool
```

### Activating a Tool's Environment (`activate` command)

Sometimes, you might want to manually work within a tool's isolated environment (e.g., to use its specific Python interpreter or installed packages directly). The `activate` command helps with this:

```bash
jackknife activate <tool_name>
```

This command prints the necessary shell command to activate the tool's virtual environment. **It does not activate the environment itself.**

#### Example (macOS/Linux - bash/zsh)

```bash
# Print the activation command for the 'cinit' tool's environment
jackknife activate cinit

# To actually activate it, use eval:
eval $(jackknife activate cinit)

# Now your shell is using the cinit environment
(cinit) $ python --version
(cinit) $ which python
# .../.jackknife_envs/cinit/bin/python

# Deactivate when done
(cinit) $ deactivate
$
```

#### Example (Windows - Command Prompt)

```batch
:: Print the activation command path
jackknife activate cinit

:: You would typically run the printed .bat script directly
C:\Users\You\.jackknife_envs\cinit\Scripts\activate.bat

(cinit) C:\Your\Project> REM Now in the tool's environment
```

> **Note:** The `activate` command only works if the tool has been run at least once with `jackknife run <tool_name>` to create its environment.

## How It Works

1. When you run `jackknife run giftomp4 ...`, the script finds `tools/giftomp4.py`.
2. It checks for a corresponding virtual environment in `~/.jackknife_envs/giftomp4`.
3. If needed (and not using a shared environment), it creates the environment and installs dependencies from `tools/giftomp4.requirements.txt` using `uv`.
4. It executes the tool script with your arguments using the isolated Python interpreter from the environment.

## Adding New Tools

Adding new tools to Jackknife is straightforward. You can either write a standard Python script or use the provided helper decorators for easier argument parsing.

For detailed instructions and examples, please see the dedicated guide:

**➡️ [docs/creating-tools.md](./docs/creating-tools.md)**

Here's a quick summary of the two approaches:

### 1. Using the Tool Decorator (Recommended)

Leverage `@tool` and `@argument` from `jackknife.tool_helpers` for automatic argument parsing. See `tools/example_decorated.py` and the guide for details.

### 2. Traditional Script Approach

Write a standard script using `argparse`, `typer`, or similar. Ensure it has an `if __name__ == "__main__":` block and uses `sys.exit()`. See `tools/example_traditional.py` and the guide for details.

**Key Steps:**

1. Place your Python script (e.g., `mytool.py`) inside the `tools/` directory.
2. If your tool has dependencies, list them in `mytool.requirements.txt` in the same directory.
3. Run it: `jackknife run mytool [arguments...]`

## Environment Location

By default, environments are stored in `~/.jackknife_envs/`. You can change this location:

```bash
export JACKKNIFE_ENVS_DIR=/path/to/your/envs
jackknife run giftomp4 input.gif
```

Jackknife will create separate environments for each tool, or reuse compatible environments if sharing is enabled. Use `jackknife activate <tool_name>` to get the command for entering a specific tool's environment manually.

## Code Quality

Jackknife uses several tools to maintain high code quality:

### Ruff for Linting and Formatting

[Ruff](https://github.com/astral-sh/ruff) is an extremely fast Python linter and formatter written in Rust. It replaces many traditional Python tools (Flake8, Black, isort, etc.) with a single, much faster alternative.

To run Ruff linting:

```bash
ruff check .
```

To format the code with Ruff:

```bash
ruff format .
```

### Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to manage our pre-commit hooks. After cloning the repository, install the hooks with:

```bash
pip install pre-commit
pre-commit install
```

This will automatically check the code quality before each commit.

## Testing

Jackknife includes a comprehensive test suite using pytest and coverage reporting.

### Running Tests

```bash
# Install development dependencies first
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test
pytest tests/test_cli.py::TestMain::test_successful_tool_execution
```

### Coverage Reports

The test suite includes coverage reporting to ensure code quality:

```bash
# Run tests with coverage (automatically includes --cov options)
pytest

# Generate HTML coverage report only
pytest --cov-report=html --cov-report=term-missing

# View coverage report
open htmlcov/index.html
```

Current test coverage: **91%**

### Test Structure

- **Unit Tests**: Test individual functions in isolation
- **Integration Tests**: Test how components work together
- **Functional Tests**: End-to-end tests using real subprocess calls

## Todo

- [x] Add boilerplate-free tool development with decorators
- [x] Add Ruff for linting and formatting
- [x] Add pre-commit hooks
- [x] Add cascading tool execution
- [x] Add environment sharing for compatible tools
- [x] Add `activate` command to get venv source string
- [ ] Add tool discovery plugins
- [ ] Add caching for faster startup
- [ ] Add shared environment option
- [ ] Implement tool update command
- [ ] Add tool versions and dependency locking

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Make sure to run tests and pre-commit hooks before submitting your PR.

## License

MIT License - See LICENSE file for details