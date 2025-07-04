@echo off
REM Build and Run MCP Server for Splunk - Windows Batch Wrapper
REM This batch file calls the PowerShell version for compatibility

echo.
echo 🚀 MCP Server for Splunk - Windows Setup
echo ========================================
echo.
echo This script will launch the PowerShell version of the build script.
echo.

REM Check if PowerShell is available
where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PowerShell not found. Please install PowerShell or use the .ps1 script directly.
    echo.
    echo Download PowerShell from: https://aka.ms/powershell
    echo Or run directly: .\scripts\build_and_run.ps1
    pause
    exit /b 1
)

REM Get the directory of this batch file
set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%build_and_run.ps1

REM Check if the PowerShell script exists
if not exist "%PS_SCRIPT%" (
    echo [ERROR] PowerShell script not found: %PS_SCRIPT%
    echo.
    echo Please ensure you're running this from the project root directory.
    pause
    exit /b 1
)

echo [INFO] Launching PowerShell script: %PS_SCRIPT%
echo.

REM Launch the PowerShell script with all arguments passed through
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*

REM Check the exit code from PowerShell
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PowerShell script failed with exit code: %ERRORLEVEL%
    echo.
    echo Troubleshooting tips:
    echo - Ensure PowerShell execution policy allows script execution
    echo - Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    echo - Check if Python 3.10+ is installed
    echo - Verify Docker Desktop is running (for Docker mode)
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [SUCCESS] Setup completed successfully!
echo.
pause 