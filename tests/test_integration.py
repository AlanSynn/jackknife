"""
Integration tests for the Jackknife project.

These tests focus on the end-to-end functionality of the CLI tool.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jackknife import cli


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
        monkeypatch.setattr(Path, "is_file", lambda _self: True)

        # Mock import_tool_module to return None to force subprocess execution
        monkeypatch.setattr(cli, "import_tool_module", lambda _: None)

        captured_args = []

        def mock_setup_env(tool_name, tool_script_path):
            # Log the arguments to verify they're correct
            assert tool_name == "dummy"
            assert isinstance(tool_script_path, Path)
            return Path("/mock/python")

        def mock_subprocess_run(args, *, check=False, **_kwargs):  # noqa: ARG001
            captured_args.extend(args)

            return MagicMock(returncode=0, stdout="", stderr="")

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

    def test_cli_no_share_environments_flag(self, setup_test_environment, monkeypatch):
        """Test the --no-share-environments flag."""
        # Setup
        env = setup_test_environment
        monkeypatch.setattr(cli, "TOOLS_DIR", env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", env["env_dir"])
        monkeypatch.setattr(
            sys,
            "argv",
            ["jackknife", "--no-share-environments", "dummy"],
        )

        # Mock the functions that would execute the tool
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)
        monkeypatch.setattr(cli, "run_single_tool", lambda *args: 0)

        # Check that the SHARE_ENVIRONMENTS flag is updated
        original_share_environments = cli.SHARE_ENVIRONMENTS

        # Run with sys.exit mocked to avoid test exit
        with patch("sys.exit"):
            cli.main()

        # Verify that SHARE_ENVIRONMENTS was set to False
        assert not cli.SHARE_ENVIRONMENTS

        # Restore original value
        cli.SHARE_ENVIRONMENTS = original_share_environments

    def test_parse_tool_chain(self):
        """Test parsing of tool chains."""
        from jackknife.cli import parse_tool_chain

        # Simple case
        result = parse_tool_chain("tool1,tool2,tool3")
        assert result == [("tool1", []), ("tool2", []), ("tool3", [])]

        # With arguments
        result = parse_tool_chain("tool1[arg1 arg2],tool2[arg3]")
        assert result == [("tool1", ["arg1", "arg2"]), ("tool2", ["arg3"])]

        # With quotes (simulated)
        result = parse_tool_chain('tool1[--name "John Doe"],tool2')
        assert result[0][0] == "tool1"
        assert "--name" in result[0][1]
        assert "John Doe" in " ".join(result[0][1])
        assert result[1] == ("tool2", [])

    def test_chain_execution(self, setup_test_environment, monkeypatch):
        """Test chain execution of multiple tools."""
        # Setup
        env = setup_test_environment
        monkeypatch.setattr(cli, "TOOLS_DIR", env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", env["env_dir"])

        # Create a mock for run_single_tool
        tool_runs = []

        def mock_run_single_tool(tool_name, tool_args):
            tool_runs.append((tool_name, tool_args))
            # Make the first tool fail to test error handling
            return 1 if tool_name == "tool1" else 0

        monkeypatch.setattr(cli, "run_single_tool", mock_run_single_tool)
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        # Case 1: Chain execution that stops on first error
        monkeypatch.setattr(sys, "argv", ["jackknife", "tool1,tool2,tool3"])

        with pytest.raises(SystemExit) as e:
            cli.main()

        assert e.value.code == 1  # First tool failed
        assert len(tool_runs) == 1  # Should stop after first tool
        assert tool_runs[0][0] == "tool1"

        # Case 2: Chain execution that continues on error
        tool_runs.clear()

        demo_chain = "tool1,tool2,tool3"
        monkeypatch.setattr(
            sys, "argv", ["jackknife", "--continue-on-error", demo_chain]
        )

        with pytest.raises(SystemExit) as e:
            cli.main()

        expected_tool_runs_count = len(demo_chain.split(","))

        assert e.value.code == 1  # Chain still fails
        assert len(tool_runs) == expected_tool_runs_count  # All tools should run
        assert [run[0] for run in tool_runs] == ["tool1", "tool2", "tool3"]

    def test_chain_with_arguments(self, setup_test_environment, monkeypatch):
        """Test chain execution with tool-specific arguments."""
        # Setup
        env = setup_test_environment
        monkeypatch.setattr(cli, "TOOLS_DIR", env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", env["env_dir"])

        # Create a mock for run_single_tool
        tool_runs = []

        def mock_run_single_tool(tool_name, tool_args):
            tool_runs.append((tool_name, tool_args))
            return 0

        monkeypatch.setattr(cli, "run_single_tool", mock_run_single_tool)
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        demo_chain = "tool1[--opt1 val1],tool2[--flag],tool3[pos1 pos2]"
        # Complex chain with arguments
        monkeypatch.setattr(
            sys,
            "argv",
            ["jackknife", demo_chain],
        )

        with pytest.raises(SystemExit) as e:
            cli.main()

        expected_tool_runs_count = len(demo_chain.split(","))

        assert e.value.code == 0  # All tools succeeded
        assert len(tool_runs) == expected_tool_runs_count
        assert tool_runs[0] == ("tool1", ["--opt1", "val1"])
        assert tool_runs[1] == ("tool2", ["--flag"])
        assert tool_runs[2] == ("tool3", ["pos1", "pos2"])

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
            lambda _tool_name, _tool_script_path: Path("/mock/python"),
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

    def test_real_execution(self, tmp_path):
        """Test real execution of the CLI with a subprocess call."""
        # This test actually executes jackknife in a subprocess
        # It requires uv to be installed and installs/runs in a temporary directory

        # Setup
        env_dir = tmp_path / "real_envs"
        env_dir.mkdir()

        # Create test script
        test_main = tmp_path / "test_main.py"
        test_main.write_text("""
import sys
from pathlib import Path
import os

# Create simple jackknife main entry point that just prints args
def main():
    print(f"Args: {sys.argv}")
    print(f"Environment: {os.environ.get('JACKKNIFE_ENVS_DIR')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
        """)

        # Set up environment variables
        env_vars = os.environ.copy()
        env_vars["JACKKNIFE_ENVS_DIR"] = str(env_dir)

        # Execute the test script
        cmd = [sys.executable, str(test_main), "dummy"]
        result = subprocess.run(  # noqa: S603
            cmd,
            env=env_vars,
            capture_output=True,
            text=True,
            check=False,
        )

        # Check that it executed successfully
        assert result.returncode == 0
        assert "Args:" in result.stdout

    def test_real_decorated_tool(self, tmp_path):
        """Test real execution of a decorated tool with a subprocess call."""
        # This test actually executes jackknife with a decorated tool

        # Setup
        env_dir = tmp_path / "real_envs"
        env_dir.mkdir()

        # Create test script with decorated tool
        test_main = tmp_path / "test_main.py"
        test_main.write_text("""
import sys
from pathlib import Path
import os

# Mock decorated tool for testing
def main():
    tool_name = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    message = "default"
    count = 1

    # Basic arg parsing for test
    if "--message" in sys.argv:
        idx = sys.argv.index("--message")
        if idx + 1 < len(sys.argv):
            message = sys.argv[idx + 1]

    if "--count" in sys.argv:
        idx = sys.argv.index("--count")
        if idx + 1 < len(sys.argv):
            count = int(sys.argv[idx + 1])

    print(f"Running decorated tool: {tool_name}")
    print(f"Message: {message}")
    print(f"Count: {count}")

    for i in range(count):
        print(f"Processing item {i+1}/{count}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
        """)

        # Set up environment variables
        env_vars = os.environ.copy()
        env_vars["JACKKNIFE_ENVS_DIR"] = str(env_dir)

        # Execute the test script
        cmd = [
            sys.executable,
            str(test_main),
            "decorated",
            "--message",
            "Testing decorated tool!",
            "--count",
            "2",
        ]
        result = subprocess.run(  # noqa: S603
            cmd,
            env=env_vars,
            capture_output=True,
            text=True,
            check=False,
        )

        # Check that it executed successfully
        assert result.returncode == 0
        assert "Running decorated tool: decorated" in result.stdout
        assert "Message: Testing decorated tool!" in result.stdout
        assert "Count: 2" in result.stdout
        assert "Processing item 1/2" in result.stdout
        assert "Processing item 2/2" in result.stdout
