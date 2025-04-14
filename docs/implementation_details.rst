======================
Implementation Details
======================

.. contents:: Table of Contents
   :depth: 3
   :local:
   :backlinks: none

Overview
--------

This document provides technical details about Jackknife's implementation, including key components, algorithms, and design patterns. It's intended for developers who want to understand or contribute to the codebase.

Core Components
--------------

Command-Line Interface (CLI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI is implemented in ``jackknife/cli.py`` and serves as the main entry point for the application. Key functions include:

1. ``main()``: The primary entry point, handling argument parsing and dispatching to other functions.
2. ``run_single_tool()``: Executes a single tool with its arguments.
3. ``parse_tool_chain()``: Parses complex tool chains with arguments.
4. ``setup_environment()``: Creates or reuses isolated environments for tools.

The CLI uses argparse for command-line argument parsing with a custom usage format that supports both simple and complex command structures.

Environment Management
~~~~~~~~~~~~~~~~~~~~

Environment management is a critical part of Jackknife, implemented through several key functions:

1. ``setup_environment()``: Creates or prepares environments for tools.
2. ``find_compatible_environment()``: Identifies existing environments that can be reused.
3. ``get_python_executable()``: Returns the path to the Python interpreter in an environment.
4. ``parse_requirements()``: Extracts package names from requirements files.
5. ``get_installed_packages()``: Determines what packages are installed in an environment.

This system is designed to balance isolation with efficiency by intelligently reusing environments when possible.

Tool Decorator System
~~~~~~~~~~~~~~~~~~~

The decorator system in ``jackknife/tool_helpers.py`` provides a simplified way to create tools:

1. ``@tool``: The main decorator that transforms a function into a command-line tool.
2. ``argument()``: A factory function that creates argument specifications.
3. ``_generate_parser()``: Automatically creates an argument parser from function annotations.
4. ``_run_with_args()``: Executes the tool function with parsed arguments.

This system leverages Python's type annotations to create a declarative API for defining tool interfaces.

Implementation Details
--------------------

Environment Sharing Algorithm
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The environment sharing system works as follows:

1. When a tool is run, Jackknife checks if it has its own environment already.
2. If not, it parses the tool's requirements to get a set of normalized package names.
3. It then searches through existing environments to find ones where:
   a. All the tool's required packages are already installed
   b. The environment's Python version is compatible
4. If a compatible environment is found, Jackknife creates a symlink (Unix) or directory junction (Windows) instead of creating a new environment.
5. The tool then uses this shared environment for execution.

This approach saves disk space and setup time while maintaining the appearance of isolation.

Tool Execution Flow
~~~~~~~~~~~~~~~~~

The tool execution process follows these steps:

1. Parse the command-line arguments to determine the tool(s) to run.
2. For each tool:
   a. Locate the tool script in the tools directory
   b. Set up the environment (create, reuse, or link)
   c. Attempt to import the tool module directly
   d. If successful and using our decorator, execute in-process
   e. Otherwise, execute as a subprocess with the isolated Python interpreter
3. Report success or failure back to the user

This dual execution model allows both simple script-based tools and decorator-based tools to work with the same interface.

Command Chaining Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Command chaining is implemented through these steps:

1. The parser detects a comma in the tool argument, triggering chain mode.
2. ``parse_tool_chain()`` splits the argument into individual tool specifications.
3. For tool-specific arguments, it parses bracket-enclosed sections.
4. Each tool is executed in sequence.
5. By default, execution stops on first error, but ``--continue-on-error`` changes this behavior.

The parsing handles nested brackets and quoted arguments correctly to support complex command structures.

Rich Terminal Output
~~~~~~~~~~~~~~~~~~

Jackknife uses the ``rich`` library to provide enhanced terminal output:

1. Custom theme defined in ``THEME`` with consistent color mappings.
2. Progress spinners for long-running operations like environment creation.
3. Panels with styled headers for clear visual separation.
4. Error messages with appropriate styling for visibility.

This provides a modern, user-friendly interface that makes the status of operations clear.

Testing Approach
--------------

Unit Tests
~~~~~~~~~

Unit tests focus on testing individual functions in isolation:

1. ``TestEnsureUvInstalled``: Tests the uv availability check.
2. ``TestGetPythonExecutable``: Tests Python path construction.
3. ``TestImportToolModule``: Tests module importing functionality.
4. ``TestFindToolFunction``: Tests function discovery in modules.
5. ``TestSetupEnvironment``: Tests environment creation and reuse.

These tests use mocking extensively to isolate the tested functionality.

Integration Tests
~~~~~~~~~~~~~~~

Integration tests verify that components work together correctly:

1. ``TestJackknifeCLI``: Tests CLI argument parsing and command execution.
2. ``test_decorated_tool``: Tests the decorator system integration with the CLI.
3. ``test_chain_execution``: Tests the command chaining functionality.

These tests mock external commands but test internal component interactions.

Functional Tests
~~~~~~~~~~~~~~

Functional tests run the actual CLI command and verify results:

1. ``TestRealExecution.test_real_execution``: Runs a real tool with subprocess.
2. ``TestRealExecution.test_real_decorated_tool``: Tests a decorated tool end-to-end.

These tests are conditionally skipped if the environment doesn't support them.

Test Fixtures
~~~~~~~~~~~

Several fixtures support the tests:

1. ``mock_which``: Mocks the shutil.which function to simulate uv availability.
2. ``mock_cli_env``: Sets up a mock CLI environment for testing.
3. ``setup_test_environment``: Creates a realistic test environment with tools.
4. ``setup_decorated_tool``: Adds a decorated tool to the test environment.

These fixtures help create consistent test environments and reduce duplication.

Performance Considerations
------------------------

Caching
~~~~~~

Several caching mechanisms improve performance:

1. ``_requirements_cache``: Caches parsed requirements to avoid repeated file parsing.
2. ``_environment_packages``: Caches package lists for environments to reduce subprocess calls.

Environment Creation Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Environment creation is optimized in several ways:

1. Using ``uv`` for faster environment creation and package installation.
2. Reusing compatible environments through symlinks/junctions.
3. Only checking compatibility when environment sharing is enabled.

Subprocess Management
~~~~~~~~~~~~~~~~~~~

Subprocess execution is optimized:

1. Direct import and execution for decorated tools to avoid subprocess overhead.
2. Fallback to subprocess for traditional tools.
3. Proper handling of stdout/stderr to ensure real-time feedback.

Future Improvements
-----------------

Several areas have been identified for future performance improvements:

1. **Global Package Cache**: A shared package cache across environments.
2. **Startup Time Optimization**: Faster tool discovery and initialization.
3. **Parallel Execution**: Running multiple tools in parallel when in a chain.
4. **Enhanced Caching**: More sophisticated caching of environment information.
5. **Lazy Environment Creation**: Only create environments when needed.

These improvements would maintain the current isolation and sharing benefits while further improving performance.