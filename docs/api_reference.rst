=============
API Reference
=============

.. contents:: Table of Contents
   :depth: 3
   :local:
   :backlinks: none

This document provides reference information for Jackknife's public APIs, including the tool decorator system and environment management functionality.

Tool Decorator API
-----------------

The tool decorator system simplifies creating tools for Jackknife by automatically handling argument parsing and execution.

@tool Decorator
~~~~~~~~~~~~~

.. code-block:: python

    from jackknife.tool_helpers import tool, argument

    @tool
    def my_tool(
        input_file: argument(help="Path to the input file to process"),
        output_file: argument(help="Path to save the output", required=False) = None,
        verbose: argument(flag=True, help="Enable verbose output", short_name="v") = False,
        count: argument(help="Number of items to process", type=int) = 1,
    ):
        """My awesome tool that does something useful."""
        # Tool implementation
        return 0  # Return an exit code

The ``@tool`` decorator transforms a Python function into a command-line tool. It:

1. Automatically generates an argument parser based on the function's parameters
2. Handles parsing command-line arguments
3. Executes the function with the parsed arguments
4. Captures the return value as an exit code

argument() Function
~~~~~~~~~~~~~~~~

.. code-block:: python

    argument(
        help: str,                     # Help text for the argument
        short_name: str = None,        # Optional short flag name (e.g., 'v' for '--verbose')
        type: Type = str,              # Type conversion function
        choices: List[Any] = None,     # List of allowed values
        flag: bool = False,            # Whether the argument is a flag (True/False)
        required: bool = None,         # Whether the argument is required
        metavar: str = None,           # Name to use in help messages
        nargs: str = None,             # Number of arguments ('+', '*', '?', or int)
        action: str = None,            # Action to take (e.g., 'store_true')
    )

The ``argument()`` function creates an argument specification for use with the ``@tool`` decorator. Key features:

- **Automatic Type Handling**: Uses the type annotation for validation
- **Flag Support**: Boolean flags with ``flag=True``
- **Short Names**: Automatically creates short options with ``short_name``
- **Flexible Requirements**: Control which arguments are required

Command-Line Interface
---------------------

Jackknife's command-line interface provides several options for running tools and managing environments.

Basic Usage
~~~~~~~~~

.. code-block:: text

    jackknife <tool_name> [tool_arguments...]

Run a single tool with its specific arguments.

Tool Chaining
~~~~~~~~~~~

.. code-block:: text

    jackknife "tool1[arg1 arg2],tool2[arg3 arg4],tool3"

Run multiple tools in sequence, with tool-specific arguments.

Global Options
~~~~~~~~~~~

.. code-block:: text

    # Continue chain execution even if a tool fails
    jackknife --continue-on-error tool1,tool2,tool3

    # Disable environment sharing
    jackknife --no-share-environments <tool_name>

Environment Variables
~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Environment Variable
     - Description
   * - ``JACKKNIFE_ENVS_DIR``
     - Directory where virtual environments are stored (default: ``~/.jackknife_envs``)
   * - ``JACKKNIFE_SHARE_ENVIRONMENTS``
     - Control environment sharing (``true``/``false``, default: ``true``)

Environment Management API
------------------------

These functions are primarily for internal use but can be helpful to understand how Jackknife manages environments.

setup_environment()
~~~~~~~~~~~~~~~~

.. code-block:: python

    def setup_environment(tool_name: str, tool_script_path: Path) -> Path:
        """
        Ensures the virtual environment for the tool exists and dependencies are installed.
        Returns the path to the python executable in the venv.
        """

This function:

1. Checks if the environment already exists
2. If sharing is enabled, looks for a compatible environment
3. If a compatible environment is found, creates a symlink or directory junction
4. Otherwise, creates a new environment
5. Installs dependencies from the requirements file if it exists
6. Returns the path to the Python executable in the environment

find_compatible_environment()
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def find_compatible_environment(tool_name: str, requirements_path: Path) -> Optional[Path]:
        """
        Find an existing environment whose packages are a superset of the required packages.

        Args:
            tool_name: Name of the tool
            requirements_path: Path to the requirements file

        Returns:
            Path to a compatible environment if found, None otherwise
        """

This function:

1. Skips if environment sharing is disabled
2. Parses the tool's requirements
3. Checks each existing environment to see if it includes all required packages
4. Returns the path to a compatible environment if found

parse_requirements()
~~~~~~~~~~~~~~~~~

.. code-block:: python

    def parse_requirements(requirements_path: Path) -> Set[str]:
        """
        Parse a requirements.txt file and return a set of normalized package requirements.

        Returns:
            Set of package requirements in a normalized format
        """

This function:

1. Reads the requirements file
2. Normalizes package names by removing version specifiers and options
3. Returns a set of normalized package names for comparison

get_installed_packages()
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def get_installed_packages(python_executable: Path) -> Set[str]:
        """
        Get a set of packages installed in the environment.

        Args:
            python_executable: Path to the Python executable

        Returns:
            Set of installed package names (normalized)
        """

This function:

1. Uses ``uv pip list`` to get installed packages
2. Parses the output to extract package names
3. Returns a set of normalized package names

Error Handling
------------

Jackknife uses exit codes to indicate success or failure:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Exit Code
     - Description
   * - 0
     - Success
   * - 1
     - General error
   * - 130
     - Interrupted by user (Ctrl+C)

All errors are printed to stderr with appropriate formatting.