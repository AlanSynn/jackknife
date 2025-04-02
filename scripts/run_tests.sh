#!/bin/bash
# Run Jackknife tests and generate coverage report

# Ensure we're in the project root
cd "$(dirname "$0")/.." || exit 1

# Create .venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv --seed
fi

# Activate virtual environment
source .venv/bin/activate

# Install dev dependencies
echo "Installing development dependencies..."
uv pip install -e ".[dev]"

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest "$@"

# If tests pass and no arguments provided, open coverage report
if [ $? -eq 0 ] && [ $# -eq 0 ]; then
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        open htmlcov/index.html
    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        # Linux
        if [ -n "$DISPLAY" ]; then
            xdg-open htmlcov/index.html
        else
            echo "Coverage report generated in htmlcov/index.html"
        fi
    elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW32_NT" ] || [ "$(expr substr $(uname -s) 1 10)" == "MINGW64_NT" ]; then
        # Windows
        start htmlcov/index.html
    else
        echo "Coverage report generated in htmlcov/index.html"
    fi
fi