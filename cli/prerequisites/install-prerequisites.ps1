# Fast.BI CLI Prerequisites Installer for Windows
# Cross-platform script that detects OS and runs appropriate installation

#Requires -Version 5.1

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output (removed for batch file compatibility)

# Logging function
function Write-Log {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Color
}

function Write-Error {
    param([string]$Message)
    Write-Log "ERROR: $Message" "Red"
}

function Write-Warning {
    param([string]$Message)
    Write-Log "WARNING: $Message" "Yellow"
}

function Write-Success {
    param([string]$Message)
    Write-Log "SUCCESS: $Message" "Green"
}

# Function to detect operating system
function Get-OperatingSystem {
    Write-Log "Detecting operating system..." "Blue"
    
    if ($IsWindows) {
        Write-Log "Windows detected" "White"
        return "windows"
    } elseif ($IsLinux) {
        Write-Log "Linux detected" "White"
        return "linux"
    } elseif ($IsMacOS) {
        Write-Log "macOS detected" "White"
        return "macos"
    } else {
        # Fallback for older PowerShell versions
        $os = Get-WmiObject -Class Win32_OperatingSystem
        if ($os.Caption -like "*Windows*") {
            Write-Log "Windows detected (fallback method)" "White"
            return "windows"
        } else {
            Write-Log "Unknown operating system" "Yellow"
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
        Write-Log "Running as Administrator" "White"
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
        Write-Log "Created logs directory: $logsDir" "Blue"
    }
}

# Function to check if WSL2 is installed and available
function Test-WSL2 {
    Write-Log "Checking WSL2 installation..." "Blue"
    
    # Check if WSL is available
    if (-not (Get-Command "wsl" -ErrorAction SilentlyContinue)) {
        Write-Log "WSL not found" "Yellow"
        return $false
    }
    
    # Check WSL version
    try {
        wsl --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "WSL2 is available" "Green"
            return $true
        }
    } catch {
        Write-Log "WSL version check failed" "Yellow"
    }
    
    # Check if WSL is installed but might be WSL1
    try {
        $wslList = wsl --list --verbose 2>$null
        if ($LASTEXITCODE -eq 0) {
            if ($wslList -match "2") {
                Write-Log "WSL2 is installed" "Green"
                return $true
            } else {
                Write-Log "WSL1 detected, WSL2 required" "Yellow"
                return $false
            }
        }
    } catch {
        Write-Log "WSL list check failed" "Yellow"
    }
    
    return $false
}

# Function to install WSL2 and Ubuntu
function Install-WSL2 {
    Write-Log "Installing WSL2 and Ubuntu..." "Blue"
    
    Write-Warning "WSL2 is required to run Fast.BI CLI on Windows"
    Write-Warning "This will install WSL2 and Ubuntu Linux distribution"
    Write-Warning "The installation may take several minutes and require a restart"
    
    $confirm = Read-Host "Do you want to continue with WSL2 installation? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Error "WSL2 installation cancelled. Fast.BI CLI cannot run without WSL2 on Windows."
        exit 1
    }
    
    try {
        # Enable WSL feature
        Write-Log "Enabling WSL feature..." "Blue"
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        
        # Enable Virtual Machine Platform
        Write-Log "Enabling Virtual Machine Platform..." "Blue"
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
        
        # Set WSL2 as default
        Write-Log "Setting WSL2 as default..." "Blue"
        wsl --set-default-version 2
        
        # Install Ubuntu
        Write-Log "Installing Ubuntu..." "Blue"
        wsl --install -d Ubuntu
        
        Write-Success "WSL2 and Ubuntu installation initiated"
        Write-Warning "Please restart your computer and run this script again"
        Write-Warning "After restart, Ubuntu will complete its setup automatically"
        
        $restart = Read-Host "Do you want to restart now? (y/N)"
        if ($restart -eq "y" -or $restart -eq "Y") {
            Write-Log "Restarting computer..." "Blue"
            Restart-Computer -Force
        } else {
            Write-Warning "Please restart manually and run this script again"
            exit 0
        }
        
    } catch {
        Write-Error "WSL2 installation failed: $($_.Exception.Message)"
        exit 1
    }
}

# Function to show WSL2 setup instructions
function Show-WSL2Instructions {
    Write-Log "WSL2 and Ubuntu are ready!" "Green"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Blue
    Write-Host "===========" -ForegroundColor Blue
    Write-Host ""
    Write-Host "1. Open WSL2 Ubuntu:" -ForegroundColor White
    Write-Host "   wsl -d Ubuntu" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "2. Clone the repository in WSL2:" -ForegroundColor White
    Write-Host "   git clone https://github.com/fast-bi/data-development-platform.git" -ForegroundColor Yellow
    Write-Host "   cd data-development-platform" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "3. Run the Linux prerequisites installer:" -ForegroundColor White
    Write-Host "   chmod +x cli/prerequisites/install-prerequisites.sh" -ForegroundColor Yellow
    Write-Host "   ./cli/prerequisites/install-prerequisites.sh" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "4. After installation, run the CLI from WSL2:" -ForegroundColor White
    Write-Host "   python3 cli.py" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Tip: You can access your Windows files from WSL2 at /mnt/c/" -ForegroundColor Blue
    Write-Host "Tip: Use 'code .' in WSL2 to open VS Code with WSL2 integration" -ForegroundColor Blue
}

# Function to run platform-specific installation
function Invoke-PlatformInstall {
    param([string]$Platform)
    
    switch ($Platform) {
        "windows" {
            # Check if WSL2 is available
            if (Test-WSL2) {
                Write-Log "WSL2 detected, showing setup instructions..." "Blue"
                Show-WSL2Instructions
            } else {
                Write-Log "WSL2 not found, installing WSL2 and Ubuntu..." "Blue"
                Install-WSL2
            }
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
}

# Function to verify installation
function Test-Installation {
    Write-Log "Verifying installation..." "Blue"
    
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
    Write-Host ""
    Write-Host "Summary:" -ForegroundColor Blue
    Write-Host "========" -ForegroundColor Blue
    Write-Host "WSL2 and Ubuntu are ready for Fast.BI CLI" -ForegroundColor Green
    Write-Host "Follow the instructions above to complete setup in WSL2" -ForegroundColor White
    Write-Host "All prerequisites will be installed in the Linux environment" -ForegroundColor White
    Write-Host ""
    Write-Host "Benefits of this approach:" -ForegroundColor Blue
    Write-Host "  - Consistent behavior across Windows, Linux, and macOS" -ForegroundColor White
    Write-Host "  - No Windows-specific compatibility issues" -ForegroundColor White
    Write-Host "  - Full Linux toolchain support" -ForegroundColor White
    Write-Host "  - Better performance for development tools" -ForegroundColor White
}

# Function to check if we're in the right directory
function Test-Directory {
    if (-not (Test-Path "..\..\cli.py")) {
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
            Write-Log "Installation cancelled" "Yellow"
            exit 1
        }
    }
}

# Main installation function
function Main {
    Write-Host "Fast.BI CLI Prerequisites Installer" -ForegroundColor Blue
    Write-Host "====================================" -ForegroundColor Blue
    Write-Host ""
    
    # Setup logging
    New-LogsDirectory
    
    # Detect OS
    $os = Get-OperatingSystem
    Write-Log "Detected OS: $os" "Blue"
    
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
