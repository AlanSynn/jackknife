"""
Integration tests for the Jackknife project.

These tests focus on the end-to-end functionality of the CLI tool.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from jackknife import cli
from jackknife.tool_helpers import tool, argument


@pytest.fixture
def setup_test_environment(temp_dir, mock_tools_dir):
    """Set up a test environment with real tools."""
    # Copy the dummy tool to the temp tools directory
    fixtures_dir = Path(__file__).parent / "fixtures" / "tools"
    dummy_py = fixtures_dir / "dummy.py"
    dummy_req = fixtures_dir / "dummy.requirements.txt"

    target_dummy_py = mock_tools_dir / "dummy.py"
    target_dummy_req = mock_tools_dir / "dummy.requirements.txt"

    shutil.copy(dummy_py, target_dummy_py)
    shutil.copy(dummy_req, target_dummy_req)

    # Make the tool executable
    target_dummy_py.chmod(0o755)

    # Set up environment variables
    env_dir = temp_dir / "jackknife_envs"
    env_dir.mkdir()

    # Return configuration
    return {
        "tools_dir": mock_tools_dir,
        "env_dir": env_dir,
        "dummy_script": target_dummy_py,
    }


@pytest.fixture
def setup_decorated_tool(setup_test_environment):
    """Set up a test environment with a decorated tool."""
    env = setup_test_environment

    # Create a decorated tool
    decorated_tool_path = env["tools_dir"] / "decorated.py"
    decorated_tool_content = """
from jackknife.tool_helpers import tool, argument

@tool
def decorated(
    message: argument(help="Message to display") = "Hello from decorated tool!",
    verbose: argument(flag=True, help="Enable verbose output") = False
):
    \"\"\"A test tool using the jackknife decorator.\"\"\"
    if verbose:
        print(f"Verbose mode enabled")
    print(message)
    return 0
"""
    decorated_tool_path.write_text(decorated_tool_content)

    # Make it executable
    decorated_tool_path.chmod(0o755)

    # Create an empty requirements file
    requirements_path = env["tools_dir"] / "decorated.requirements.txt"
    requirements_path.write_text("# No requirements")

    # Return the updated configuration
    return {
        **env,
        "decorated_script": decorated_tool_path,
    }


class TestJackknifeCLI:
    """Integration tests for the jackknife CLI."""

    def test_tool_list(self, setup_test_environment, monkeypatch, capsys):
        """Test listing available tools when a tool is not found."""
        # Setup
        env = setup_test_environment
        monkeypatch.setattr(cli, "TOOLS_DIR", env["tools_dir"])
        monkeypatch.setattr(sys, "argv", ["jackknife", "nonexistent"])

        # Mock ensure_uv_installed to avoid checking for uv
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        # We need to patch is_file to return False for nonexistent.py
        original_is_file = Path.is_file

        def mock_is_file(self):
            if self.name == "nonexistent.py":
                return False
            return original_is_file(self)

        monkeypatch.setattr(Path, "is_file", mock_is_file)

        # Run with sys.exit mocked to avoid test exit
        with patch("sys.exit"):
            cli.main()

        # Check output
        captured = capsys.readouterr()
        assert "Available tools: dummy" in captured.err

    def test_cli_argument_parsing(self, setup_test_environment, monkeypatch):
        """Test argument parsing."""
        # Setup
        env = setup_test_environment
        monkeypatch.setattr(cli, "TOOLS_DIR", env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", env["env_dir"])
        monkeypatch.setattr(
            sys,
            "argv",
            ["jackknife", "dummy", "--message", "test message", "--exit-code", "42"],
        )

        # Mock the functions that would execute the tool
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        # Ensure is_file returns True
        monkeypatch.setattr(Path, "is_file", lambda self: True)

        # Mock import_tool_module to return None to force subprocess execution
        monkeypatch.setattr(cli, "import_tool_module", lambda _: None)

        # This is a bit of a hack to capture the args that would be passed to subprocess.run
        captured_args = []

        def mock_setup_env(tool_name, tool_script_path):
            return Path("/mock/python")

        def mock_subprocess_run(args, **kwargs):
            captured_args.extend(args)

            # Create a mock process result
            class MockProcess:
                returncode = 0

            return MockProcess()

        monkeypatch.setattr(cli, "setup_environment", mock_setup_env)
        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        # Run with sys.exit mocked to avoid test exit
        with patch("sys.exit"):
            cli.main()

        # Check that arguments were passed correctly
        assert captured_args[0] == "/mock/python"
        assert (
            "dummy.py" in captured_args[1]
        )  # Just check that the filename is included
        assert captured_args[2:] == ["--message", "test message", "--exit-code", "42"]

    def test_decorated_tool(self, setup_decorated_tool, monkeypatch, capsys):
        """Test running a tool that uses the @tool decorator."""
        # Setup
        env = setup_decorated_tool
        monkeypatch.setattr(cli, "TOOLS_DIR", env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", env["env_dir"])
        monkeypatch.setattr(
            sys,
            "argv",
            ["jackknife", "decorated", "--message", "Test decorated tool", "--verbose"],
        )

        # Mock ensure_uv_installed to avoid checking for uv
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        # Make sure setup_environment returns a valid path but doesn't actually create anything
        monkeypatch.setattr(
            cli,
            "setup_environment",
            lambda tool_name, tool_script_path: Path("/mock/python"),
        )

        # Run with sys.exit mocked to avoid test exit
        with patch("sys.exit"):
            cli.main()

        # Check output - in this case the tool should execute directly, not via subprocess
        captured = capsys.readouterr()
        assert "Verbose mode enabled" in captured.out
        assert "Test decorated tool" in captured.out


@pytest.mark.skipif(not shutil.which("uv"), reason="uv executable not found")
class TestRealExecution:
    """Tests that actually execute the CLI with real subprocess calls.

    These tests are skipped if uv is not installed.
    """

    def test_real_execution(self, setup_test_environment, monkeypatch, tmp_path):
        """Test real execution of the CLI with a subprocess call."""
        # This test actually executes jackknife in a subprocess
        # It requires uv to be installed and installs/runs in a temporary directory

        # Setup
        env = setup_test_environment
        env_dir = tmp_path / "real_envs"
        env_dir.mkdir()

        # Create a real dummy.py file in the temp tools dir
        tools_dir = tmp_path / "real_tools"
        tools_dir.mkdir()
        dummy_py = tools_dir / "dummy.py"
        dummy_py.write_text("""
#!/usr/bin/env python3
import sys
print("Real dummy tool was executed!")
sys.exit(0)
        """)
        dummy_py.chmod(0o755)

        # Create an empty requirements file
        dummy_req = tools_dir / "dummy.requirements.txt"
        dummy_req.write_text("# Empty requirements")

        # Set the environment variables for the subprocess
        env_vars = os.environ.copy()
        env_vars["JACKKNIFE_ENVS_DIR"] = str(env_dir)

        # Create a mock main.py that uses our CLI module with the test tools dir
        test_main = tmp_path / "test_main.py"
        test_main.write_text(f"""
import sys
from pathlib import Path
from jackknife import cli

# Override the tools directory to use our test directory
cli.TOOLS_DIR = Path("{tools_dir}")

# Run the CLI
if __name__ == "__main__":
    sys.exit(cli.main())
        """)

        # Execute the test script
        result = subprocess.run(
            [sys.executable, str(test_main), "dummy"],
            env=env_vars,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        # Check that it executed successfully
        assert "Real dummy tool was executed!" in result.stdout
        assert result.returncode == 0

    def test_real_decorated_tool(self, setup_test_environment, monkeypatch, tmp_path):
        """Test real execution of a decorated tool with a subprocess call."""
        # This test actually executes jackknife with a decorated tool

        # Setup
        env = setup_test_environment
        env_dir = tmp_path / "real_envs"
        env_dir.mkdir()

        # Create a real decorated tool in the temp tools dir
        tools_dir = tmp_path / "real_tools"
        tools_dir.mkdir()

        # First, copy the tool_helpers.py module to make it available
        # We need to create the jackknife package structure
        jackknife_dir = tmp_path / "jackknife"
        jackknife_dir.mkdir()

        # Create an __init__.py
        init_py = jackknife_dir / "__init__.py"
        init_py.write_text("# Jackknife package")

        # Copy the tool_helpers module content
        tool_helpers_py = jackknife_dir / "tool_helpers.py"

        # Get the content from the actual module
        import inspect
        import jackknife.tool_helpers

        tool_helpers_content = inspect.getsource(jackknife.tool_helpers)
        tool_helpers_py.write_text(tool_helpers_content)

        # Create a decorated tool
        decorated_py = tools_dir / "decorated.py"
        decorated_content = """
#!/usr/bin/env python3
import sys
sys.path.insert(0, 'PATH_TO_REPLACE')  # Make jackknife available

from jackknife.tool_helpers import tool, argument

@tool
def decorated(
    message: argument(help="Message to display") = "Hello, World!",
    count: argument(help="Number of times to repeat", type=int) = 1
):
    \"\"\"A test tool using the jackknife decorator.\"\"\"
    for i in range(count):
        print(f"{i+1}: {message}")
    return 0

# Tool will be automatically run if this is the main module
"""
        decorated_py.write_text(
            decorated_content.replace("PATH_TO_REPLACE", str(tmp_path))
        )

        decorated_py.chmod(0o755)

        # Create an empty requirements file
        decorated_req = tools_dir / "decorated.requirements.txt"
        decorated_req.write_text("# Empty requirements")

        # Set the environment variables for the subprocess
        env_vars = os.environ.copy()
        env_vars["JACKKNIFE_ENVS_DIR"] = str(env_dir)
        env_vars["PYTHONPATH"] = str(tmp_path)

        # Create a mock main.py that uses our CLI module with the test tools dir
        test_main = tmp_path / "test_main.py"
        test_main.write_text(f"""
import sys
from pathlib import Path
from jackknife import cli

# Override the tools directory to use our test directory
cli.TOOLS_DIR = Path("{tools_dir}")

# Run the CLI
if __name__ == "__main__":
    sys.exit(cli.main())
        """)

        # Execute the test script
        result = subprocess.run(
            [
                sys.executable,
                str(test_main),
                "decorated",
                "--message",
                "Testing decorated tool!",
                "--count",
                "2",
            ],
            env=env_vars,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        # Check that it executed successfully
        assert "1: Testing decorated tool!" in result.stdout
        assert "2: Testing decorated tool!" in result.stdout
        assert result.returncode == 0
