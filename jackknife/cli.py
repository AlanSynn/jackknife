import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, Dict, List, Optional, Set, Tuple

import typer

# Import Rich for better terminal output
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
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

# Whether to share environments between compatible tools (when one tool's requirements are a subset of another)
SHARE_ENVIRONMENTS = os.environ.get("JACKKNIFE_SHARE_ENVIRONMENTS", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Cache for package metadata
_requirements_cache: Dict[str, Set[str]] = {}
_environment_packages: Dict[str, Set[str]] = {}

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
    """Return the path to the Python executable in the virtual environment."""
    if os.name == "nt" or sys.platform == "win32":  # Windows
        return env_path / "Scripts" / "python.exe"
    return env_path / "bin" / "python"


def parse_requirements(requirements_path: Path) -> Set[str]:
    """
    Parse a requirements.txt file and return a set of normalized package requirements.

    This ignores version specifiers and options, focusing just on the package names.

    Args:
        requirements_path: Path to the requirements file

    Returns:
        Set of package names in normalized form
    """
    if requirements_path in _requirements_cache:
        return _requirements_cache[requirements_path]

    requirements = set()
    if not requirements_path.exists():
        _requirements_cache[requirements_path] = requirements
        return requirements

    try:
        with open(requirements_path) as f:
            for raw_line in f:
                processed_line = raw_line.strip()
                # Skip comments and empty lines
                if not processed_line or processed_line.startswith('#'):
                    continue

                # Handle line continuations
                while processed_line.endswith('\\'):
                    processed_line = processed_line[:-1].strip()
                    next_line = next(f, '').strip()
                    processed_line += ' ' + next_line

                # Extract the package name (ignore version specifiers and options)
                # This is a simplified approach - for complex cases, we might need more
                package = processed_line.split('=')[0].split('>')[0].split('<')[0].split('!')[0].split('~')[0].split('[')[0].strip()
                # Remove any extras
                if package:
                    requirements.add(package.lower())
    except OSError:
        # Handle file not found or reading errors
        pass

    _requirements_cache[requirements_path] = requirements
    return requirements


def get_installed_packages(python_executable: Path) -> Set[str]:
    """
    Get a set of packages installed in the environment.

    Args:
        python_executable: Path to the Python executable

    Returns:
        Set of installed package names (normalized)
    """
    env_key = str(python_executable)
    if env_key in _environment_packages:
        return _environment_packages[env_key]

    packages = set()

    uv_path = shutil.which("uv")
    if not uv_path:
        uv_not_found_message = "uv command not found"
        raise OSError(uv_not_found_message)

    try:
        # Use uv pip list to get installed packages which should be more reliable
        # than running pip through the interpreter (since uv ensures pip is available)
        result = subprocess.run( # noqa: S603
            [uv_path, "pip", "list", "--python", str(python_executable), "--no-input"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # Skip the first two lines (header + separator)
            lines = result.stdout.strip().split("\n")[2:]
            for line in lines:
                parts = line.split()
                if parts:
                    packages.add(parts[0].lower())
        _environment_packages[env_key] = packages
    except Exception as e:
        console.print(f"[warning]Warning:[/] Failed to get installed packages: {e}")
        return set()
    else:
        return packages


def find_compatible_environment(
    tool_name: str, requirements_path: Path
) -> Optional[Path]:
    """
    Find an existing environment whose packages are a superset of the required packages.

    Args:
        tool_name: Name of the tool
        requirements_path: Path to the requirements file

    Returns:
        Path to a compatible environment if found, None otherwise
    """
    if not SHARE_ENVIRONMENTS:
        return None

    # Check if tool has requirements
    tool_requirements = parse_requirements(requirements_path)
    if not tool_requirements:
        # Empty or non-existent requirements, any environment would work
        # But we'll just create a new one for simplicity and clarity
        return None

    # Look for existing environments
    try:
        for env_dir in ENVS_DIR.iterdir():
            if not env_dir.is_dir():
                continue

            # Skip the tool's own environment if it exists
            if env_dir.name == tool_name:
                continue

            # Check if this environment has the required packages
            python_executable = get_python_executable(env_dir)
            if not python_executable.exists():
                continue

            installed_packages = get_installed_packages(python_executable)

            # Check if all required packages are installed
            if tool_requirements.issubset(installed_packages):
                console.print(
                    f"[info]Package compatibility found:[/] Tool [highlight]{tool_name}[/] can use packages from [highlight]{env_dir.name}[/]"
                )
                return env_dir
    except Exception as e:
        console.print(
            f"[warning]Warning:[/] Error while looking for compatible environments: {e}"
        )

    return None


# --- Environment Setup Helpers ---

def _link_to_compatible_environment(env_path: Path, compatible_env: Path, tool_name: str) -> None:
    """Creates a symlink or junction to a compatible environment."""
    console.print(
        f"Using compatible environment from [highlight]'{compatible_env.name}'[/] for [highlight]'{tool_name}'[/]"
    )
    try:
        # Ensure the parent directory exists
        ENVS_DIR.mkdir(parents=True, exist_ok=True)
        cmd_path = "cmd"

        if os.name == "nt":  # Windows
            subprocess.run( # noqa: S603
                [cmd_path, "/c", "mklink", "/J", str(env_path), str(compatible_env)],
                check=True,
                capture_output=True,
            )
        else:  # Unix/Mac
            env_path.symlink_to(compatible_env, target_is_directory=True)
    except (OSError, subprocess.CalledProcessError) as e:
        console_stderr.print(
            f"[error]Error linking to compatible environment for '{tool_name}':[/] {e}"
        )
        # If linking fails, we should probably fall back to creating a new env,
        # but for simplicity now, we exit.
        # Alternatively, re-raise the error for setup_environment to handle.
        raise typer.Exit(code=1) from e

def _create_new_environment(env_path: Path, tool_name: str) -> None:
    """Creates a new virtual environment using uv."""
    console.print(
        f"Creating virtual environment for [highlight]'{tool_name}'[/] in {env_path}..."
    )
    ENVS_DIR.mkdir(parents=True, exist_ok=True)
    uv_path = shutil.which("uv")
    if not uv_path:
        console_stderr.print("[error]Error:[/] 'uv' command not found during environment creation.")
        raise typer.Exit(code=1)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Creating venv for {tool_name}...", total=None)
            result = subprocess.run( # noqa: S603
                [uv_path, "venv", str(env_path)], check=False, capture_output=True, text=True
            )
            result.check_returncode() # Raise CalledProcessError if failed
            progress.update(task, completed=True)
        console.print(f"[success]Virtual environment created for '{tool_name}'.[/]")
    except FileNotFoundError as e: # Should be caught by shutil.which earlier, but defensive
        console_stderr.print("[error]Error:[/] 'uv' command not found.")
        raise typer.Exit(code=1) from e
    except subprocess.CalledProcessError as e:
        console_stderr.print(f"[error]Error creating venv for '{tool_name}':[/]")
        console_stderr.print(f"Command: {' '.join(e.cmd)}")
        console_stderr.print(f"Output:\n{e.stderr or e.stdout}") # Show error output
        raise typer.Exit(code=1) from e

def _install_dependencies(python_executable: Path, requirements_path: Path, tool_name: str) -> None:
    """Installs dependencies from a requirements file into the environment."""
    if not requirements_path.exists():
        console.print(f"[info]No requirements file found for '{tool_name}'.[/]")
        return

    uv_path = shutil.which("uv")
    if not uv_path:
        console_stderr.print("[error]Error:[/] 'uv' command not found during dependency installation.")
        raise typer.Exit(code=1)

    console.print(
        f"Found requirements: [info]{requirements_path.name}[/]. Installing for '{tool_name}'..."
    )
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Installing dependencies for {tool_name}...", total=None)
            install_result = subprocess.run( # noqa: S603
                [
                    uv_path,
                    "pip",
                    "install",
                    "--python",
                    str(python_executable),
                    "-r",
                    str(requirements_path),
                    "--no-input", # Add no-input flag
                ],
                check=False, # Check manually below
                capture_output=True,
                text=True,
            )

            # --- Debug: Print uv output ---
            if install_result.stdout and install_result.returncode != 0:
                console.print("[dim]uv stdout:[/]")
                console.print(f"[dim]{install_result.stdout.strip()}[/]")
            if install_result.stderr:
                console.print("[dim yellow]uv stderr:[/]")
                console.print(f"[dim yellow]{install_result.stderr.strip()}[/]")
            # --- End Debug ---

            install_result.check_returncode() # Raise CalledProcessError if failed
            progress.update(task, completed=True)

        console.print(f"[success]Dependencies installed for '{tool_name}'.[/]")
        # Invalidate package cache for this environment
        _environment_packages.pop(str(python_executable), None)

    except FileNotFoundError as e:
        console_stderr.print("[error]Error:[/] 'uv' command not found.")
        raise typer.Exit(code=1) from e
    except subprocess.CalledProcessError as e:
        console_stderr.print(f"[error]Error installing dependencies for '{tool_name}':[/]")
        console_stderr.print(f"Command: {' '.join(e.cmd)}")
        # Show stderr first if available, otherwise stdout
        output = e.stderr or e.stdout
        console_stderr.print(f"Output:\n{output.strip()}")
        raise typer.Exit(code=1) from e

def setup_environment(tool_name: str, tool_script_path: Path) -> Path:
    """
    Ensures the virtual environment for the tool exists and dependencies are installed.
    Returns the path to the python executable in the venv.
    """
    env_path = ENVS_DIR / tool_name
    python_executable = get_python_executable(env_path)
    requirements_path = tool_script_path.with_suffix(".requirements.txt")

    # 1. Check if environment already exists and seems valid
    if python_executable.is_file(): # More robust check than just exists()
        # Optional: Add a check here to verify if required packages are installed?
        # For now, assume existing env is okay.
        return python_executable

    # 2. Try linking to a compatible environment if sharing is enabled
    compatible_env = find_compatible_environment(tool_name, requirements_path)
    if compatible_env:
        try:
            _link_to_compatible_environment(env_path, compatible_env, tool_name)
            # If linking succeeds, return the python executable from the *linked* path
            return get_python_executable(env_path)
        except Exception:
             # If linking fails, proceed to create a new environment
             console.print(f"[warning]Linking failed, creating dedicated environment for {tool_name}...[/]")

    # 3. Create a new environment
    try:
        _create_new_environment(env_path, tool_name)
    except typer.Exit:
         raise # Propagate exit
    except Exception as e:
         # Catch unexpected errors during creation
         console_stderr.print(f"[error]Unexpected error during environment creation: {e}[/]")
         raise typer.Exit(code=1) from e

    # 4. Install dependencies into the newly created environment
    try:
        _install_dependencies(python_executable, requirements_path, tool_name)
    except typer.Exit:
         raise # Propagate exit
    except Exception as e:
         # Catch unexpected errors during installation
         console_stderr.print(f"[error]Unexpected error during dependency installation: {e}[/]")
         # Consider removing the partially created env?
         shutil.rmtree(env_path, ignore_errors=True)
         raise typer.Exit(code=1) from e

    # 5. Return the path to the python executable in the new env
    if not python_executable.is_file():
         # Final sanity check
         console_stderr.print(f"[error]Environment setup finished, but Python executable not found at {python_executable}[/]")
         raise typer.Exit(code=1)

    return python_executable


def import_tool_module(tool_script_path: Path) -> Optional[ModuleType]:
    """
    Import a tool script as a module.

    This allows us to check if it's using our tool decorator and run it directly
    if it is, or fall back to subprocess execution if not.

    Args:
        tool_script_path: Path to the tool script

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
    except ModuleNotFoundError as e:
        # This is somewhat expected if the tool has dependencies not in the main env.
        # The fallback execution handles this case.
        console.print(f"[info]Tool has dependencies (like '{e.name}'), will run as subprocess.")
        return None
    except Exception as e:
        # Other import errors might indicate issues with the script itself.
        console.print(f"[warning]Warning:[/] Could not import tool as module: {e}")
        return None
    else:
        return module


def find_tool_function(module: ModuleType) -> Optional[Callable]:
    """
    Find the main tool function in a module.

    Args:
        module: The module to search for a tool function

    Returns:
        The tool function if found, None otherwise
    """
    # Look for a function marked with our tool decorator
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and hasattr(obj, "_is_jackknife_tool"):
            return obj

    # Fall back to looking for a function named main
    if hasattr(module, "main") and callable(module.main):
        return module.main

    return None


# --- Main Execution Logic ---


def parse_tool_chain(tool_chain_arg: str) -> List[Tuple[str, List[str]]]:
    """
    Parse a tool chain argument into individual tool names and their arguments.

    Formats supported:
    - Simple chaining: "tool1,tool2,tool3"
    - With arguments: "tool1[arg1 arg2],tool2[arg3 arg4]"

    Args:
        tool_chain_arg: A comma-separated list of tools, optionally with arguments

    Returns:
        List of tuples containing (tool_name, [tool_args])
    """
    tools = []

    # Split by comma, but handle cases where comma might be inside square brackets
    parts = []
    current = ""
    in_brackets = False

    for char in tool_chain_arg:
        if char == "[":
            in_brackets = True
            current += char
        elif char == "]":
            in_brackets = False
            current += char
        elif char == "," and not in_brackets:
            if current:
                parts.append(current)
                current = ""
        else:
            current += char

    if current:
        parts.append(current)

    # Process each part
    for part in parts:
        # Check if it has arguments
        if "[" in part and part.endswith("]"):
            name, args_str = part.split("[", 1)
            args_str = args_str[:-1]  # Remove closing bracket
            # Split args by space, respecting quotes
            try:
                args = subprocess.list2cmdline(args_str.split()).split()
            except Exception:
                # Fallback to simple splitting if parsing fails
                args = args_str.split()
            tools.append((name.strip(), args))
        else:
            tools.append((part.strip(), []))

    return tools


def run_single_tool(tool_name: str, tool_args: List[str], share_environments: bool = SHARE_ENVIRONMENTS) -> int:
    """
    Run a single tool with the given arguments.

    Args:
        tool_name: Name of the tool to run
        tool_args: Arguments to pass to the tool
        share_environments: Whether to share environments between compatible tools

    Returns:
        Exit code from the tool execution
    """
    # Set the global environment sharing setting
    global SHARE_ENVIRONMENTS # noqa: PLW0603
    SHARE_ENVIRONMENTS = share_environments

    # Locate the tool script
    tool_script_path = (TOOLS_DIR / f"{tool_name}.py").resolve()

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
        return 1

    # Setup the tool's environment (create if needed, install deps)
    console.print(
        Panel.fit(
            f"Preparing tool [highlight]{tool_name}[/]",
            title="JACKKNIFE",
            title_align="left",
            style="blue",
        )
    )

    try:
        venv_python_executable = setup_environment(tool_name, tool_script_path)
    except Exception as e:
        console_stderr.print(
            f"[error]Failed to prepare environment for {tool_name}:[/] {e}"
        )
        return 1

    # Execute the tool
    console.print(
        Panel.fit(
            f"Running tool [highlight]{tool_name}[/]",
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
                sys.argv = [str(tool_script_path)] + tool_args

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
                        f"Tool [highlight]{tool_name}[/] finished with exit code: [{status_style}]{exit_code}[/]",
                        title=f"JACKKNIFE: {status_text}",
                        title_align="left",
                        style="blue",
                    )
                )

                return exit_code

        # Otherwise, fall back to running it as a subprocess with the virtual environment
        command = [
            str(venv_python_executable),
            str(tool_script_path),
        ] + tool_args  # Pass remaining args

        # Run the tool script, inheriting stdout/stderr, and wait for completion
        result = subprocess.run(command, check=False) # noqa: S603

        status_style = "success" if result.returncode == 0 else "error"
        status_text = "SUCCESS" if result.returncode == 0 else "FAILED"

        console.print(
            Panel.fit(
                f"Tool [highlight]{tool_name}[/] finished with exit code: [{status_style}]{result.returncode}[/]",
                title=f"JACKKNIFE: {status_text}",
                title_align="left",
                style="blue",
            )
        )
    except KeyboardInterrupt:
        console_stderr.print(
            "\n[error]Operation interrupted by user.[/]"
        )
        return 130
    except Exception as e:
        console_stderr.print(
            f"[error]An error occurred while executing the tool:[/] {e}"
        )
        return 1
    finally:
        # Restore original sys.argv
        sys.argv = original_argv

    return result.returncode


def main() -> None:
    # 1. Ensure uv is available
    ensure_uv_installed()

    # 2. Parse arguments
    parser = argparse.ArgumentParser(
        description="Jackknife: Run tools in isolated environments.",
        usage="jackknife <tool_name | tool_chain> [tool_args...]",
        epilog=(
            "Tool chain examples:\n"
            "  jackknife tool1,tool2,tool3\n"
            '  jackknife "tool1[--arg1 val1],tool2[--arg2 val2]"\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "tool_arg",
        help="Name of the tool to run (e.g., giftomp4) or comma-separated chain (e.g., tool1,tool2)",
    )
    parser.add_argument(
        "tool_args",
        nargs=argparse.REMAINDER,
        help="Arguments to pass to the tool script (for single tool mode only)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue executing tools in a chain even if previous tools fail",
    )
    parser.add_argument(
        "--no-share-environments",
        action="store_false",
        dest="share_environments",
        help="Disable environment sharing between compatible tools",
    )

    args = parser.parse_args()

    # Override environment sharing if specified
    share_environments = SHARE_ENVIRONMENTS
    if hasattr(args, "share_environments"):
        share_environments = args.share_environments

    # Check if we're running a chain of tools
    if "," in args.tool_arg:
        # Parse the tool chain
        tool_chain = parse_tool_chain(args.tool_arg)

        if args.tool_args:
            console_stderr.print(
                "[warning]Warning:[/] Additional arguments provided but running in chain mode. "
                "Arguments are ignored. Use tool1[arg1 arg2],tool2[arg3 arg4] syntax instead."
            )

        # Execute each tool in sequence
        final_exit_code = 0
        console.print(
            Panel.fit(
                f"Starting execution of [bold]{len(tool_chain)}[/] tools in sequence",
                title="JACKKNIFE: CHAIN EXECUTION",
                title_align="left",
                style="blue",
            )
        )

        for i, (tool_name, tool_args) in enumerate(tool_chain):
            console.print(
                f"[bold cyan]({i + 1}/{len(tool_chain)})[/] Running tool: [bold]{tool_name}[/]"
            )

            # Pass share_environments to run_single_tool
            exit_code = run_single_tool(tool_name, tool_args, share_environments)

            if exit_code != 0:
                final_exit_code = exit_code
                if not args.continue_on_error:
                    console_stderr.print(
                        f"[error]Chain execution stopped due to error in tool {tool_name}[/]"
                    )
                    break

        # Show a summary of the chain execution
        status_style = "success" if final_exit_code == 0 else "error"
        status_text = "SUCCESS" if final_exit_code == 0 else "FAILED"

        console.print(
            Panel.fit(
                f"Chain execution of {len(tool_chain)} tools finished with overall exit code: [{status_style}]{final_exit_code}[/]",
                title=f"JACKKNIFE CHAIN: {status_text}",
                title_align="left",
                style="blue",
            )
        )

        sys.exit(final_exit_code)
    else:
        # Single tool execution
        exit_code = run_single_tool(args.tool_arg, args.tool_args, share_environments)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
