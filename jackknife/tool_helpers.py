"""
Helper utilities for Jackknife tool development.

This module provides decorators and classes to simplify the development of tools by
handling argument parsing automatically.
"""

import argparse
import functools
import inspect
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, get_type_hints

# Type definitions
T = TypeVar("T")
ToolFunction = Callable[..., int]


@dataclass
class ArgumentSpec:
    """Specification for a command-line argument."""

    name: str
    help: str = ""
    type: Any = str
    default: Any = None
    choices: Optional[List[Any]] = None
    required: bool = False
    flag: bool = False  # If True, this is a boolean flag argument
    nargs: Optional[Union[int, str]] = None  # For arguments that take multiple values
    metavar: Optional[str] = None  # Display name for usage messages
    short_name: Optional[str] = None  # Short-form option (e.g., -v for --verbose)


# Global registry to store argument specs for annotated types
# This avoids issues with argparse trying to use the annotation class as a type
_ARGUMENT_REGISTRY = {}


def argument(
    help: str = "",
    type: Any = None,
    default: Any = None,
    choices: Optional[List[Any]] = None,
    required: bool = None,
    flag: bool = False,
    nargs: Optional[Union[int, str]] = None,
    metavar: Optional[str] = None,
    short_name: Optional[str] = None,
) -> Any:
    """
    Decorator to mark a function parameter as a command-line argument.

    This is used in combination with the @tool decorator to automatically generate
    argparse code for Jackknife tools.

    Example:
        @tool
        def my_tool(
            input_file: argument(help="Input file path"),
            verbose: argument(flag=True, help="Enable verbose output") = False
        ):
            # Implementation

    Args:
        help: Help text for the argument
        type: Type of the argument (e.g., int, float)
        default: Default value if argument is not provided
        choices: List of allowed values
        required: Whether the argument is required
        flag: If True, treats this as a boolean flag (--flag vs. --option value)
        nargs: Number of values to consume (int, '?', '*', '+')
        metavar: Display name for usage messages
        short_name: Short-form option (e.g., 'v' for --verbose/-v)

    Returns:
        The original type annotation with attached argument spec metadata
    """
    # Create an ArgumentSpec instance
    arg_spec = ArgumentSpec(
        name=None,  # Will be set by @tool based on parameter name
        help=help,
        type=type,
        default=default,
        choices=choices,
        required=required,
        flag=flag,
        nargs=nargs,
        metavar=metavar,
        short_name=short_name,
    )

    # Create a unique identifier for this argument spec
    spec_id = id(arg_spec)
    _ARGUMENT_REGISTRY[spec_id] = arg_spec

    # Return a dummy class with a reference to the spec ID
    class AnnotatedType:
        _arg_spec_id = spec_id

    return AnnotatedType


def _get_arg_spec(arg_type):
    """
    Get the argument spec for a type annotation.

    Args:
        arg_type: The type annotation to check

    Returns:
        ArgumentSpec or None if not found
    """
    # Check if the type has our _arg_spec_id attribute
    if hasattr(arg_type, "_arg_spec_id"):
        spec_id = arg_type._arg_spec_id
        return _ARGUMENT_REGISTRY.get(spec_id)
    return None


def tool(func: Optional[Callable] = None, *, description: Optional[str] = None):
    """
    Decorator to turn a function into a Jackknife tool with automatic argument parsing.

    Example:
        @tool
        def my_tool(
            input_file: argument(help="Input file path"),
            verbose: argument(flag=True, help="Enable verbose output") = False
        ):
            # Implementation

    Args:
        func: The tool function
        description: Optional description for the tool (defaults to function docstring)

    Returns:
        A wrapper function that handles argument parsing
    """

    def decorator(func: Callable) -> Callable:
        # Extract function signature and annotations
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        @functools.wraps(func)
        def wrapper():
            """Wrapper function that handles argument parsing."""
            # Create parser
            desc = description or func.__doc__ or f"Jackknife tool: {func.__name__}"
            parser = argparse.ArgumentParser(description=desc)

            # Track parameters for later function call
            param_names = []

            # Add arguments based on function parameters
            for param_name, param in sig.parameters.items():
                param_names.append(param_name)

                # Get the argument specification
                arg_type = type_hints.get(param_name, Any)
                arg_spec = _get_arg_spec(arg_type)

                if arg_spec is None:
                    # No special handling, create a simple argument
                    if param.default is inspect.Parameter.empty:
                        # Positional argument
                        parser.add_argument(param_name, help=f"{param_name} parameter")
                    else:
                        # Optional argument with default
                        parser.add_argument(
                            f"--{param_name.replace('_', '-')}",
                            dest=param_name,
                            default=param.default,
                            help=f"{param_name} parameter (default: {param.default})",
                        )
                else:
                    # We have a specialized argument specification
                    arg_spec.name = param_name

                    # Determine if this is a positional or optional argument
                    has_default = param.default is not inspect.Parameter.empty
                    is_positional = not has_default and not arg_spec.flag

                    # Set required based on default and explicit setting
                    if arg_spec.required is None:
                        arg_spec.required = not has_default and not is_positional

                    # Determine argument type if not explicitly specified
                    if arg_spec.type is None:
                        if arg_type is bool or (
                            hasattr(arg_type, "__origin__")
                            and arg_type.__origin__ is bool
                        ):
                            arg_spec.flag = True
                        else:
                            # Try to get the actual type, falling back to str
                            arg_spec.type = str

                    # Handle flags (boolean options)
                    if arg_spec.flag:
                        option_name = f"--{param_name.replace('_', '-')}"
                        short_option = (
                            f"-{arg_spec.short_name}" if arg_spec.short_name else None
                        )
                        opts = [opt for opt in [short_option, option_name] if opt]

                        if has_default and param.default:
                            # Default is True, create a negative flag (--no-flag)
                            neg_name = f"--no-{param_name.replace('_', '-')}"
                            parser.add_argument(
                                neg_name,
                                dest=param_name,
                                action="store_false",
                                help=arg_spec.help or f"Disable {param_name}",
                            )
                        else:
                            # Default is False, create a positive flag (--flag)
                            parser.add_argument(
                                *opts,
                                dest=param_name,
                                action="store_true",
                                help=arg_spec.help or f"Enable {param_name}",
                            )
                    elif is_positional:
                        # Positional argument
                        parser.add_argument(
                            param_name,
                            type=arg_spec.type,
                            nargs=arg_spec.nargs,
                            choices=arg_spec.choices,
                            metavar=arg_spec.metavar,
                            help=arg_spec.help,
                        )
                    else:
                        # Optional argument with value
                        option_name = f"--{param_name.replace('_', '-')}"
                        short_option = (
                            f"-{arg_spec.short_name}" if arg_spec.short_name else None
                        )
                        opts = [opt for opt in [short_option, option_name] if opt]

                        parser.add_argument(
                            *opts,
                            dest=param_name,
                            type=arg_spec.type,
                            default=param.default if has_default else arg_spec.default,
                            required=arg_spec.required,
                            choices=arg_spec.choices,
                            nargs=arg_spec.nargs,
                            metavar=arg_spec.metavar,
                            help=arg_spec.help,
                        )

            # Parse the arguments
            args = parser.parse_args()

            # Call the original function with parsed arguments
            kwargs = {name: getattr(args, name) for name in param_names}
            return func(**kwargs)

        # Mark this as a jackknife tool
        wrapper._is_jackknife_tool = True

        # If called directly, run the wrapped function
        if hasattr(func, "__module__") and func.__module__ == "__main__":
            return wrapper()

        return wrapper

    # Allow both @tool and @tool(...) syntax
    if func is None:
        return decorator
    return decorator(func)


def standalone_script(main_func: ToolFunction) -> None:
    """
    Helper function for tools that want to work both with Jackknife and as standalone scripts.

    Example:
        def main():
            # Implementation
            return 0

        if __name__ == "__main__":
            standalone_script(main)

    Args:
        main_func: Function to execute
    """
    result = main_func()
    sys.exit(result if isinstance(result, int) else 0)
