#!/bin/bash
# Run tests with coverage and generate badges

# Exit immediately if a command exits with non-zero status
set -e

echo "Running tests with coverage..."
python -m pytest --cov=jackknife --cov-report=term-missing --cov-report=html --cov-report=xml

# Check if the coverage-badge directory exists, create if not
mkdir -p .github/badges

# Check if genbadge is installed
if command -v genbadge &> /dev/null; then
    echo "Generating coverage badge..."
    genbadge coverage -i coverage.xml -o .github/badges/coverage.svg
    echo "Coverage badge generated at .github/badges/coverage.svg"
else
    echo "genbadge not installed. Skipping badge generation."
    echo "To install: pip install genbadge[coverage]"
fi

echo "Coverage report generated in htmlcov/ directory"
echo "You can view it by opening htmlcov/index.html in your browser"
echo "Coverage data also saved in coverage.xml for CI integrations"