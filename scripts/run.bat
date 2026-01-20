@echo off
setlocal enabledelayedexpansion

REM Change to project root (scripts\..)
cd /d "%~dp0.."

echo.
echo [Oncology Registry Copilot] Initializing environment...
echo.

REM Try to activate the virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment: .venv
    call ".venv\Scripts\activate.bat"
) else (
    echo WARNING: Virtual environment .venv not found.
    echo Make sure you have created it and installed requirements:
    echo    python -m venv .venv
    echo    .venv\Scripts\activate
    echo    pip install -r requirements.txt
    echo.
)

echo.
echo Running full pipeline: NER -> pre-abstract -> evaluation
echo.

python scripts\run_full_pipeline.py

echo.
echo Pipeline finished. Press any key to close this window.
pause >nul
endlocal
