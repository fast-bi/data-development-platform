@echo off
REM Fast.BI CLI Prerequisites Installer for Windows
REM This batch file provides instructions and runs the PowerShell installer

echo.
echo ========================================
echo Fast.BI CLI Prerequisites Installer
echo ========================================
echo.
echo This installer will install all required tools for the Fast.BI CLI:
echo.
echo Required Tools:
echo - Python 3.9+
echo - kubectl
echo - gcloud CLI
echo - Terraform
echo - Terragrunt
echo - Helm
echo - Git
echo - jq
echo - curl
echo - Docker Desktop (optional)
echo.
echo Prerequisites:
echo - Windows 10/11 or Windows Server 2016+
echo - PowerShell 5.1 or later
echo - Administrator privileges
echo - Internet connection
echo.
echo The installer will:
echo 1. Check system requirements
echo 2. Install Chocolatey package manager
echo 3. Install all required tools
echo 4. Configure environment variables
echo 5. Verify installations
echo.
echo Note: This process may take 10-30 minutes depending on your system.
echo.

set /p continue="Do you want to continue? (Y/N): "
if /i "%continue%"=="Y" goto :install
if /i "%continue%"=="N" goto :exit
goto :continue

:install
echo.
echo Starting installation...
echo.

REM Check if PowerShell is available
powershell -Command "Get-Host" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PowerShell is not available on this system.
    echo Please install PowerShell 5.1 or later and try again.
    pause
    exit /b 1
)

REM Check PowerShell version
for /f "tokens=*" %%i in ('powershell -Command "$PSVersionTable.PSVersion.Major"') do set psversion=%%i
if %psversion% lss 5 (
    echo ERROR: PowerShell 5.1 or later is required.
    echo Current version: %psversion%
    echo Please upgrade PowerShell and try again.
    pause
    exit /b 1
)

echo PowerShell version check passed: %psversion%
echo.

REM Run the PowerShell installer
echo Running PowerShell installer...
powershell -ExecutionPolicy Bypass -File "install-prerequisites.ps1"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Installation completed successfully!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Restart your terminal/PowerShell
    echo 2. Configure your cloud provider credentials
    echo 3. Run the Fast.BI CLI: python cli.py
    echo.
    echo For verification, run: verify-prerequisites.ps1
    echo.
) else (
    echo.
    echo ========================================
    echo Installation failed!
    echo ========================================
    echo.
    echo Please check the error messages above.
    echo Common solutions:
    echo - Run as Administrator
    echo - Check your internet connection
    echo - Ensure sufficient disk space
    echo - Check Windows Defender/firewall settings
    echo.
)

goto :exit

:exit
echo.
echo Press any key to exit...
pause >nul
exit /b 0
