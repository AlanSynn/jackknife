@echo off
REM Run Jackknife tests and generate coverage report

REM Ensure we're in the project root
cd /d %~dp0\..

REM Create .venv if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    call uv venv --seed
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dev dependencies
echo Installing development dependencies...
call uv pip install -e .[dev]

REM Run tests with coverage
echo Running tests with coverage...
python -m pytest %*

REM If tests pass and no arguments provided, open coverage report
if %ERRORLEVEL% EQU 0 if "%~1"=="" (
    echo Opening coverage report...
    start "" htmlcov\index.html
)