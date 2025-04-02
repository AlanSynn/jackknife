#!/bin/bash
# Run Ruff formatting on the project

# Exit immediately if a command exits with non-zero status
set -e

echo "Running Ruff formatting..."
ruff format jackknife tests tools

echo "Formatting complete! ✅"