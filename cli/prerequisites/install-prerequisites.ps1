# Fast.BI CLI Prerequisites Installer for Windows
# Cross-platform script that detects OS and runs appropriate installation

#Requires -Version 5.1

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$White = "White"

# Logging function
function Write-Log {
    param(
        [string]$Message,
        [string]$Color = $White
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Color
}

function Write-Error {
    param([string]$Message)
    Write-Log "ERROR: $Message" $Red
}

function Write-Warning {
    param([string]$Message)
    Write-Log "WARNING: $Message" $Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Log "SUCCESS: $Message" $Green
}

# Function to detect operating system
function Get-OperatingSystem {
    Write-Log "Detecting operating system..." $Blue
    
    if ($IsWindows) {
        Write-Log "Windows detected" $White
        return "windows"
    } elseif ($IsLinux) {
        Write-Log "Linux detected" $White
        return "linux"
    } elseif ($IsMacOS) {
        Write-Log "macOS detected" $White
        return "macos"
    } else {
        # Fallback for older PowerShell versions
        $os = Get-WmiObject -Class Win32_OperatingSystem
        if ($os.Caption -like "*Windows*") {
            Write-Log "Windows detected (fallback method)" $White
            return "windows"
        } else {
            Write-Log "Unknown operating system" $Yellow
            return "unknown"
        }
    }
}

# Function to check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to check privileges
function Test-Privileges {
    if (Test-Administrator) {
        Write-Log "Running as Administrator" $White
        return $true
    } else {
        Write-Warning "This script requires Administrator privileges"
        Write-Warning "Please run PowerShell as Administrator and try again"
        return $false
    }
}

# Function to create logs directory
function New-LogsDirectory {
    $logsDir = "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir | Out-Null
        Write-Log "Created logs directory: $logsDir" $Blue
    }
}

# Function to run platform-specific installation
function Invoke-PlatformInstall {
    param([string]$Platform)
    
    $scriptPath = ""
    
    switch ($Platform) {
        "windows" {
            $scriptPath = ".\windows\install-windows.ps1"
        }
        "linux" {
            Write-Error "Linux detected. Please run the bash script instead:"
            Write-Error "  ./install-prerequisites.sh"
            exit 1
        }
        "macos" {
            Write-Error "macOS detected. Please run the bash script instead:"
            Write-Error "  ./install-prerequisites.sh"
            exit 1
        }
        default {
            Write-Error "Unsupported operating system: $Platform"
            exit 1
        }
    }
    
    if (-not (Test-Path $scriptPath)) {
        Write-Error "Installation script not found: $scriptPath"
        exit 1
    }
    
    Write-Log "Running $Platform installation script..." $Blue
    
    # Run the platform-specific script with logging
    $logFile = "logs\install-$Platform-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
    
    try {
        & $scriptPath 2>&1 | Tee-Object -FilePath $logFile
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Platform-specific installation completed successfully"
        } else {
            Write-Error "Platform-specific installation failed"
            exit 1
        }
    } catch {
        Write-Error "Error running platform-specific installation: $($_.Exception.Message)"
        exit 1
    }
}

# Function to verify installation
function Test-Installation {
    Write-Log "Verifying installation..." $Blue
    
    $verifyScript = ".\verify-prerequisites.ps1"
    if (Test-Path $verifyScript) {
        try {
            & $verifyScript
            if ($LASTEXITCODE -eq 0) {
                Write-Success "All prerequisites verified successfully!"
            } else {
                Write-Warning "Some prerequisites may not be properly installed"
                Write-Warning "Check the verification output above for details"
            }
        } catch {
            Write-Warning "Error running verification script: $($_.Exception.Message)"
        }
    } else {
        Write-Warning "Verification script not found. Please run verification manually."
    }
}

# Function to show installation summary
function Show-InstallationSummary {
    Write-Log "Installation Summary:" $Blue
    Write-Host "====================" $White
    Write-Host "✅ Prerequisites installation completed" $Green
    Write-Host "📁 Logs saved to: logs\" $White
    Write-Host "🔍 Run verification: .\verify-prerequisites.ps1" $White
    Write-Host ""
    Write-Host "Next steps:" $White
    Write-Host "1. Configure your cloud provider credentials" $White
    Write-Host "2. Run the Fast.BI CLI: python cli.py" $White
    Write-Host "3. Follow the deployment guide in docs\" $White
}

# Function to check if we're in the right directory
function Test-Directory {
    if (-not (Test-Path "..\cli.py")) {
        Write-Error "This script must be run from the cli\prerequisites\ directory"
        Write-Error "Please navigate to the correct directory and try again"
        exit 1
    }
}

# Function to check available disk space
function Test-DiskSpace {
    $drive = (Get-Location).Drive
    $freeSpace = $drive.Free / 1GB
    
    if ($freeSpace -lt 2) {
        Write-Warning "Low disk space detected. At least 2GB recommended for installation."
        Write-Warning "Available space: $([math]::Round($freeSpace, 2)) GB"
        
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            Write-Log "Installation cancelled" $Yellow
            exit 1
        }
    }
}

# Main installation function
function Main {
    Write-Host "🚀 Fast.BI CLI Prerequisites Installer" $Blue
    Write-Host "======================================" $Blue
    Write-Host ""
    
    # Setup logging
    New-LogsDirectory
    
    # Detect OS
    $os = Get-OperatingSystem
    Write-Log "Detected OS: $os" $Blue
    
    # Check privileges
    if (-not (Test-Privileges)) {
        exit 1
    }
    
    # Check if we're in the right directory
    Test-Directory
    
    # Check available disk space
    Test-DiskSpace
    
    # Run platform-specific installation
    Invoke-PlatformInstall $os
    
    # Verify installation
    Test-Installation
    
    # Show summary
    Show-InstallationSummary
}

# Handle script interruption
try {
    # Run main function
    Main
}
catch {
    Write-Error "Installation interrupted: $($_.Exception.Message)"
    exit 1
}
