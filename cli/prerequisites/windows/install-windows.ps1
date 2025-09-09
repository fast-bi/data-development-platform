# Fast.BI CLI Prerequisites Installer for Windows
# Installs all required tools using Chocolatey and other methods

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
    Write-Log "Installation completed! Next steps:" $Blue
    Write-Host ""
    Write-Host "🔧 Configure your tools:" $White
    Write-Host "  1. gcloud auth login" $White
    Write-Host "  2. gcloud config set project YOUR_PROJECT_ID" $White
    Write-Host "  3. kubectl config set-cluster my-cluster --server=https://your-cluster-endpoint" $White
    Write-Host ""
    Write-Host "🚀 Start using Fast.BI CLI:" $White
    Write-Host "  1. cd .." $White
    Write-Host "  2. python cli.py" $White
    Write-Host ""
    Write-Host "📚 Documentation:" $White
    Write-Host "  - CLI help: python cli.py --help" $White
    Write-Host "  - Deployment guide: docs/" $White
    Write-Host ""
    Write-Host "⚠️  Note: You may need to restart your terminal or PowerShell session" $Yellow
    Write-Host "   to ensure all tools are in your PATH" $Yellow
    Write-Host ""
    Write-Host "🐳 Docker users: Docker Desktop may need to be started manually" $Yellow
}

# Main installation function
function Main {
    Write-Host "🪟 Fast.BI CLI Prerequisites Installer for Windows" $Blue
    Write-Host "==================================================" $Blue
    Write-Host ""
    
    # Check Windows version
    Test-WindowsVersion
    
    # Check PowerShell version
    Test-PowerShellVersion
    
    # Set execution policy
    Set-ExecutionPolicy
    
    # Install Chocolatey
    Install-Chocolatey
    
    # Install Python
    Install-Python
    
    # Install kubectl
    Install-Kubectl
    
    # Install gcloud CLI
    Install-Gcloud
    
    # Install Terraform
    Install-Terraform
    
    # Install Terragrunt
    Install-Terragrunt
    
    # Install Helm
    Install-Helm
    
    # Install additional tools
    Install-AdditionalTools
    
    # Configure environment variables
    Set-EnvironmentVariables
    
    # Verify installations
    if (Test-Installations) {
        # Show next steps
        Show-NextSteps
    } else {
        Write-Error "Installation verification failed"
        exit 1
    }
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
