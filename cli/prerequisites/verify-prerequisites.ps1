# Fast.BI CLI Prerequisites Verification Script for Windows
# Verifies that all required tools are properly installed and accessible

#Requires -Version 5.1

# Set error action preference
$ErrorActionPreference = "Continue"

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

function Write-ErrorLog {
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

# Function to get command version
function Get-CommandVersion {
    param([string]$Command, [string]$VersionArg = "--version")
    
    try {
        $version = & $Command $VersionArg 2>&1 | Select-Object -First 1
        return $version
    }
    catch {
        return "Version check failed"
    }
}

# Function to verify tool installation
function Test-Tool {
    param(
        [string]$ToolName,
        [string]$Command = $ToolName,
        [string]$VersionArg = "--version"
    )
    
    Write-Log "Verifying $ToolName installation..." $Blue
    
    if (-not (Test-Command $Command)) {
        Write-ErrorLog "$ToolName not found in PATH"
        return $false
    }
    
    try {
        $version = Get-CommandVersion $Command $VersionArg
        Write-Success "$ToolName version: $version"
        return $true
    }
    catch {
        Write-ErrorLog "$ToolName command failed"
        return $false
    }
}

# Main verification function
function Main {
    Write-Host "Fast.BI CLI Prerequisites Verification" $Blue
    Write-Host "=====================================" $Blue
    Write-Host ""
    
    $allPassed = $true
    
    # Test core tools
    $tools = @(
        @{Name="Python"; Command="python"; VersionArg="--version"},
        @{Name="pip"; Command="pip"; VersionArg="--version"},
        @{Name="kubectl"; Command="kubectl"; VersionArg="version --client"},
        @{Name="gcloud"; Command="gcloud"; VersionArg="--version"},
        @{Name="terraform"; Command="terraform"; VersionArg="--version"},
        @{Name="terragrunt"; Command="terragrunt"; VersionArg="--version"},
        @{Name="helm"; Command="helm"; VersionArg="version"},
        @{Name="git"; Command="git"; VersionArg="--version"},
        @{Name="jq"; Command="jq"; VersionArg="--version"},
        @{Name="curl"; Command="curl"; VersionArg="--version"}
    )
    
    foreach ($tool in $tools) {
        if (-not (Test-Tool -ToolName $tool.Name -Command $tool.Command -VersionArg $tool.VersionArg)) {
            $allPassed = $false
        }
    }
    
    Write-Host ""
    Write-Host "=====================================" $Blue
    
    if ($allPassed) {
        Write-Success "All prerequisites verified successfully!"
        Write-Host ""
        Write-Host "You can now run the Fast.BI CLI:" $White
        Write-Host "  python cli.py --help" $White
        return $true
    } else {
        Write-ErrorLog "Some prerequisites failed verification"
        Write-Host ""
        Write-Host "Please run the installation script again:" $White
        Write-Host "  .\windows\install-windows.ps1" $White
        return $false
    }
}

# Run verification
try {
    $result = Main
    if ($result) {
        exit 0
    } else {
        exit 1
    }
}
catch {
    Write-ErrorLog "Verification failed"
    exit 1
}