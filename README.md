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

Run tools using the following format:

```bash
jackknife <tool_name> [tool_arguments...]
```

- `<tool_name>`: The name of the tool script (without the `.py` extension) in the `tools/` directory
- `[tool_arguments...]`: Any arguments you want to pass directly to the tool script

### Example

Using the included `giftomp4` tool:

```bash
# Show help for the giftomp4 tool
jackknife giftomp4 --help

# Convert a GIF to MP4
jackknife giftomp4 my_animation.gif -o my_video.mp4 --fps 24 --verbose
```

### Cascading Tool Execution

You can run multiple tools in sequence with a single command:

```bash
# Run multiple tools in sequence
jackknife tool1,tool2,tool3

# Stop on first error (default behavior)
jackknife tool1,tool2,tool3

# Continue even if a tool fails
jackknife tool1,tool2,tool3 --continue-on-error
```

#### Tool-Specific Arguments

You can provide arguments for each tool using square brackets:

```bash
# Run tools with their own arguments
jackknife "tool1[--option value],tool2[arg1 arg2],tool3[--flag]"
```

> **Note**: When using tool-specific arguments, you need to quote the entire command in most shells to prevent the brackets from being interpreted by the shell.

### Environment Sharing

Jackknife can optimize disk space usage by reusing compatible environments:

```bash
# Enable environment sharing (default)
jackknife mytool

# Disable environment sharing
jackknife --no-share-environments mytool
```

You can also control this behavior globally with an environment variable:

```bash
# Disable environment sharing globally
export JACKKNIFE_SHARE_ENVIRONMENTS=false
jackknife mytool

# Enable environment sharing globally
export JACKKNIFE_SHARE_ENVIRONMENTS=true
jackknife mytool
```

When environment sharing is enabled, Jackknife will:
1. Check if a tool's requirements are a subset of an existing environment
2. If found, create a symlink to the existing environment instead of a new one
3. Use the shared environment for running the tool

This is particularly useful when you have many tools with overlapping dependencies.

## How It Works

1. When you run `jackknife giftomp4 ...`, the script finds `tools/giftomp4.py`
2. It checks for a corresponding virtual environment in `~/.jackknife_envs/giftomp4`
3. If needed, it creates the environment and installs required dependencies
4. It executes the tool with your arguments using the isolated Python interpreter

## Adding New Tools

There are two ways to create tools for Jackknife:

### 1. Using the Tool Decorator (Recommended)

The easiest way to create a tool is to use the `@tool` decorator, which automatically handles argument parsing for you:

```python
#!/usr/bin/env python3
"""Example tool using the Jackknife decorator system."""

from jackknife.tool_helpers import tool, argument

@tool
def my_tool(
    input_file: argument(help="Path to the input file to process"),
    output_file: argument(help="Path to save the output", required=False) = None,
    verbose: argument(flag=True, help="Enable verbose output", short_name="v") = False,
    count: argument(help="Number of items to process", type=int) = 1,
):
    """My awesome tool that does something useful."""
    # Your tool implementation here
    if verbose:
        print(f"Processing {input_file} with count={count}")

    # Do something with the input file

    if output_file:
        print(f"Writing output to {output_file}")

    return 0  # Return an exit code
```

### 2. Traditional Script Approach

You can also create tools as traditional Python scripts with their own argument parsing:

```python
#!/usr/bin/env python3
"""Example tool using traditional argparse."""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="My awesome tool")
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument("--output-file", "-o", help="Output file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--count", "-c", type=int, default=1, help="Number of items to process")

    args = parser.parse_args()

    # Your tool implementation here

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Both approaches work with jackknife:

1. Create your Python script (e.g., `mytool.py`) inside the `tools/` directory
2. If your tool has dependencies, list them in `mytool.requirements.txt` in the same directory
3. Run it: `jackknife mytool [arguments...]`

## Environment Location

By default, environments are stored in `~/.jackknife_envs/`. You can change this location:

```bash
export JACKKNIFE_ENVS_DIR=/path/to/your/envs
jackknife giftomp4 input.gif
```

Jackknife will create separate environments for each tool, or reuse compatible environments if sharing is enabled.

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