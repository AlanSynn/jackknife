#!/bin/bash
# Run Ruff linting on the project

# Exit immediately if a command exits with non-zero status
set -e

echo "Running Ruff linting..."
ruff check jackknife tests tools

echo "All checks passed! ✅"