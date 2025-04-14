"""
Unit tests for the Jackknife CLI module.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jackknife import cli


@pytest.fixture
def mock_which(monkeypatch):
    """Mocks shutil.which to return a path for 'uv'."""

    def mock_return(command):
        if command == "uv":
            return "/usr/bin/uv"
        return None

    monkeypatch.setattr(shutil, "which", mock_return)


class TestEnsureUvInstalled:
    """Tests for the ensure_uv_installed function."""

    def test_uv_installed(self, mock_which, capsys):
        """Test that function passes when uv is installed."""
        # The _mock_which fixture patches shutil.which implicitly.
        with patch("sys.exit") as mock_exit:
            cli.ensure_uv_installed()
            mock_exit.assert_not_called()
        # If we reached here, no exception was raised
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_uv_not_installed(self, monkeypatch, capsys):
        """Test that function exits when uv is not installed."""
        # Mock shutil.which to return None for 'uv'
        monkeypatch.setattr(shutil, "which", lambda _: None)

        # Mock sys.exit to avoid exiting the test
        with patch("sys.exit") as mock_exit:
            cli.ensure_uv_installed()
            mock_exit.assert_called_once_with(1)

        # Check that error message was printed
        captured = capsys.readouterr()
        assert "Error: 'uv' command not found" in captured.err


class TestGetPythonExecutable:
    """Tests for the get_python_executable function."""

    def test_windows_path(self, monkeypatch):
        """Test Windows path construction."""
        monkeypatch.setattr(sys, "platform", "win32")
        env_path = Path("/test/env")
        result = cli.get_python_executable(env_path)
        assert result == Path("/test/env/Scripts/python.exe")

    def test_unix_path(self, monkeypatch):
        """Test Unix path construction."""
        monkeypatch.setattr(sys, "platform", "linux")
        env_path = Path("/test/env")
        result = cli.get_python_executable(env_path)
        assert result == Path("/test/env/bin/python")


class TestImportToolModule:
    """Tests for the import_tool_module function."""

    def test_successful_import(self, tmp_path):
        """Test successful module import."""
        # Create a mock tool script
        tool_script = tmp_path / "mock_tool.py"
        tool_script.write_text("""
def main():
    return 0
        """)

        # Import the module
        module = cli.import_tool_module(tool_script)

        # Check that the module was imported and has the expected function
        assert module is not None
        assert hasattr(module, "main")
        assert callable(module.main)

    def test_failed_import(self, tmp_path):
        """Test handling of failed imports."""
        # Create an invalid Python file
        bad_script = tmp_path / "bad_tool.py"
        bad_script.write_text("This is not valid Python code")

        # Try to import it
        module = cli.import_tool_module(bad_script)

        # Should return None for failed imports
        assert module is None


class TestFindToolFunction:
    """Tests for the find_tool_function function."""

    def test_find_decorated_tool(self):
        """Test finding a function with the jackknife tool decorator."""

        # Create a mock module with a decorated function
        class MockModule:
            pass

        module = MockModule()

        def decorated_func():
            pass

        decorated_func._is_jackknife_tool = True
        module.tool_func = decorated_func

        # Find the tool function
        func = cli.find_tool_function(module)

        # Should find the decorated function
        assert func is decorated_func

    def test_find_main_function(self):
        """Test finding a main function when no decorated function exists."""

        # Create a mock module with a main function
        class MockModule:
            pass

        module = MockModule()

        def main_func():
            pass

        module.main = main_func

        # Find the tool function
        func = cli.find_tool_function(module)

        # Should find the main function
        assert func is main_func

    def test_no_function_found(self):
        """Test behavior when no appropriate function is found."""

        # Create a mock module without appropriate functions
        class MockModule:
            pass

        module = MockModule()

        # Find the tool function
        func = cli.find_tool_function(module)

        # Should return None
        assert func is None


class TestSetupEnvironment:
    """Tests for the setup_environment function."""

    def test_existing_environment(self, mock_cli_env, monkeypatch):
        """Test that existing environments are reused."""
        # Setup
        tool_name = "dummy"
        tool_script_path = mock_cli_env["tools_dir"] / "dummy.py"
        expected_python_path = mock_cli_env["python_path"]

        # Mock PROJECT_ROOT and TOOLS_DIR
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", mock_cli_env["env_dir"])

        # Execute
        result = cli.setup_environment(tool_name, tool_script_path)

        # Verify
        assert result == expected_python_path

    @pytest.mark.parametrize("requirements_exists", [True, False])
    def test_new_environment_creation(
        self, mock_cli_env, monkeypatch, requirements_exists
    ):
        """Test creation of a new environment."""
        # Setup
        tool_name = "newtool"
        tool_script_path = mock_cli_env["tools_dir"] / "newtool.py"
        requirements_path = mock_cli_env["tools_dir"] / "newtool.requirements.txt"

        # Create the tool script
        tool_script_path.touch()

        # Create requirements file if needed for the test
        if requirements_exists:
            requirements_path.touch()

        # Mock subprocess.run to avoid actual command execution
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock path.exists for the executable to simulate non-existing env first
        original_exists = Path.exists

        def mock_exists(self):
            if str(self).endswith("bin/python"):
                # Return False the first time, True thereafter
                if not hasattr(mock_exists, "called"):
                    mock_exists.called = True
                    return False
                return True
            return original_exists(self)

        monkeypatch.setattr(Path, "exists", mock_exists)

        # Mock PROJECT_ROOT and TOOLS_DIR
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", mock_cli_env["env_dir"])

        # Execute
        cli.setup_environment(tool_name, tool_script_path)

        expected_call_count = 2 if requirements_exists else 1

        # Verify
        assert mock_run.call_count == expected_call_count

        # Verify the first call is to uv venv
        first_call_args = mock_run.call_args_list[0][0][0]
        uv_path = shutil.which("uv")
        assert first_call_args[0] == uv_path
        assert first_call_args[1] == "venv"

        # Verify the second call is to uv pip install if applicable
        if requirements_exists:
            second_call_args = mock_run.call_args_list[1][0][0]
            assert second_call_args[0] == uv_path
            assert second_call_args[1] == "pip"
            assert second_call_args[2] == "install"
            assert "-r" in second_call_args

    def test_environment_creation_error(self, mock_cli_env, monkeypatch):
        """Test error handling during environment creation."""
        # Setup
        tool_name = "errortool"
        tool_script_path = mock_cli_env["tools_dir"] / "errortool.py"

        # Create the tool script
        tool_script_path.touch()

        # Mock find_compatible_environment to return None to avoid requirements parsing
        monkeypatch.setattr(cli, "find_compatible_environment", lambda *_args: None)

        # Mock subprocess.run to raise CalledProcessError
        error = subprocess.CalledProcessError(
            1, ["uv", "venv"], output=b"", stderr=b"Error"
        )
        mock_run = MagicMock(side_effect=error)
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock path.exists for the executable to simulate non-existing env
        monkeypatch.setattr(
            Path, "exists", lambda self: not str(self).endswith("bin/python")
        )

        # Mock PROJECT_ROOT and TOOLS_DIR
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", mock_cli_env["env_dir"])

        # Mock sys.exit to avoid exiting the test
        with patch("sys.exit") as mock_exit:
            cli.setup_environment(tool_name, tool_script_path)
            mock_exit.assert_called_once_with(1)

    @pytest.mark.parametrize("share_environments", [True, False])
    def test_environment_sharing(self, mock_cli_env, monkeypatch, share_environments):
        """Test environment sharing between compatible tools."""
        # Setup
        # First tool with dependencies
        tool1_name = "tool1"
        tool1_script_path = mock_cli_env["tools_dir"] / "tool1.py"
        tool1_requirements = mock_cli_env["tools_dir"] / "tool1.requirements.txt"

        # Second tool with a subset of the dependencies
        tool2_name = "tool2"
        tool2_script_path = mock_cli_env["tools_dir"] / "tool2.py"
        tool2_requirements = mock_cli_env["tools_dir"] / "tool2.requirements.txt"

        # Create the tool scripts and requirements
        tool1_script_path.touch()
        tool1_requirements.write_text("rich>=13.0.0\nrequests>=2.28.0")

        tool2_script_path.touch()
        tool2_requirements.write_text("rich>=13.0.0")

        # Set up for environment sharing test
        env_path_tool1 = mock_cli_env["env_dir"] / tool1_name

        # Mock the find_compatible_environment function
        def mock_find_compatible(tool_name, _req_path):
            if share_environments and tool_name == "tool2":
                return env_path_tool1
            return None

        # Mock dependencies for environment sharing
        monkeypatch.setattr(cli, "SHARE_ENVIRONMENTS", share_environments)
        monkeypatch.setattr(cli, "find_compatible_environment", mock_find_compatible)

        # Mock the exists function to control environment creation
        def mock_exists(self):
            # Tool1 environment exists after first check
            if tool1_name in str(self) and hasattr(mock_exists, "tool1_created"):
                return True
            # Create a flag for tool1 env after we "create" it
            if tool1_name in str(self) and "python" in str(self):
                mock_exists.tool1_created = True
                return False
            # Tool2 environment doesn't exist initially
            return False

        # Mock PROJECT_ROOT and TOOLS_DIR
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", mock_cli_env["env_dir"])
        monkeypatch.setattr(Path, "exists", mock_exists)

        # Create tool1 environment first
        cli.setup_environment(tool1_name, tool1_script_path)

        # Capture calls to symlink_to
        symlink_calls = []

        def track_symlink_to(self, target, _target_is_directory=False):
            symlink_calls.append((str(self), str(target)))

        monkeypatch.setattr(Path, "symlink_to", track_symlink_to)

        # Mock subprocess.run for directory junction on Windows
        def mock_subprocess_run(args, **_kwargs):
            if args[0] == "cmd" and "/J" in args:
                # Windows directory junction
                source = args[4]
                target = args[5]
                symlink_calls.append((source, target))
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        # Now create tool2 environment
        cli.setup_environment(tool2_name, tool2_script_path)

        # Check if environment sharing worked as expected
        if share_environments:
            # Should have created a symlink or directory junction
            assert len(symlink_calls) == 1
            assert tool2_name in symlink_calls[0][0]
            assert tool1_name in symlink_calls[0][1]
        else:
            # Should not have created a symlink
            assert len(symlink_calls) == 0


class TestMain:
    """Tests for the main CLI function."""

    def test_tool_not_found(self, mock_cli_env, monkeypatch, capsys):
        """Test error handling when tool is not found."""
        # Setup
        monkeypatch.setattr(sys, "argv", ["jackknife", "nonexistenttool"])
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])

        # Mock ensure_uv_installed to do nothing
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        # We need to patch tool_script_path.is_file() to return False to trigger the error
        original_is_file = Path.is_file

        def mock_is_file(self):
            if self.name == "nonexistenttool.py":
                return False
            return original_is_file(self)

        monkeypatch.setattr(Path, "is_file", mock_is_file)

        # Mock sys.exit to avoid exiting the test
        with patch("sys.exit") as mock_exit:
            cli.main()
            # Only check that sys.exit was called with error code
            assert mock_exit.call_count >= 1
            assert mock_exit.call_args_list[0][0][0] != 0  # Ensure it's an error exit

        # Check that error message was printed
        captured = capsys.readouterr()
        assert "Tool script not found" in captured.err

    def test_successful_tool_execution(self, mock_cli_env, monkeypatch):
        """Test successful tool execution path."""
        # Setup
        monkeypatch.setattr(sys, "argv", ["jackknife", "dummy", "--message", "test"])
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", mock_cli_env["env_dir"])

        # Create the dummy tool
        dummy_script = mock_cli_env["tools_dir"] / "dummy.py"
        dummy_script.touch(mode=0o755)

        # Make sure the is_file() check returns True
        original_is_file = Path.is_file

        def mock_is_file(self):
            if self.name == "dummy.py":
                return True
            return original_is_file(self)

        monkeypatch.setattr(Path, "is_file", mock_is_file)

        # Mock functions to avoid actual execution
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)
        monkeypatch.setattr(
            cli,
            "setup_environment",
            lambda tool_name, tool_script_path: mock_cli_env["python_path"],
        )

        # Mock import_tool_module to return None to force subprocess execution
        monkeypatch.setattr(cli, "import_tool_module", lambda _: None)

        # Mock subprocess.run to simulate successful execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run = MagicMock(return_value=mock_process)
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock sys.exit to avoid exiting the test
        with patch("sys.exit") as mock_exit:
            cli.main()
            mock_exit.assert_called_once_with(0)

        # Verify subprocess.run was called with correct args
        run_args = mock_run.call_args[0][0]
        assert str(run_args[0]) == str(mock_cli_env["python_path"])
        # Use Path's name attribute to compare just the filename part
        assert Path(run_args[1]).name == dummy_script.name
        assert run_args[2:] == ["--message", "test"]

    def test_decorated_tool_execution(self, mock_cli_env, monkeypatch):
        """Test execution of a tool using the @tool decorator."""
        # Setup
        monkeypatch.setattr(sys, "argv", ["jackknife", "decorated_tool", "--verbose"])
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])
        monkeypatch.setattr(cli, "ENVS_DIR", mock_cli_env["env_dir"])

        # Create the decorated_tool script file
        decorated_tool_script = mock_cli_env["tools_dir"] / "decorated_tool.py"
        decorated_tool_script.touch(mode=0o755)

        # Make sure the is_file() check returns True
        original_is_file = Path.is_file

        def mock_is_file(self):
            if self.name == "decorated_tool.py":
                return True
            return original_is_file(self)

        monkeypatch.setattr(Path, "is_file", mock_is_file)

        # Create a mock decorated tool module
        class MockModule:
            pass

        module = MockModule()

        mock_tool_func = MagicMock(return_value=0)
        mock_tool_func._is_jackknife_tool = True
        module.tool_func = mock_tool_func

        # Mock import_tool_module to return our mock module
        monkeypatch.setattr(cli, "import_tool_module", lambda _: module)

        # Mock find_tool_function to return our decorated function
        monkeypatch.setattr(cli, "find_tool_function", lambda _: mock_tool_func)

        # Mock ensure_uv_installed and setup_environment
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        # Define a function that verifies its parameters
        def setup_mock_env(tool_name, tool_script_path):
            assert tool_name == "decorated_tool"
            assert tool_script_path.name == "decorated_tool.py"
            return mock_cli_env["python_path"]

        monkeypatch.setattr(cli, "setup_environment", setup_mock_env)

        # Mock sys.exit to avoid exiting the test
        with patch("sys.exit") as mock_exit:
            cli.main()

            # Verify the tool function was called
            mock_tool_func.assert_called_once()

            # The CLI should exit with the same code the tool returned
            assert any(call.args[0] == 0 for call in mock_exit.call_args_list)

    def test_keyboard_interrupt(self, mock_cli_env, monkeypatch):
        """Test handling of keyboard interrupt."""
        # Setup
        monkeypatch.setattr(sys, "argv", ["jackknife", "dummy"])
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])

        # Create the dummy tool
        dummy_script = mock_cli_env["tools_dir"] / "dummy.py"
        dummy_script.touch(mode=0o755)

        # Mock is_file to return True
        def mock_is_file(self):
            return self.name == "dummy.py" or Path.is_file(self)

        monkeypatch.setattr(Path, "is_file", mock_is_file)

        # Mock functions to avoid actual execution
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        # Define a function that verifies its parameters
        def setup_mock_env(tool_name, tool_script_path):
            assert tool_name == "dummy"
            assert tool_script_path.name == "dummy.py"
            return mock_cli_env["python_path"]

        monkeypatch.setattr(cli, "setup_environment", setup_mock_env)

        # Mock import_tool_module to return None to force subprocess execution
        monkeypatch.setattr(cli, "import_tool_module", lambda _: None)

        # Mock subprocess.run to raise KeyboardInterrupt
        mock_run = MagicMock(side_effect=KeyboardInterrupt)
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock sys.exit to avoid exiting the test
        with patch("sys.exit") as mock_exit:
            cli.main()
            mock_exit.assert_called_once_with(130)

    def test_generic_exception(self, mock_cli_env, monkeypatch):
        """Test handling of generic exceptions."""
        # Setup
        monkeypatch.setattr(sys, "argv", ["jackknife", "dummy"])
        monkeypatch.setattr(cli, "TOOLS_DIR", mock_cli_env["tools_dir"])

        # Create the dummy tool
        dummy_script = mock_cli_env["tools_dir"] / "dummy.py"
        dummy_script.touch(mode=0o755)

        # Mock is_file to return True
        def mock_is_file(self):
            return self.name == "dummy.py" or Path.is_file(self)

        monkeypatch.setattr(Path, "is_file", mock_is_file)

        # Mock functions to avoid actual execution
        monkeypatch.setattr(cli, "ensure_uv_installed", lambda: None)

        # Define a function that verifies its parameters
        def setup_mock_env(tool_name, tool_script_path):
            assert tool_name == "dummy"
            assert tool_script_path.name == "dummy.py"
            return mock_cli_env["python_path"]

        monkeypatch.setattr(cli, "setup_environment", setup_mock_env)

        # Mock import_tool_module to return None to force subprocess execution
        monkeypatch.setattr(cli, "import_tool_module", lambda _: None)

        # Mock subprocess.run to raise an exception
        mock_run = MagicMock(side_effect=Exception("Test error"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock sys.exit to avoid exiting the test
        with patch("sys.exit") as mock_exit:
            cli.main()
            mock_exit.assert_called_once_with(1)
