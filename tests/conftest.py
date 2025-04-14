"""
Pytest configuration and fixtures for the Jackknife project.
"""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_tools_dir(temp_dir):
    """Create a temporary directory with test tools."""
    # Create a tools directory
    tools_dir = temp_dir / "tools"
    tools_dir.mkdir()

    # Copy the test tools from the fixtures
    fixtures_dir = Path(__file__).parent / "fixtures" / "tools"
    for tool_file in fixtures_dir.glob("*"):
        if tool_file.is_file():
            shutil.copy(tool_file, tools_dir / tool_file.name)

    return tools_dir


@pytest.fixture
def mock_env_dir(temp_dir):
    """Create a temporary directory for environments."""
    env_dir = temp_dir / "envs"
    env_dir.mkdir()
    return env_dir


@pytest.fixture
def mock_cli_env(monkeypatch, mock_tools_dir, mock_env_dir):
    """Set up environment variables and paths for CLI testing."""
    # Mock the environment directory
    monkeypatch.setenv("JACKKNIFE_ENVS_DIR", str(mock_env_dir))

    # Prepare a mock environment structure for a tool
    dummy_env_dir = mock_env_dir / "dummy"
    dummy_env_dir.mkdir()
    bin_dir = dummy_env_dir / "bin"
    bin_dir.mkdir()

    # Create a mock Python executable
    python_path = bin_dir / "python"
    python_path.touch(mode=0o755)  # Make it executable

    # Return the environment configuration
    env_config = {
        "tools_dir": mock_tools_dir,
        "env_dir": mock_env_dir,
        "dummy_env_dir": dummy_env_dir,
        "python_path": python_path,
    }
    return env_config
