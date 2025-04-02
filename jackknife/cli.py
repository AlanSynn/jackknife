import argparse
import os
import sys
import subprocess
import shutil
import importlib.util
from pathlib import Path

# Import Rich for better terminal output
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.theme import Theme

# --- Configuration ---

# Custom theme for consistent styling
THEME = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "bold red",
        "highlight": "bold magenta",
        "title": "bold blue",
    }
)

# Create console instances for stdout and stderr
console = Console(theme=THEME)
console_stderr = Console(stderr=True, theme=THEME)

# Tools directory is at the root of the project
# Package is now directly at the root (not in src/)
PROJECT_ROOT = Path(__file__).parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"

# Directory to store the virtual environments for each tool
# Using a hidden directory in the user's home for persistence across projects
DEFAULT_ENVS_DIR = Path.home() / ".jackknife_envs"
# Allow overriding via environment variable
ENVS_DIR = Path(os.environ.get("JACKKNIFE_ENVS_DIR", DEFAULT_ENVS_DIR))

# --- Helper Functions ---


def ensure_uv_installed() -> None:
    """Checks if uv is installed and accessible."""
    if not shutil.which("uv"):
        console_stderr.print("[error]Error:[/] 'uv' command not found.")
        console_stderr.print(
            "[error]Jackknife requires 'uv' for environment management.[/]"
        )
        console_stderr.print("[info]Please install it first:[/]")
        console_stderr.print(
            "   Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )
        console_stderr.print(
            '   Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
        )
        console_stderr.print("   See: https://github.com/astral-sh/uv")
        sys.exit(1)


def get_python_executable(env_path: Path) -> Path:
    """Gets the path to the python executable within a virtual environment."""
    if sys.platform == "win32":
        return env_path / "Scripts" / "python.exe"
    else:
        return env_path / "bin" / "python"


def setup_environment(tool_name: str, tool_script_path: Path) -> Path:
    """
    Ensures the virtual environment for the tool exists and dependencies are installed.
    Returns the path to the python executable in the venv.
    """
    env_path = ENVS_DIR / tool_name
    python_executable = get_python_executable(env_path)
    requirements_path = tool_script_path.with_suffix(".requirements.txt")

    if not python_executable.exists():
        console.print(
            f"Creating virtual environment for [highlight]'{tool_name}'[/] in {env_path}..."
        )
        ENVS_DIR.mkdir(parents=True, exist_ok=True)  # Ensure base dir exists

        try:
            # Use uv to create the venv with a progress spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Creating environment...", total=None)
                subprocess.run(
                    ["uv", "venv", str(env_path)], check=True, capture_output=True
                )
                progress.update(task, completed=True)

            console.print("[success]Virtual environment created.[/]")

            # Check for and install requirements if they exist
            if requirements_path.exists():
                console.print(
                    f"Found requirements: [info]{requirements_path.name}[/]. Installing..."
                )

                # Use uv pip install with a progress spinner
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True,
                ) as progress:
                    task = progress.add_task("Installing dependencies...", total=None)
                    subprocess.run(
                        [
                            "uv",
                            "pip",
                            "install",
                            "--python",
                            str(python_executable),
                            "-r",
                            str(requirements_path),
                        ],
                        check=True,
                        capture_output=True,
                    )
                    progress.update(task, completed=True)

                console.print("[success]Dependencies installed.[/]")
            else:
                console.print("[info]No requirements file found.[/]")

        except FileNotFoundError:
            console_stderr.print(
                "[error]Error:[/] 'uv' command not found during environment creation."
            )
            console_stderr.print(
                "[info]Make sure 'uv' is installed and in your PATH.[/]"
            )
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            console_stderr.print(
                f"[error]Error setting up environment for '{tool_name}':[/]"
            )
            console_stderr.print(f"Command: {' '.join(e.cmd)}")
            console_stderr.print(f"Return Code: {e.returncode}")
            console_stderr.print(f"Output:\n{e.stdout.decode()}")
            console_stderr.print(f"Error Output:\n{e.stderr.decode()}")
            sys.exit(1)
        except Exception as e:
            console_stderr.print(
                f"[error]An unexpected error occurred during environment setup:[/] {e}"
            )
            sys.exit(1)

    return python_executable


def import_tool_module(tool_script_path: Path):
    """
    Import a tool script as a module.

    This allows us to check if it's using our tool decorator and run it directly
    if it is, or fall back to subprocess execution if not.

    Returns:
        The imported module object, or None if import failed
    """
    try:
        module_name = f"jackknife_tool_{tool_script_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, tool_script_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        # If we can't import the module, we'll fall back to running it as a subprocess
        console.print(f"[warning]Note:[/] Could not import tool as module: {e}")
        return None


def find_tool_function(module):
    """
    Find the main tool function in a module.

    Returns:
        The tool function if found, None otherwise
    """
    # Look for a function marked with our tool decorator
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and hasattr(obj, "_is_jackknife_tool"):
            return obj

    # If not found, look for a main function
    if hasattr(module, "main") and callable(module.main):
        return module.main

    return None


# --- Main Execution Logic ---


def main() -> None:
    # 1. Ensure uv is available
    ensure_uv_installed()

    # 2. Parse arguments
    parser = argparse.ArgumentParser(
        description="Jackknife: Run tools in isolated environments.",
        usage="jackknife <tool_name> [tool_args...]",
    )
    parser.add_argument("tool_name", help="Name of the tool to run (e.g., giftomp4)")
    parser.add_argument(
        "tool_args",
        nargs=argparse.REMAINDER,
        help="Arguments to pass to the tool script",
    )

    args = parser.parse_args()

    # 3. Locate the tool script
    tool_script_path = (TOOLS_DIR / f"{args.tool_name}.py").resolve()

    if not tool_script_path.is_file():
        console_stderr.print(
            f"[error]Error:[/] Tool script not found: {tool_script_path}"
        )
        available_tools = [
            f.stem for f in TOOLS_DIR.glob("*.py") if f.stem != "__init__"
        ]
        if available_tools:
            console_stderr.print(
                f"[info]Available tools:[/] {', '.join(available_tools)}"
            )
        sys.exit(1)

    # 4. Setup the tool's environment (create if needed, install deps)
    console.print(
        Panel.fit(
            f"Preparing tool [highlight]{args.tool_name}[/]",
            title="JACKKNIFE",
            title_align="left",
            style="blue",
        )
    )

    try:
        venv_python_executable = setup_environment(args.tool_name, tool_script_path)
    except Exception as e:
        console_stderr.print(
            f"[error]Failed to prepare environment for {args.tool_name}:[/] {e}"
        )
        sys.exit(1)

    # 5. Execute the tool
    console.print(
        Panel.fit(
            f"Running tool [highlight]{args.tool_name}[/]",
            title="JACKKNIFE",
            title_align="left",
            style="blue",
        )
    )

    # Save original sys.argv
    original_argv = sys.argv.copy()

    try:
        # First, try to import the module to see if it's using our tool decorator
        module = import_tool_module(tool_script_path)

        if module:
            tool_func = find_tool_function(module)

            if tool_func and hasattr(tool_func, "_is_jackknife_tool"):
                # It's using our decorator, so we can run it directly
                # Set sys.argv as the tool would expect
                sys.argv = [str(tool_script_path)] + args.tool_args

                try:
                    result = tool_func()
                    exit_code = result if isinstance(result, int) else 0
                except SystemExit as e:
                    # Capture sys.exit() calls from the tool
                    exit_code = e.code if isinstance(e.code, int) else 0

                status_style = "success" if exit_code == 0 else "error"
                status_text = "SUCCESS" if exit_code == 0 else "FAILED"

                console.print(
                    Panel.fit(
                        f"Tool [highlight]{args.tool_name}[/] finished with exit code: [{status_style}]{exit_code}[/]",
                        title=f"JACKKNIFE: {status_text}",
                        title_align="left",
                        style="blue",
                    )
                )

                sys.exit(exit_code)

        # Otherwise, fall back to running it as a subprocess with the virtual environment
        command = [
            str(venv_python_executable),
            str(tool_script_path),
        ] + args.tool_args  # Pass remaining args

        # Run the tool script, inheriting stdout/stderr, and wait for completion
        result = subprocess.run(command, check=False)

        status_style = "success" if result.returncode == 0 else "error"
        status_text = "SUCCESS" if result.returncode == 0 else "FAILED"

        console.print(
            Panel.fit(
                f"Tool [highlight]{args.tool_name}[/] finished with exit code: [{status_style}]{result.returncode}[/]",
                title=f"JACKKNIFE: {status_text}",
                title_align="left",
                style="blue",
            )
        )

        sys.exit(result.returncode)
    except KeyboardInterrupt:
        console_stderr.print(
            Panel.fit(
                "Execution interrupted by user",
                title="JACKKNIFE: CANCELLED",
                title_align="left",
                style="yellow",
            )
        )
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        console_stderr.print(
            Panel.fit(
                f"Error running tool [highlight]{args.tool_name}[/]: {e}",
                title="JACKKNIFE: ERROR",
                title_align="left",
                style="red",
            )
        )
        sys.exit(1)
    finally:
        # Restore original sys.argv
        sys.argv = original_argv


if __name__ == "__main__":
    main()
