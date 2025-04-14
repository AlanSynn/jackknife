=================
Design Philosophy
=================

.. contents:: Table of Contents
   :depth: 3
   :local:
   :backlinks: none

Core Principles
--------------

Jackknife follows several core design principles that drive the project's development:

Isolation by Default
~~~~~~~~~~~~~~~~~~~

Each tool in Jackknife operates within its own isolated virtual environment. This design choice ensures that:

1. **No Dependency Conflicts**: Tools with different or conflicting dependencies can coexist peacefully.
2. **Stability**: Changes to one tool's dependencies don't affect others.
3. **Reproducibility**: Each tool's environment can be recreated independently.
4. **Clean Testing**: When testing a new tool, you start with a clean slate.

This isolation prevents the "dependency hell" often encountered in Python projects where different tools may require incompatible versions of the same package.

Efficiency Through Sharing
~~~~~~~~~~~~~~~~~~~~~~~~~

While isolation is the default behavior, Jackknife intelligently shares environments when it makes sense:

1. **Subset Detection**: If a tool's dependencies are a subset of another tool's, Jackknife can reuse the more comprehensive environment.
2. **Symlinks**: Environment sharing is implemented using symlinks (Unix) or directory junctions (Windows) to avoid duplication.
3. **Optional Control**: Users can disable sharing when needed for complete isolation.

This approach provides the perfect balance between isolation for safety and sharing for efficiency.

Zero Global Impact
~~~~~~~~~~~~~~~~~

Jackknife is designed to minimize its impact on the global Python environment:

1. **No Global Dependencies**: Dependencies are installed only in tool-specific environments.
2. **Minimal Installation**: Jackknife itself has minimal dependencies.
3. **Contained Files**: All environments are stored in a specific directory that can easily be removed if needed.

This ensures that installing Jackknife and its tools won't interfere with other Python projects on your system.

Simplicity and Extensibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The project aims to balance simplicity for users with extensibility for developers:

1. **Simple Interface**: Running tools should be straightforward and intuitive.
2. **No Boilerplate**: Tools can be created with minimal code using the ``@tool`` decorator.
3. **Extensible Design**: The core architecture allows for adding new features without breaking existing functionality.
4. **Progressive Disclosure**: Basic features are simple, while advanced features are available when needed.

Architectural Decisions
----------------------

Environment Management with uv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Jackknife uses ``uv`` rather than ``virtualenv`` or ``venv`` for several key reasons:

1. **Performance**: ``uv`` is significantly faster than traditional Python package installers.
2. **Reliability**: Better handling of dependency resolution reduces environment creation failures.
3. **Modern Design**: As a newer tool, ``uv`` incorporates lessons learned from previous tools.
4. **Optimized Installation**: ``uv`` optimizes package installation for faster tool setup.

Decorator-Based Tool API
~~~~~~~~~~~~~~~~~~~~~~~

The ``@tool`` decorator system simplifies tool creation:

1. **Reduced Boilerplate**: Eliminates repetitive argparse code.
2. **Type-Based Arguments**: Leverages Python's type annotations for argument definition.
3. **Self-Documentation**: Tools automatically generate help text based on docstrings and argument definitions.
4. **Consistent Interface**: All decorator-based tools share a common interface pattern.

This approach makes creating new tools more accessible while maintaining flexibility for advanced use cases.

Command Chaining
~~~~~~~~~~~~~~~

The command chaining feature follows a specific design:

1. **Comma Separation**: Simple syntax using comma-separated tool names.
2. **Bracket Arguments**: Tool-specific arguments are enclosed in brackets.
3. **Sequential Execution**: Tools run in order, with configurable error handling.
4. **Shared State**: Files created by one tool can be used by subsequent tools.

This allows complex workflows to be created by combining simpler tools.

Development Practices
-------------------

Code Quality Standards
~~~~~~~~~~~~~~~~~~~~~

Jackknife maintains high code quality through:

1. **Ruff**: Single tool for linting and formatting that replaces multiple traditional tools.
2. **Pre-commit Hooks**: Automated quality checks before commits.
3. **Rich Type Annotations**: Comprehensive typing for better static analysis.
4. **Comprehensive Testing**: High test coverage with unit, integration, and functional tests.
5. **Clear Documentation**: All code includes docstrings and explanatory comments.

Testing Strategy
~~~~~~~~~~~~~~

The project uses a multi-level testing approach:

1. **Unit Tests**: For core functions and classes in isolation.
2. **Integration Tests**: For how components work together.
3. **Functional Tests**: End-to-end tests of actual CLI commands.
4. **Environment Tests**: Tests with different Python versions and operating systems.
5. **Coverage Reporting**: Ensures high code coverage and identifies untested areas.

Future Direction
---------------

Planned Enhancements
~~~~~~~~~~~~~~~~~~~

Several key enhancements are planned for Jackknife:

1. **Plugin System**: Allow discovery of tools from external packages.
2. **Caching**: Improve startup performance through intelligent caching.
3. **Shared Environment Option**: Allow tools to opt-in to a shared environment.
4. **Tool Updates**: Command to update tool dependencies.
5. **Dependency Locking**: Better control over exact dependency versions.

Design Evolution
~~~~~~~~~~~~~~

As Jackknife evolves, these core design principles will guide its development:

1. **Backward Compatibility**: New features should not break existing tools.
2. **Performance Optimization**: Continue to improve speed and efficiency.
3. **User Experience**: Enhance usability based on feedback.
4. **Extensibility**: Keep the architecture flexible for future needs.

Conclusion
---------

Jackknife's design philosophy represents a balance between isolation and efficiency, simplicity and power. By providing isolated environments while enabling intelligent sharing, it offers an elegant solution to Python tool management. The decorator-based API reduces the friction of creating new tools, while the command chaining feature allows for powerful workflows composed of simple components.

This philosophy will continue to guide the project's development, ensuring that Jackknife remains a reliable, efficient, and user-friendly tool for Python developers.