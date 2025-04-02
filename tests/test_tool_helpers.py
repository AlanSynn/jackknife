"""
Tests for the jackknife.tool_helpers module.
"""

import sys
from unittest.mock import patch
import pytest

from jackknife.tool_helpers import tool, argument, standalone_script, _ARGUMENT_REGISTRY


class TestDecorators:
    """Tests for the tool and argument decorators."""

    def test_argument_decorator(self):
        """Test that the argument decorator correctly attaches metadata."""
        # Create a type annotation with the argument decorator
        annotated = argument(help="Test help", type=int, default=42, flag=True)

        # Verify that it has the _arg_spec_id attribute
        assert hasattr(annotated, "_arg_spec_id")

        # Check that the spec is registered in _ARGUMENT_REGISTRY
        spec_id = getattr(annotated, "_arg_spec_id")
        assert spec_id in _ARGUMENT_REGISTRY

        # Verify that the argument spec has the correct values
        arg_spec = _ARGUMENT_REGISTRY[spec_id]
        assert arg_spec.help == "Test help"
        assert arg_spec.type == int
        assert arg_spec.default == 42
        assert arg_spec.flag is True
        assert arg_spec.name is None  # Name gets set during tool execution

    def test_tool_decorator_marks_function(self):
        """Test that the tool decorator marks the function correctly."""

        @tool
        def sample_tool():
            return 0

        # Check that the function is marked as a jackknife tool
        assert hasattr(sample_tool, "_is_jackknife_tool")
        assert sample_tool._is_jackknife_tool is True

    def test_standalone_script(self):
        """Test the standalone_script function."""
        test_exit_code = 42

        def test_func():
            return test_exit_code

        # Mock sys.exit to avoid actually exiting during the test
        with patch("sys.exit") as mock_exit:
            standalone_script(test_func)
            mock_exit.assert_called_once_with(test_exit_code)


class TestToolExecution:
    """Tests for the execution of decorated tools."""

    def test_tool_execution_with_args(self):
        """Test that a decorated tool correctly processes arguments."""

        @tool
        def sample_tool(
            positional: argument(help="A positional argument"),
            optional: argument(help="An optional argument") = "default",
            flag: argument(flag=True, help="A flag argument") = False,
        ):
            # Return the arguments as a dictionary for testing
            return {"positional": positional, "optional": optional, "flag": flag}

        # Mock sys.argv and run the tool
        with patch(
            "sys.argv", ["tool_script.py", "value", "--optional", "custom", "--flag"]
        ):
            result = sample_tool()

            # Check that arguments were parsed correctly
            assert result["positional"] == "value"
            assert result["optional"] == "custom"
            assert result["flag"] is True

    def test_type_conversion(self):
        """Test that argument types are correctly converted."""

        @tool
        def typed_tool(
            number: argument(help="A number", type=int),
            flag: argument(flag=True, help="A flag") = False,
        ):
            return {"number": number, "number_type": type(number), "flag": flag}

        # Test with valid input
        with patch("sys.argv", ["tool_script.py", "42"]):
            result = typed_tool()
            assert result["number"] == 42
            assert result["number_type"] is int

        # Test with invalid input (would normally exit, but we'll catch the SystemExit)
        with patch("sys.argv", ["tool_script.py", "not_a_number"]):
            with pytest.raises(SystemExit):
                typed_tool()

    def test_help_output(self, capsys):
        """Test that help text is correctly generated."""

        @tool(description="Test tool description")
        def help_tool(
            positional: argument(help="Positional arg help"),
            optional: argument(help="Optional arg help") = "default",
            flag: argument(flag=True, help="Flag help") = False,
        ):
            return 0

        # Mock sys.argv to request help
        with patch("sys.argv", ["tool_script.py", "--help"]):
            # This should print help and exit, which we catch
            with pytest.raises(SystemExit):
                help_tool()

            # Capture and check the output
            captured = capsys.readouterr()
            assert "Test tool description" in captured.out
            assert "Positional arg help" in captured.out
            assert "Optional arg help" in captured.out
            assert "Flag help" in captured.out

    def test_short_names(self):
        """Test that short option names work correctly."""

        @tool
        def short_option_tool(
            verbose: argument(flag=True, help="Verbose mode", short_name="v") = False,
            output: argument(help="Output file", short_name="o") = "default.txt",
        ):
            return {"verbose": verbose, "output": output}

        # Test with short options
        with patch("sys.argv", ["tool_script.py", "-v", "-o", "custom.txt"]):
            result = short_option_tool()
            assert result["verbose"] is True
            assert result["output"] == "custom.txt"
