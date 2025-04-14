#!/usr/bin/env python3
"""
Example tool using the Jackknife decorator system.

This example shows how to create a tool using the @tool decorator,
which automatically handles argument parsing.
"""

from jackknife.tool_helpers import argument, tool


@tool
def example_decorated(
    input_file: argument(help_text="Path to the input file to process"),
    output_file: argument(help_text="Path to save the output", required=False) = None,
    verbose: argument(flag=True, help_text="Enable verbose output", short_name="v") = False,
    mode: argument(
        help_text="Processing mode", choices=["fast", "normal", "thorough"]
    ) = "normal",
    count: argument(help_text="Number of times to process", type=int) = 1,
) -> int:
    """
    Example tool that demonstrates the Jackknife decorator system.

    This tool doesn't do anything real, it just shows how to use the
    @tool decorator with argument specifications.
    """
    # Print information about the arguments
    print(f"Processing {input_file}")

    if output_file:
        print(f"Output will be saved to: {output_file}")
    else:
        print("No output file specified, results will be printed to stdout")

    if verbose:
        print("Verbose mode enabled")
        print(f"Using mode: {mode}")
        print(f"Processing count: {count}")

    # Simulate some processing
    print(f"Processing in {mode} mode...")
    for i in range(count):
        if verbose:
            print(f"Processing iteration {i + 1}/{count}")

    print("Processing complete!")
    return 0  # Return success


# The decorator handles the __main__ check internally,
# so no need for the if __name__ == "__main__" block
