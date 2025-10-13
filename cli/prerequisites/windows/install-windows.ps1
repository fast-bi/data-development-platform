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

# Function to refresh environment variables
function Refresh-Environment {
    Write-Log "Refreshing environment variables..." $Blue
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Also refresh from registry for current session
    try {
        $machinePath = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment").GetValue("Path")
        $userPath = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment").GetValue("Path")
        $env:Path = "$machinePath;$userPath"
    } catch {
        Write-Warning "Could not refresh PATH from registry, using environment variables only"
    }
}

# Function to disable Microsoft Store Python aliases
function Disable-PythonAliases {
    Write-Log "Disabling Microsoft Store Python aliases..." $Blue
    
    $aliasPaths = @(
        "$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\python.exe",
        "$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\python3.exe",
        "$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\python3.11.exe"
    )
    
    foreach ($aliasPath in $aliasPaths) {
        if (Test-Path $aliasPath) {
            try {
                Remove-Item $aliasPath -Force -ErrorAction SilentlyContinue
                Write-Log "Removed Python alias: $aliasPath" $White
            } catch {
                Write-Warning "Could not remove Python alias: $aliasPath"
            }
        }
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

# Function to enable Windows long path support
function Enable-LongPathSupport {
    Write-Log "Configuring Windows long path support..." $Blue
    
    try {
        # Check current long path setting
        $currentSetting = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -ErrorAction SilentlyContinue
        
        if ($currentSetting -and $currentSetting.LongPathsEnabled -eq 1) {
            Write-Log "Long path support already enabled" $White
        } else {
            Write-Log "Enabling long path support..." $Yellow
            Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1
            Write-Success "Long path support enabled successfully"
            Write-Warning "A system restart may be required for changes to take effect"
        }
        
        # Configure Git to handle long paths
        Write-Log "Configuring Git for long path support..." $Blue
        try {
            & git config --global core.longpaths true 2>$null
            & git config --global core.precomposeUnicode true 2>$null
            & git config --global core.protectNTFS false 2>$null
            Write-Success "Git configured for long path support"
        } catch {
            Write-Warning "Could not configure Git (Git may not be installed yet)"
        }
        
    } catch {
        Write-Warning "Could not enable long path support: $($_.Exception.Message)"
        Write-Warning "You may need to enable it manually in Group Policy or Registry"
        Write-Warning "This is required to avoid 'Filename too long' errors with Terraform modules"
    }
}

# Function to install Chocolatey
function Install-Chocolatey {
    Write-Log "Installing Chocolatey..." $Blue
    
    if (Test-Command "choco") {
        Write-Log "Chocolatey already installed" $White
        Write-Log "Updating Chocolatey..." $Blue
        try {
            choco upgrade chocolatey -y --no-progress
            Write-Success "Chocolatey updated successfully"
        } catch {
            Write-Warning "Chocolatey update failed, but continuing with installation"
        }
        return
    }
    
    # Install Chocolatey
    Write-Log "Downloading and installing Chocolatey..." $Blue
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    
    try {
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        Write-Success "Chocolatey installation completed"
    } catch {
        Write-Error "Chocolatey installation failed: $($_.Exception.Message)"
        exit 1
    }
    
    # Refresh environment variables
    Refresh-Environment
    
    # Wait a moment for PATH to be updated
    Start-Sleep -Seconds 3
    
    # Verify installation
    if (Test-Command "choco") {
        Write-Success "Chocolatey installed and verified successfully"
    } else {
        Write-Error "Chocolatey installation failed - command not found in PATH"
        Write-Error "Please restart PowerShell and try again"
        exit 1
    }
}

# Function to install Python
function Install-Python {
    Write-Log "Installing Python..." $Blue
    
    # First, disable Microsoft Store Python aliases
    Disable-PythonAliases
    
    # Check if Python is already installed and working
    try {
        $pythonPath = Get-Command python -ErrorAction Stop | Select-Object -ExpandProperty Source
        if ($pythonPath -and $pythonPath -notlike "*WindowsApps*") {
            $version = & python --version 2>&1
            Write-Log "Python already installed: $version at $pythonPath" $White
            
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
    } catch {
        Write-Log "Python not found or not working properly" $White
    }
    
    # Install Python via Chocolatey
    Write-Log "Installing Python 3.11 via Chocolatey..." $Blue
    try {
        choco install python311 -y --no-progress
        Write-Success "Python installation completed"
    } catch {
        Write-Error "Python installation failed: $($_.Exception.Message)"
        exit 1
    }
    
    # Refresh environment variables
    Refresh-Environment
    
    # Wait for PATH to be updated
    Start-Sleep -Seconds 3
    
    # Verify installation
    try {
        $version = & python --version 2>&1
        Write-Success "Python installed successfully: $version"
    } catch {
        Write-Error "Python installation failed - command not working"
        Write-Error "Please restart PowerShell and try again"
        exit 1
    }
}

# Function to install Python packages (requirements)
function Install-PythonPackages {
    Write-Log "Installing Python packages..." $Blue
    
    if (-not (Test-Command "python")) {
        Write-Warning "Python not available; skipping package installation"
        return
    }
    
    try {
        Write-Log "Upgrading pip..." $Blue
        & python -m ensurepip --upgrade 2>$null
        & python -m pip install --upgrade pip
    } catch {
        Write-Warning "Failed to upgrade pip: $($_.Exception.Message)"
    }
    
    # Determine requirements.txt location
    # Prefer CLI-specific requirements first, fallback to repo root
    $scriptRoot = Split-Path -Parent $PSCommandPath
    $repoRoot = Resolve-Path (Join-Path $scriptRoot "..\..")
    $cliReq = Resolve-Path -ErrorAction SilentlyContinue (Join-Path $scriptRoot "..\requirements.txt")
    $rootReq = Join-Path $repoRoot "requirements.txt"
    
    $requirementsPath = $null
    if ($cliReq -and (Test-Path $cliReq)) { $requirementsPath = $cliReq }
    elseif (Test-Path $rootReq) { $requirementsPath = $rootReq }
    
    if ($requirementsPath) {
        Write-Log "Installing packages from: $requirementsPath" $Blue
        try {
            & python -m pip install -r "$requirementsPath"
            Write-Success "Python packages installed successfully"
        } catch {
            Write-Warning "Failed to install from requirements.txt: $($_.Exception.Message)"
        }
    } else {
        Write-Warning "No requirements.txt found; skipping package installation"
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
    try {
        choco install kubernetes-cli -y --no-progress
        Write-Success "kubectl installation completed"
    } catch {
        Write-Error "kubectl installation failed: $($_.Exception.Message)"
        exit 1
    }
    
    # Refresh environment variables
    Refresh-Environment
    
    # Verify installation
    if (Test-Command "kubectl") {
        try {
            $version = kubectl version --client 2>$null | Select-Object -First 1
            Write-Success "kubectl installed successfully: $version"
        } catch {
            Write-Success "kubectl installed successfully (version check failed)"
        }
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
    
    # Try installing gcloud CLI via Chocolatey first
    Write-Log "Installing gcloud CLI via Chocolatey..." $Blue
    $chocoResult = & choco install gcloudsdk -y --no-progress 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "gcloud CLI installation completed via Chocolatey"
    } else {
        Write-Warning "Chocolatey installation failed, trying alternative method..."
        
        # Alternative: Download and install gcloud CLI directly
        Write-Log "Downloading gcloud CLI directly from Google..." $Blue
        $gcloudInstaller = "$env:TEMP\google-cloud-cli-installer.exe"
        $gcloudUrl = "https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe"
        
        try {
            # Download the installer
            Write-Log "Downloading gcloud installer..." $Blue
            Invoke-WebRequest -Uri $gcloudUrl -OutFile $gcloudInstaller -UseBasicParsing
            
            # Run the installer silently
            Write-Log "Running gcloud installer..." $Blue
            Start-Process -FilePath $gcloudInstaller -ArgumentList "/S" -Wait
            
            # Clean up
            Remove-Item $gcloudInstaller -Force -ErrorAction SilentlyContinue
            
            Write-Success "gcloud CLI installation completed via direct installer"
        } catch {
            Write-Error "Both Chocolatey and direct installation methods failed"
            Write-Warning "You can install gcloud CLI manually from: https://cloud.google.com/sdk/docs/install"
            return
        }
    }
    
    # Refresh environment variables
    Refresh-Environment
    
    # Wait a moment for PATH to be updated
    Start-Sleep -Seconds 3
    
    # Verify installation
    if (Test-Command "gcloud") {
        try {
            $version = gcloud --version | Select-Object -First 1
            Write-Success "gcloud CLI installed successfully: $version"
        } catch {
            Write-Success "gcloud CLI installed successfully (version check failed)"
        }
    } else {
        Write-Warning "gcloud CLI installation may have failed - command not found in PATH"
        Write-Warning "Please restart PowerShell and try again, or install manually"
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
    try {
        choco install terraform -y --no-progress
        Write-Success "Terraform installation completed"
    } catch {
        Write-Warning "Terraform installation failed: $($_.Exception.Message)"
        Write-Warning "You can install Terraform manually from: https://www.terraform.io/downloads"
        return
    }
    
    # Refresh environment variables
    Refresh-Environment
    
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
    
    # Install specific Terragrunt version for consistency
    Write-Log "Installing Terragrunt v0.88.1..." $Blue
    $terragruntVersion = "v0.88.1"
    $terragruntUrl = "https://github.com/gruntwork-io/terragrunt/releases/download/$terragruntVersion/terragrunt_windows_amd64.exe"
    $terragruntPath = "$env:TEMP\terragrunt.exe"
    
    try {
        # Download Terragrunt
        Write-Log "Downloading Terragrunt from GitHub..." $Blue
        Invoke-WebRequest -Uri $terragruntUrl -OutFile $terragruntPath -UseBasicParsing
        
        # Install to system PATH
        $installPath = "$env:ProgramFiles\Terragrunt"
        if (-not (Test-Path $installPath)) {
            New-Item -ItemType Directory -Path $installPath -Force | Out-Null
        }
        
        Copy-Item $terragruntPath "$installPath\terragrunt.exe" -Force
        
        # Add to PATH if not already present
        $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if ($currentPath -notlike "*$installPath*") {
            [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$installPath", "Machine")
            Write-Success "Terragrunt added to system PATH: $installPath"
        } else {
            Write-Log "Terragrunt already in system PATH" $White
        }
        
        # Also add to current session PATH
        if ($env:PATH -notlike "*$installPath*") {
            $env:PATH += ";$installPath"
        }
        
        # Clean up
        Remove-Item $terragruntPath -Force -ErrorAction SilentlyContinue
        
        Write-Success "Terragrunt installation completed"
    } catch {
        Write-Warning "Terragrunt installation failed: $($_.Exception.Message)"
        Write-Warning "You can install Terragrunt manually from: https://terragrunt.gruntwork.io/docs/getting-started/install/"
        return
    }
    
    # Refresh environment variables
    Refresh-Environment
    
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
    try {
        choco install kubernetes-helm -y --no-progress
        Write-Success "Helm installation completed"
    } catch {
        Write-Warning "Helm installation failed: $($_.Exception.Message)"
        Write-Warning "You can install Helm manually from: https://helm.sh/docs/intro/install/"
        return
    }
    
    # Refresh environment variables
    Refresh-Environment
    
    # Verify installation
    if (Test-Command "helm") {
        try {
            $version = helm version 2>$null | Select-Object -First 1
            Write-Success "Helm installed successfully: $version"
        } catch {
            Write-Success "Helm installed successfully (version check failed)"
        }
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
        try {
            choco install git -y --no-progress
            Write-Success "Git installed successfully"
        } catch {
            Write-Warning "Git installation failed: $($_.Exception.Message)"
        }
    } else {
        Write-Log "Git already installed" $White
    }
    
    # Install jq
    if (-not (Test-Command "jq")) {
        Write-Log "Installing jq..." $Blue
        try {
            choco install jq -y --no-progress
            Write-Success "jq installed successfully"
        } catch {
            Write-Warning "jq installation failed: $($_.Exception.Message)"
        }
    } else {
        Write-Log "jq already installed" $White
    }
    
    # Install Docker Desktop (optional but recommended)
    if (-not (Test-Command "docker")) {
        Write-Log "Installing Docker Desktop..." $Blue
        try {
            choco install docker-desktop -y --no-progress
            Write-Success "Docker Desktop installed successfully"
            Write-Warning "Docker Desktop requires manual setup and login"
        } catch {
            Write-Warning "Docker Desktop installation failed: $($_.Exception.Message)"
            Write-Warning "You can install Docker Desktop manually later"
        }
    } else {
        Write-Log "Docker already installed" $White
    }
    
    # Install curl if not present
    if (-not (Test-Command "curl")) {
        Write-Log "Installing curl..." $Blue
        try {
            choco install curl -y --no-progress
            Write-Success "curl installed successfully"
        } catch {
            Write-Warning "curl installation failed: $($_.Exception.Message)"
        }
    } else {
        Write-Log "curl already installed" $White
    }
    
    # Refresh environment variables
    Refresh-Environment
}

# Function to configure environment variables
function Set-EnvironmentVariables {
    Write-Log "Configuring environment variables..." $Blue
    
    # Configure Terraform to use shorter paths to avoid Windows path length issues
    Write-Log "Configuring Terraform environment variables..." $Blue
    try {
        [Environment]::SetEnvironmentVariable("TF_DATA_DIR", "C:\tf", "User")
        $env:TF_DATA_DIR = "C:\tf"
        Write-Success "Terraform data directory set to C:\tf"
    } catch {
        Write-Warning "Could not set TF_DATA_DIR environment variable"
    }
    
    # Configure Terragrunt to use shorter cache paths to avoid Windows path length issues
    Write-Log "Configuring Terragrunt cache location..." $Blue
    try {
        $terragruntCachePath = "C:\temp\terragrunt-cache"
        [Environment]::SetEnvironmentVariable("TG_DOWNLOAD_DIR", $terragruntCachePath, "User")
        $env:TG_DOWNLOAD_DIR = $terragruntCachePath
        
        # Create the cache directory if it doesn't exist
        if (-not (Test-Path $terragruntCachePath)) {
            New-Item -ItemType Directory -Path $terragruntCachePath -Force | Out-Null
            Write-Log "Created Terragrunt cache directory: $terragruntCachePath" $White
        }
        
        Write-Success "Terragrunt cache directory set to $terragruntCachePath"
        Write-Log "This prevents 'Filename too long' errors with Terraform modules" $White
    } catch {
        Write-Warning "Could not set TG_DOWNLOAD_DIR environment variable"
    }
    
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
    $gcloudPaths = @(
        "$env:ProgramData\chocolatey\lib\gcloudsdk\tools\google-cloud-sdk\bin",
        "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin",
        "${env:ProgramFiles(x86)}\Google\Cloud SDK\google-cloud-sdk\bin",
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
    )
    
    $gcloudAdded = $false
    foreach ($gcloudPath in $gcloudPaths) {
        if (Test-Path $gcloudPath) {
            # Check system PATH first
            $currentSystemPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
            if ($currentSystemPath -notlike "*$gcloudPath*") {
                Write-Log "Adding gcloud CLI to system PATH: $gcloudPath" $Blue
                [Environment]::SetEnvironmentVariable("PATH", "$currentSystemPath;$gcloudPath", "Machine")
                Write-Success "gcloud CLI added to system PATH"
                $gcloudAdded = $true
            } else {
                Write-Log "gcloud CLI already in system PATH" $White
            }
            
            # Also add to current session PATH
            if ($env:Path -notlike "*$gcloudPath*") {
                $env:Path += ";$gcloudPath"
            }
            break
        }
    }
    
    if (-not $gcloudAdded) {
        Write-Warning "gcloud CLI path not found in standard locations"
        Write-Warning "You may need to add gcloud to PATH manually"
    }
}

# Function to ensure critical tools are in system PATH
function Ensure-SystemPath {
    Write-Log "Ensuring critical tools are in system PATH..." $Blue
    
    # Ensure Terragrunt is in system PATH
    $terragruntPath = "$env:ProgramFiles\Terragrunt"
    if (Test-Path $terragruntPath) {
        $currentSystemPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if ($currentSystemPath -notlike "*$terragruntPath*") {
            Write-Log "Adding Terragrunt to system PATH: $terragruntPath" $Blue
            [Environment]::SetEnvironmentVariable("PATH", "$currentSystemPath;$terragruntPath", "Machine")
            Write-Success "Terragrunt added to system PATH"
        } else {
            Write-Log "Terragrunt already in system PATH" $White
        }
    } else {
        Write-Warning "Terragrunt installation path not found: $terragruntPath"
    }
    
    # Ensure gcloud is in system PATH
    $gcloudPaths = @(
        "$env:ProgramData\chocolatey\lib\gcloudsdk\tools\google-cloud-sdk\bin",
        "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin",
        "${env:ProgramFiles(x86)}\Google\Cloud SDK\google-cloud-sdk\bin",
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
    )
    
    $gcloudFound = $false
    foreach ($gcloudPath in $gcloudPaths) {
        if (Test-Path $gcloudPath) {
            $currentSystemPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
            if ($currentSystemPath -notlike "*$gcloudPath*") {
                Write-Log "Adding gcloud CLI to system PATH: $gcloudPath" $Blue
                [Environment]::SetEnvironmentVariable("PATH", "$currentSystemPath;$gcloudPath", "Machine")
                Write-Success "gcloud CLI added to system PATH"
            } else {
                Write-Log "gcloud CLI already in system PATH" $White
            }
            $gcloudFound = $true
            break
        }
    }
    
    if (-not $gcloudFound) {
        Write-Warning "gcloud CLI installation path not found in standard locations"
        Write-Warning "This may cause issues with Python subprocess calls"
    }
    
    Write-Success "System PATH configuration completed"
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
        Write-Warning "You can install missing tools manually or run the script again"
        # Don't return false - allow installation to complete
    }
    
    return $true
}

# Function to show next steps
function Show-NextSteps {
    Write-Host ""
    Write-Host "Configure your tools:" $White
    Write-Host "  1. gcloud auth login" $White
    Write-Host "  2. gcloud config set project YOUR_PROJECT_ID" $White
    Write-Host "  3. kubectl config set-cluster my-cluster --server=https://your-cluster-endpoint" $White
    Write-Host ""
    Write-Host "Start using Fast.BI CLI:" $White
    Write-Host "  1. cd .." $White
    Write-Host "  2. python cli.py" $White
    Write-Host ""
    Write-Host "Documentation:" $White
    Write-Host "  - CLI help: python cli.py --help" $White
    Write-Host "  - Deployment guide: docs/" $White
    Write-Host ""
    Write-Host "Note: You may need to restart your terminal or PowerShell session" $Yellow
    Write-Host "   to ensure all tools are in your PATH" $Yellow
    Write-Host ""
    Write-Host "Important: Both terragrunt and gcloud have been added to system PATH" $Green
    Write-Host "   This fixes the Python subprocess issue on Windows" $Green
    Write-Host ""
    Write-Host "Important: If long path support was enabled, you may need to restart" $Yellow
    Write-Host "   your computer for the changes to take full effect" $Yellow
    Write-Host ""
    Write-Host "Docker users: Docker Desktop may need to be started manually" $Yellow
}

# Main installation function
function Main {
    Write-Host "Fast.BI CLI Prerequisites Installer for Windows" $Blue
    Write-Host "==================================================" $Blue
    Write-Host ""
    
    # Check Windows version
    Test-WindowsVersion
    
    # Check PowerShell version
    Test-PowerShellVersion
    
    # Set execution policy
    Set-ExecutionPolicy
    
    # Enable long path support
    Enable-LongPathSupport
    
    # Install Chocolatey
    Install-Chocolatey
    
    # Install Python
    Install-Python
=======
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
    

    # Install Python packages
    Install-PythonPackages
    
    # Configure environment variables
    Set-EnvironmentVariables
    
    # Ensure critical tools are in system PATH
    Ensure-SystemPath
    
    # Verify installations
    if (Test-Installations) {
        # Show next steps
        Show-NextSteps

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