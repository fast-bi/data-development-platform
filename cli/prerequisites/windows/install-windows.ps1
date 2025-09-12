# Fast.BI CLI Prerequisites Installer for Windows
# This script now redirects to WSL2 installation for better compatibility

#Requires -Version 5.1
#Requires -RunAsAdministrator

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

# Function to check if command exists
function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check Windows version
function Test-WindowsVersion {
    Write-Log "Checking Windows version..." $Blue
    
    $os = Get-WmiObject -Class Win32_OperatingSystem
    $version = $os.Version
    $build = $os.BuildNumber
    
    Write-Log "Windows version: $version (Build $build)" $White
    
    # Check if Windows 10/11 or Server 2016+
    if ($build -lt 14393) {
        Write-Error "Windows 10 (Build 14393) or later is required"
        Write-Error "Current build: $build"
        exit 1
    }
    
    Write-Success "Windows version check passed"
}

# Function to check PowerShell version
function Test-PowerShellVersion {
    Write-Log "Checking PowerShell version..." $Blue
    
    $psVersion = $PSVersionTable.PSVersion
    Write-Log "PowerShell version: $psVersion" $White
    
    if ($psVersion.Major -lt 5) {
        Write-Error "PowerShell 5.1 or later is required"
        Write-Error "Current version: $psVersion"
        exit 1
    }
    
    Write-Success "PowerShell version check passed"
}

# Function to set execution policy
function Set-ExecutionPolicy {
    Write-Log "Setting PowerShell execution policy..." $Blue
    
    $currentPolicy = Get-ExecutionPolicy
    Write-Log "Current execution policy: $currentPolicy" $White
    
    if ($currentPolicy -eq "Restricted") {
        Write-Log "Setting execution policy to RemoteSigned..." $Yellow
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force
        Write-Success "Execution policy set to RemoteSigned"
    } else {
        Write-Log "Execution policy already allows script execution" $White
    }
}

# Function to install Chocolatey
function Install-Chocolatey {
    Write-Log "Installing Chocolatey..." $Blue
    
    if (Test-Command "choco") {
        Write-Log "Chocolatey already installed" $White
        Write-Log "Updating Chocolatey..." $Blue
        choco upgrade chocolatey -y
        return
    }
    
    # Install Chocolatey
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Verify installation
    if (Test-Command "choco") {
        Write-Success "Chocolatey installed successfully"
    } else {
        Write-Error "Chocolatey installation failed"
        exit 1
    }
}

# Function to install Python
function Install-Python {
    Write-Log "Installing Python..." $Blue
    
    if (Test-Command "python") {
        $version = python --version 2>&1
        Write-Log "Python already installed: $version" $White
        
        # Check if version meets requirements
        if ($version -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 9) {
                Write-Log "Python version meets requirements" $White
                return
            }
        }
        Write-Warning "Python version may not meet requirements (need 3.9+)"
    }
    
    # Install Python via Chocolatey
    Write-Log "Installing Python 3.11 via Chocolatey..." $Blue
    choco install python311 -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Verify installation
    if (Test-Command "python") {
        $version = python --version 2>&1
        Write-Success "Python installed successfully: $version"
    } else {
        Write-Error "Python installation failed"
        exit 1
    }
}

# Function to install kubectl
function Install-Kubectl {
    Write-Log "Installing kubectl..." $Blue
    
    if (Test-Command "kubectl") {
        Write-Log "kubectl already installed" $White
        return
    }
    
    # Install kubectl via Chocolatey
    Write-Log "Installing kubectl via Chocolatey..." $Blue
    choco install kubernetes-cli -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Verify installation
    if (Test-Command "kubectl") {
        $version = kubectl version --client --short 2>$null
        if (-not $version) { $version = kubectl version --client 2>$null }
        Write-Success "kubectl installed successfully: $version"
    } else {
        Write-Error "kubectl installation failed"
        exit 1
    }
}

# Function to install gcloud CLI
function Install-Gcloud {
    Write-Log "Installing Google Cloud CLI..." $Blue
    
    if (Test-Command "gcloud") {
        Write-Log "gcloud CLI already installed" $White
        return
    }
    
    # Install gcloud CLI via Chocolatey
    Write-Log "Installing gcloud CLI via Chocolatey..." $Blue
    choco install gcloudsdk -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Verify installation
    if (Test-Command "gcloud") {
        $version = gcloud --version | Select-Object -First 1
        Write-Success "gcloud CLI installed successfully: $version"
    } else {
        Write-Error "gcloud CLI installation failed"
        exit 1
    }
}

# Function to install Terraform
function Install-Terraform {
    Write-Log "Installing Terraform..." $Blue
    
    if (Test-Command "terraform") {
        Write-Log "Terraform already installed" $White
        return
    }
    
    # Install Terraform via Chocolatey
    Write-Log "Installing Terraform via Chocolatey..." $Blue
    choco install terraform -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Verify installation
    if (Test-Command "terraform") {
        $version = terraform --version | Select-Object -First 1
        Write-Success "Terraform installed successfully: $version"
    } else {
        Write-Error "Terraform installation failed"
        exit 1
    }
}

# Function to install Terragrunt
function Install-Terragrunt {
    Write-Log "Installing Terragrunt..." $Blue
    
    if (Test-Command "terragrunt") {
        Write-Log "Terragrunt already installed" $White
        return
    }
    
    # Install Terragrunt via Chocolatey
    Write-Log "Installing Terragrunt via Chocolatey..." $Blue
    choco install terragrunt -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Verify installation
    if (Test-Command "terragrunt") {
        $version = terragrunt --version | Select-Object -First 1
        Write-Success "Terragrunt installed successfully: $version"
    } else {
        Write-Error "Terragrunt installation failed"
        exit 1
    }
}

# Function to install Helm
function Install-Helm {
    Write-Log "Installing Helm..." $Blue
    
    if (Test-Command "helm") {
        Write-Log "Helm already installed" $White
        return
    }
    
    # Install Helm via Chocolatey
    Write-Log "Installing Helm via Chocolatey..." $Blue
    choco install kubernetes-helm -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Verify installation
    if (Test-Command "helm") {
        $version = helm version --short 2>$null
        if (-not $version) { $version = helm version 2>$null }
        Write-Success "Helm installed successfully: $version"
    } else {
        Write-Error "Helm installation failed"
        exit 1
    }
}

# Function to install additional tools
function Install-AdditionalTools {
    Write-Log "Installing additional tools..." $Blue
    
    # Install Git
    if (-not (Test-Command "git")) {
        Write-Log "Installing Git..." $Blue
        choco install git -y
        Write-Success "Git installed successfully"
    } else {
        Write-Log "Git already installed" $White
    }
    
    # Install jq
    if (-not (Test-Command "jq")) {
        Write-Log "Installing jq..." $Blue
        choco install jq -y
        Write-Success "jq installed successfully"
    } else {
        Write-Log "jq already installed" $White
    }
    
    # Install Docker Desktop (optional but recommended)
    if (-not (Test-Command "docker")) {
        Write-Log "Installing Docker Desktop..." $Blue
        choco install docker-desktop -y
        Write-Success "Docker Desktop installed successfully"
        Write-Warning "Docker Desktop requires manual setup and login"
    } else {
        Write-Log "Docker already installed" $White
    }
    
    # Install curl if not present
    if (-not (Test-Command "curl")) {
        Write-Log "Installing curl..." $Blue
        choco install curl -y
        Write-Success "curl installed successfully"
    } else {
        Write-Log "curl already installed" $White
    }
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Function to configure environment variables
function Set-EnvironmentVariables {
    Write-Log "Configuring environment variables..." $Blue
    
    # Add Python Scripts to PATH if not already there
    $pythonScriptsPath = "$env:LOCALAPPDATA\Programs\Python\Python311\Scripts"
    if ($env:Path -notlike "*$pythonScriptsPath*") {
        Write-Log "Adding Python Scripts to PATH..." $Blue
        [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$pythonScriptsPath", "User")
        $env:Path += ";$pythonScriptsPath"
        Write-Success "Python Scripts added to PATH"
    } else {
        Write-Log "Python Scripts already in PATH" $White
    }
    
    # Add gcloud CLI to PATH if not already there
    $gcloudPath = "$env:ProgramData\chocolatey\lib\gcloudsdk\tools\google-cloud-sdk\bin"
    if ($env:Path -notlike "*$gcloudPath*") {
        Write-Log "Adding gcloud CLI to PATH..." $Blue
        [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$gcloudPath", "User")
        $env:Path += ";$gcloudPath"
        Write-Success "gcloud CLI added to PATH"
    } else {
        Write-Log "gcloud CLI already in PATH" $White
    }
}

# Function to verify all installations
function Test-Installations {
    Write-Log "Verifying all installations..." $Blue
    
    $tools = @("python", "kubectl", "gcloud", "terraform", "terragrunt", "helm", "git", "jq", "curl")
    $allInstalled = $true
    
    foreach ($tool in $tools) {
        if (Test-Command $tool) {
            Write-Success "✅ $tool`: installed"
        } else {
            Write-Error "❌ $tool`: not found"
            $allInstalled = $false
        }
    }
    
    if ($allInstalled) {
        Write-Success "All tools verified successfully!"
    } else {
        Write-Warning "Some tools may not be properly installed"
        return $false
    }
    
    return $true
}

# Function to show next steps
function Show-NextSteps {
    Write-Host ""
    Write-Host "📋 Summary:" $Blue
    Write-Host "===========" $Blue
    Write-Host "✅ WSL2 and Ubuntu are ready for Fast.BI CLI" $Green
    Write-Host "📁 Follow the instructions above to complete setup in WSL2" $White
    Write-Host "🔧 All prerequisites will be installed in the Linux environment" $White
    Write-Host ""
    Write-Host "💡 Benefits of this approach:" $Blue
    Write-Host "   • Consistent behavior across Windows, Linux, and macOS" $White
    Write-Host "   • No Windows-specific compatibility issues" $White
    Write-Host "   • Full Linux toolchain support" $White
    Write-Host "   • Better performance for development tools" $White
    Write-Host ""
    Write-Host "📚 Documentation:" $White
    Write-Host "  - CLI help: python3 cli.py --help" $White
    Write-Host "  - Deployment guide: docs/" $White
    Write-Host ""
    Write-Host "🐧 WSL2 provides native Linux compatibility for all tools" $Green
}

# Function to check if WSL2 is installed and available
function Test-WSL2 {
    Write-Log "Checking WSL2 installation..." $Blue
    
    # Check if WSL is available
    if (-not (Get-Command "wsl" -ErrorAction SilentlyContinue)) {
        Write-Log "WSL not found" $Yellow
        return $false
    }
    
    # Check WSL version
    try {
        $wslVersion = wsl --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "WSL2 is available" $Green
            return $true
        }
    } catch {
        Write-Log "WSL version check failed" $Yellow
    }
    
    # Check if WSL is installed but might be WSL1
    try {
        $wslList = wsl --list --verbose 2>$null
        if ($LASTEXITCODE -eq 0) {
            if ($wslList -match "2") {
                Write-Log "WSL2 is installed" $Green
                return $true
            } else {
                Write-Log "WSL1 detected, WSL2 required" $Yellow
                return $false
            }
        }
    } catch {
        Write-Log "WSL list check failed" $Yellow
    }
    
    return $false
}

# Function to install WSL2 and Ubuntu
function Install-WSL2 {
    Write-Log "Installing WSL2 and Ubuntu..." $Blue
    
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
        Write-Log "Enabling WSL feature..." $Blue
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        
        # Enable Virtual Machine Platform
        Write-Log "Enabling Virtual Machine Platform..." $Blue
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
        
        # Set WSL2 as default
        Write-Log "Setting WSL2 as default..." $Blue
        wsl --set-default-version 2
        
        # Install Ubuntu
        Write-Log "Installing Ubuntu..." $Blue
        wsl --install -d Ubuntu
        
        Write-Success "WSL2 and Ubuntu installation initiated"
        Write-Warning "Please restart your computer and run this script again"
        Write-Warning "After restart, Ubuntu will complete its setup automatically"
        
        $restart = Read-Host "Do you want to restart now? (y/N)"
        if ($restart -eq "y" -or $restart -eq "Y") {
            Write-Log "Restarting computer..." $Blue
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
    Write-Log "WSL2 and Ubuntu are ready!" $Green
    Write-Host ""
    Write-Host "🚀 Next Steps:" $Blue
    Write-Host "=============" $Blue
    Write-Host ""
    Write-Host "1. Open WSL2 Ubuntu:" $White
    Write-Host "   wsl -d Ubuntu" $Yellow
    Write-Host ""
    Write-Host "2. Clone the repository in WSL2:" $White
    Write-Host "   git clone https://github.com/your-org/data-development-platform.git" $Yellow
    Write-Host "   cd data-development-platform" $Yellow
    Write-Host ""
    Write-Host "3. Run the Linux prerequisites installer:" $White
    Write-Host "   chmod +x cli/prerequisites/install-prerequisites.sh" $Yellow
    Write-Host "   ./cli/prerequisites/install-prerequisites.sh" $Yellow
    Write-Host ""
    Write-Host "4. After installation, run the CLI from WSL2:" $White
    Write-Host "   python3 cli.py" $Yellow
    Write-Host ""
    Write-Host "💡 Tip: You can access your Windows files from WSL2 at /mnt/c/" $Blue
    Write-Host "💡 Tip: Use 'code .' in WSL2 to open VS Code with WSL2 integration" $Blue
}

# Main installation function
function Main {
    Write-Host "🪟 Fast.BI CLI Prerequisites Installer for Windows (WSL2)" $Blue
    Write-Host "========================================================" $Blue
    Write-Host ""
    
    Write-Log "Fast.BI CLI now requires WSL2 for Windows compatibility" $Blue
    Write-Log "This ensures consistent behavior across all platforms" $Blue
    Write-Host ""
    
    # Check if WSL2 is available
    if (Test-WSL2) {
        Write-Log "WSL2 detected, showing setup instructions..." $Blue
        Show-WSL2Instructions
    } else {
        Write-Log "WSL2 not found, installing WSL2 and Ubuntu..." $Blue
        Install-WSL2
    }
    
    # Show next steps
    Show-NextSteps
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
