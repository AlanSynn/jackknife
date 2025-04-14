#!/usr/bin/env python3
"""
Example tool using traditional argparse.

This example shows how to create a tool without using the Jackknife decorator system,
for comparison with the decorated approach.
"""

import argparse
import sys


def main() -> int:
    """
    Example tool implementation.

    This function does the same thing as example_decorated.py but uses
    traditional argparse directly.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Example tool using traditional argparse."
    )
    parser.add_argument("input_file", help="Path to the input file to process")
    parser.add_argument("--output-file", "-o", help="Path to save the output")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "normal", "thorough"],
        default="normal",
        help="Processing mode",
    )
    parser.add_argument(
        "--count", "-c", type=int, default=1, help="Number of times to process"
    )

    args = parser.parse_args()

    # Print information about the arguments
    print(f"Processing {args.input_file}")

    if args.output_file:
        print(f"Output will be saved to: {args.output_file}")
    else:
        print("No output file specified, results will be printed to stdout")

    if args.verbose:
        print("Verbose mode enabled")
        print(f"Using mode: {args.mode}")
        print(f"Processing count: {args.count}")

    # Simulate some processing
    print(f"Processing in {args.mode} mode...")
    for i in range(args.count):
        if args.verbose:
            print(f"Processing iteration {i + 1}/{args.count}")

    print("Processing complete!")
    return 0  # Return success


if __name__ == "__main__":
    sys.exit(main())
