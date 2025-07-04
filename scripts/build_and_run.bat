@echo off
REM MCP Server for Splunk - Windows Batch File Wrapper
REM This script calls the PowerShell script for users who prefer Command Prompt

echo MCP Server for Splunk - Windows Setup
echo =====================================
echo.

REM Check if PowerShell is available
where powershell >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: PowerShell is not available on this system.
    echo PowerShell is required to run this setup script.
    echo.
    echo Please install PowerShell or run the script directly:
    echo   powershell -File .\scripts\build_and_run.ps1
    echo.
    pause
    exit /b 1
)

REM Get the directory of this batch file
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%build_and_run.ps1"

REM Check if the PowerShell script exists
if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at: %PS_SCRIPT%
    echo Please ensure you're running this from the project root directory.
    echo.
    pause
    exit /b 1
)

echo Launching PowerShell script...
echo.

REM Execute the PowerShell script with execution policy bypass
REM Pass any command line arguments to the PowerShell script
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*

REM Capture the exit code from PowerShell
set POWERSHELL_EXIT_CODE=%errorlevel%

echo.
if %POWERSHELL_EXIT_CODE% equ 0 (
    echo Setup completed successfully!
) else (
    echo Setup encountered an error ^(exit code: %POWERSHELL_EXIT_CODE%^)
    echo.
    echo Troubleshooting:
    echo   1. Run as Administrator if you encounter permission issues
    echo   2. Check prerequisites: .\scripts\check-prerequisites.ps1
    echo   3. Try running PowerShell script directly: powershell -File .\scripts\build_and_run.ps1
)

echo.
echo Press any key to exit...
pause >nul

exit /b %POWERSHELL_EXIT_CODE% 