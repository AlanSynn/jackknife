"""
Tests for the jackknife.tool_helpers module.
"""

from unittest.mock import patch

import pytest

from jackknife.tool_helpers import _ARGUMENT_REGISTRY, argument, standalone_script, tool


class TestDecorators:
    """Tests for the tool and argument decorators."""

    def test_argument_decorator(self):
        """Test that the argument decorator correctly attaches metadata."""
        # Constants for test values
        test_help = "Test help"
        test_default = 42

        # Create a type annotation with the argument decorator
        annotated = argument(
            help_text=test_help, arg_type=int, default=test_default, flag=True
        )

        # Verify that it has the _arg_spec_id attribute
        assert hasattr(annotated, "_arg_spec_id")

        # Check that the spec is registered in _ARGUMENT_REGISTRY
        spec_id = annotated._arg_spec_id
        assert spec_id in _ARGUMENT_REGISTRY

        # Verify that the argument spec has the correct values
        arg_spec = _ARGUMENT_REGISTRY[spec_id]
        assert arg_spec.help == test_help
        assert isinstance(arg_spec.type, type(int))
        assert arg_spec.default == test_default
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
            positional: argument(help_text="A positional argument"),
            optional: argument(help_text="An optional argument") = "default",
            flag: argument(flag=True, help_text="A flag argument") = False,
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
        # Constant for test value
        test_number = 42

        @tool
        def typed_tool(
            number: argument(help_text="A number", arg_type=int),
            _flag: argument(flag=True, help_text="A flag") = False,
        ):
            return {"number": number, "number_type": type(number), "flag": _flag}

        # Test with valid input
        with patch("sys.argv", ["tool_script.py", str(test_number)]):
            result = typed_tool()
            assert result["number"] == test_number
            assert result["number_type"] is int

        # Test with invalid input (would normally exit, but we'll catch the SystemExit)
        with patch("sys.argv", ["tool_script.py", "not_a_number"]), pytest.raises(
            SystemExit
        ):
            typed_tool()

    def test_help_output(self, capsys):
        """Test that help text is correctly generated."""

        @tool(description="Test tool description")
        def help_tool(
            positional: argument(help_text="Positional arg help"),
            optional: argument(help_text="Optional arg help") = "default",
            flag: argument(flag=True, help_text="Flag help") = False,
        ):
            # Use the arguments to avoid ARG001 warnings
            if flag:
                print(f"Processing {positional} with optional={optional}")
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
            verbose: argument(
                flag=True, help_text="Verbose mode", short_name="v"
            ) = False,
            output: argument(help_text="Output file", short_name="o") = "default.txt",
        ):
            return {"verbose": verbose, "output": output}

        # Test with short options
        with patch("sys.argv", ["tool_script.py", "-v", "-o", "custom.txt"]):
            result = short_option_tool()
            assert result["verbose"] is True
            assert result["output"] == "custom.txt"
