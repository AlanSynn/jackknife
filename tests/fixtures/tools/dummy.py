#!/usr/bin/env python3
"""
Dummy tool for testing the Jackknife project.
This tool just prints a message and exits.
"""

import argparse
import sys


def main():
    """Main entry point for the dummy tool."""
    parser = argparse.ArgumentParser(description="Dummy tool for testing Jackknife")
    parser.add_argument(
        "--message", default="Hello from dummy tool!", help="Message to print"
    )
    parser.add_argument("--exit-code", type=int, default=0, help="Exit code to return")

    args = parser.parse_args()

    # Print the message
    print(args.message)

    # Return the specified exit code
    return args.exit_code


if __name__ == "__main__":
    sys.exit(main())
