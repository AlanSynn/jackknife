# Plan for `creating-tools.md` Guide

## Goal

Provide clear instructions and best practices for developers wanting to add new tool scripts to the Jackknife project.

## Structure

1.  **Introduction**
    *   Briefly explain what a Jackknife tool is (a Python script in `tools/`).
    *   Mention the benefits of using Jackknife (isolated environments).
2.  **Prerequisites**
    *   Basic Python knowledge.
    *   Understanding of command-line arguments.
    *   `uv` installed (mention it's handled by Jackknife runner itself, but good for local testing).
3.  **Core Concepts**
    *   **Location**: Tools live in the `tools/` directory.
    *   **Naming**: `my_tool.py` corresponds to `jackknife run my_tool`.
    *   **Dependencies**: Handled via `my_tool.requirements.txt` in the same directory. Jackknife/`uv` installs these into `~/.jackknife_envs/my_tool/`.
    *   **Execution**: Explain the two main ways Jackknife runs tools:
        *   Direct import (if using `@tool` decorator and no conflicting deps).
        *   Subprocess execution (standard scripts, or decorated scripts with deps). Explain why this fallback exists.
4.  **Creating a Tool: Two Approaches**
    *   **Approach 1: The `@tool` Decorator (Recommended)**
        *   Explain the benefits (automatic `argparse`, cleaner code).
        *   Introduce `jackknife.tool_helpers`: `@tool` and `@argument`.
        *   Show a clear example based on `tools/example_decorated.py`.
        *   Explain how `@argument` maps to `argparse` options (type, help, flag, short_name, required, default).
        *   Explain how the function signature maps to arguments.
        *   Mention the return value should be an exit code (int).
    *   **Approach 2: Traditional Script (Standard `argparse`)**
        *   Explain when this might be used (existing scripts, complex parsing needs).
        *   Show a clear example based on `tools/example_traditional.py`.
        *   Emphasize the need for `if __name__ == "__main__":` block and `sys.exit()`.
5.  **Handling Dependencies**
    *   Explain the `tool_name.requirements.txt` file.
    *   Recommend pinning versions for reproducibility (`==`).
    *   Mention that Jackknife uses `uv` to install these.
6.  **Best Practices & Tips**
    *   Use `rich` for nice console output (add `rich` to requirements).
    *   Handle `KeyboardInterrupt`.
    *   Return meaningful exit codes (0 for success, non-zero for failure).
    *   Consider using `typer` or other modern CLI libraries if not using the `@tool` decorator.
    *   How to test locally (activate the venv using `jackknife activate my_tool`).
7.  **Adding the Tool to the Project**
    *   Place `.py` and `.requirements.txt` in `tools/`.
    *   Update README or other docs if necessary.
    *   Add tests (brief mention, link to general testing guidelines).