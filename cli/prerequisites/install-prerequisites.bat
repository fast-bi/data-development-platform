@echo off
REM Fast.BI CLI Prerequisites Installer for Windows (WSL2)
REM This batch file provides instructions and runs the PowerShell installer

echo.
echo ========================================
echo Fast.BI CLI Prerequisites Installer
echo ========================================
echo.
echo IMPORTANT: Fast.BI CLI now requires WSL2 for Windows compatibility.
echo This ensures consistent behavior across all platforms and eliminates
echo Windows-specific compatibility issues.
echo.
echo The installer will:
echo 1. Check if WSL2 is installed
echo 2. Install WSL2 and Ubuntu if needed
echo 3. Provide instructions for completing setup in WSL2
echo.
echo Benefits of WSL2 approach:
echo - Consistent behavior across Windows, Linux, and macOS
echo - No Windows-specific compatibility issues
echo - Full Linux toolchain support
echo - Better performance for development tools
echo.
echo Prerequisites:
echo - Windows 10 version 2004+ or Windows 11
echo - PowerShell 5.1 or later
echo - Administrator privileges
echo - Internet connection
echo.
echo Note: WSL2 installation may require a system restart.
echo.

set /p continue="Do you want to continue with WSL2 setup? (Y/N): "
if /i "%continue%"=="Y" goto :install
if /i "%continue%"=="N" goto :exit
goto :continue

:install
echo.
echo Starting WSL2 setup...
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
    echo WSL2 setup completed successfully!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Follow the instructions shown above
    echo 2. Open WSL2 Ubuntu: wsl -d Ubuntu
    echo 3. Clone the repository in WSL2
    echo 4. Run the Linux prerequisites installer
    echo 5. Use the CLI from within WSL2
    echo.
    echo For more information, see the README files.
    echo.
) else (
    echo.
    echo ========================================
    echo WSL2 setup failed!
    echo ========================================
    echo.
    echo Please check the error messages above.
    echo Common solutions:
    echo - Run as Administrator
    echo - Check your internet connection
    echo - Ensure sufficient disk space
    echo - Check Windows Defender/firewall settings
    echo - Verify Windows version supports WSL2
    echo.
)

goto :exit

:exit
echo.
echo Press any key to exit...
pause >nul
exit /b 0
