# Creating Tools for Jackknife

This guide explains how to create new tool scripts that can be run using the Jackknife utility.

## Introduction

A Jackknife tool is simply a Python script (`.py` file) placed in the `tools/` directory at the root of the Jackknife project. When you run `jackknife run my_tool`, Jackknife finds `tools/my_tool.py`, sets up an isolated Python environment for it (if needed), and executes the script.

The primary benefit is that each tool manages its dependencies independently via a corresponding `.requirements.txt` file, preventing conflicts between tools.

## Prerequisites

-   Basic familiarity with Python 3.
-   Understanding of command-line arguments.
-   While Jackknife uses `uv` internally, having `uv` installed locally is helpful for testing.

## Core Concepts

-   **Location**: All tool scripts *must* reside in the `tools/` directory.
-   **Naming**: A script named `tools/my_tool.py` is executed via `jackknife run my_tool`.
-   **Dependencies**: If `tools/my_tool.py` requires external packages, list them in `tools/my_tool.requirements.txt`. Jackknife will use `uv` to install these into an isolated virtual environment located at `~/.jackknife_envs/my_tool/` (or a shared environment if compatible and enabled).
-   **Execution**: Jackknife attempts to run tools in two ways:
    1.  **Direct Import**: If a tool uses the `@tool` decorator (see below) and its dependencies *do not* conflict with Jackknife's own dependencies, Jackknife *may* import and run the tool function directly within its own process for slightly faster startup.
    2.  **Subprocess Execution (Default)**: This is the standard and most common method. Jackknife executes the tool script (`python tools/my_tool.py ...`) using the Python interpreter from the tool's dedicated virtual environment. This ensures complete isolation and is always used for standard scripts or decorated scripts that have their own dependencies.

## Creating a Tool: Two Approaches

You can create tools using a standard script approach or leverage Jackknife's helper decorators.

### Approach 1: Using the `@tool` Decorator (Recommended)

This is the preferred method as it simplifies argument parsing significantly.

**Benefits:**

-   No boilerplate `argparse` code needed.
-   Command-line arguments are generated automatically from function parameters and type hints.
-   Clear definition of arguments using the `@argument` helper.

**Helpers:**

-   `@tool`: Decorator applied to the main function of your tool.
-   `argument()`: Used within the function signature to provide details (help text, type, flags, etc.) for specific parameters.

**Example (`tools/example_decorated.py`):**

```python
#!/usr/bin/env python3
"""Example tool using the Jackknife decorator system."""

# Note: tool_helpers itself is part of the main jackknife package,
# so it doesn't need to be in the tool's requirements.txt
from jackknife.tool_helpers import tool, argument

@tool
def decorated_example(
    input_file: argument(
        help_text="Path to the input file to process",
        metavar="INPUT"
    ),
    output_file: argument(
        help_text="Path to save the output (optional)",
        required=False,
        short_name="o"
    ) = "default_output.txt", # Default value
    verbose: argument(
        flag=True, # Treat as --verbose flag
        help_text="Enable verbose output",
        short_name="v"
    ) = False, # Default for flags is usually False
    count: argument(
        help_text="Number of items to process",
        arg_type=int # Specify the type
    ) = 1,
    mode: argument(
        help_text="Processing mode",
        choices=["fast", "slow", "careful"] # Restrict choices
    ) = "fast",
):
    """An example tool demonstrating the @tool and @argument decorators."""
    # Your tool implementation here
    if verbose:
        print(f"Running in verbose mode!")
        print(f"Input: {input_file}")
        print(f"Output: {output_file}")
        print(f"Count: {count}")
        print(f"Mode: {mode}")

    print("Processing complete.")

    # Return an exit code (0 for success, non-zero for failure)
    return 0

# No need for if __name__ == "__main__" when using @tool,
# Jackknife handles the execution.
```

**How `@argument` works:**

-   `help_text`: Populates the `--help` description.
-   `arg_type`: Sets the expected type (like `type=int` in `argparse`). If omitted, it defaults to `str`.
-   `default`: Provides a default value if the argument isn't given.
-   `choices`: Restricts allowed values for the argument.
-   `required`: Set to `True` if the argument must be provided. Often inferred if no default is given.
-   `flag`: Set to `True` for boolean flags (like `--verbose`). The `default` determines if it's `--flag` (default `False`) or `--no-flag` (default `True`).
-   `short_name`: Defines a short option (e.g., `-v`).
-   `metavar`: Custom display name in help messages.

Your function should return an integer representing the exit code (0 for success).

### Approach 2: Traditional Script (Standard `argparse`)

This method involves writing a standard Python script that handles its own argument parsing, typically using the `argparse` module.

**When to use:**

-   Integrating existing scripts into Jackknife.
-   When you need argument parsing logic more complex than the `@tool` decorator provides.

**Example (`tools/example_traditional.py`):**

```python
#!/usr/bin/env python3
"""Example tool using traditional argparse."""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        description="An example tool using traditional argparse.",
        epilog="Example epilog text."
    )
    parser.add_argument(
        "input_file",
        metavar="INPUT",
        help="Path to the input file to process"
    )
    parser.add_argument(
        "--output-file", "-o",
        default="default_output.txt",
        help="Path to save the output (optional, default: %(default)s)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", # Standard boolean flag
        help="Enable verbose output"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1,
        help="Number of items to process (default: %(default)s)"
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "slow", "careful"],
        default="fast",
        help="Processing mode (choices: %(choices)s, default: %(default)s)"
    )

    # Add a mutually exclusive group example
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fast-mode", action="store_true", help="Use fast mode (alt)")
    group.add_argument("--careful-mode", action="store_true", help="Use careful mode (alt)")

    args = parser.parse_args()

    # Your tool implementation here
    if args.verbose:
        print("Running in verbose mode!")
        print(f"Input: {args.input_file}")
        print(f"Output: {args.output_file}")
        print(f"Count: {args.count}")
        print(f"Mode: {args.mode}")
        if args.fast_mode:
            print("Fast mode (alt) enabled")
        elif args.careful_mode:
            print("Careful mode (alt) enabled")

    print("Processing complete.")

    # Return an exit code
    return 0

# Crucial for standard scripts:
# Ensure main() is called and its exit code is passed to sys.exit
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

```

**Key requirements for traditional scripts:**

-   Must handle their own argument parsing (`argparse`, `typer`, etc.).
-   Must include the `if __name__ == "__main__":` guard.
-   The main execution logic should be called from within the guard.
-   The script must explicitly exit with the desired status code using `sys.exit()`. Jackknife relies on the subprocess exit code for these scripts.

## Handling Dependencies

If your tool requires packages not included in the standard Python library:

1.  Create a file named `your_tool_name.requirements.txt` in the `tools/` directory alongside `your_tool_name.py`.
2.  List each dependency on a separate line.
3.  **Pin specific versions** using `==` for reproducibility (e.g., `requests==2.31.0`). You can use `pip freeze` within a test environment or `uv pip freeze` to find current versions.

```text
# tools/my_api_tool.requirements.txt
requests==2.31.0
rich==13.7.1
```

Jackknife will automatically detect this file and use `uv pip install -r ...` to install these dependencies into the tool's isolated environment before running the script.

## Best Practices & Tips

-   **Console Output**: Use the `rich` library for formatted and colorful terminal output. Remember to add `rich` to your `.requirements.txt`.
-   **Error Handling**: Catch expected errors (e.g., `FileNotFoundError`, API errors) and print informative messages to standard error (`sys.stderr`).
-   **Keyboard Interrupt**: Catch `KeyboardInterrupt` for graceful termination if the user presses Ctrl+C.
-   **Exit Codes**: Return `0` on success and a non-zero integer (typically `1`) on failure. This allows Jackknife and shell scripts to detect errors.
-   **Complex CLIs**: If not using the `@tool` decorator and you need features like subcommands, consider using `typer` instead of `argparse` in your traditional script (add `typer` to requirements).
-   **Local Testing**: Activate the tool's specific environment to test interactively or run linters/formatters:
    ```bash
    # Create/update the environment (if needed)
    jackknife run my_tool --help

    # Activate the environment
    eval $(jackknife activate my_tool)

    # Now you are in the tool's venv
    (my_tool) $ python tools/my_tool.py --help
    (my_tool) $ # Run linters etc.
    (my_tool) $ deactivate
    ```

## Adding Your Tool to the Project

1.  Place your `my_tool.py` script in the `tools/` directory.
2.  If it has dependencies, add `my_tool.requirements.txt` to the `tools/` directory.
3.  Consider adding a brief mention or example to the main `README.md` if the tool is generally useful.
4.  Add tests for your tool in the `tests/` directory (see `CONTRIBUTING.md` or existing tests for examples).