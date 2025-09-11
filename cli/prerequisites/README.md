# Fast.BI CLI Prerequisites Installer

This directory contains intelligent installation scripts that check what's already installed and only install missing components.

## Version Consistency

All tools are now standardized to use consistent versions across platforms to ensure identical behavior:

- **Terragrunt**: v0.84.0 (standardized across Windows, Linux, macOS, and Docker)
- **Terraform**: Latest stable version
- **Helm**: Latest stable version  
- **kubectl**: Latest stable version

See `versions.yaml` for detailed version configuration and compatibility information.

## 🚀 Quick Start

### Option 1: Batch File (Recommended)
```cmd
install-prerequisites.bat
```

### Option 2: PowerShell Script (Windows)
```powershell
.\windows\install-windows.ps1
```

## 📋 What Gets Installed

The installer intelligently checks and installs:

- **Python 3.11+** (with Microsoft Store aliases disabled)
- **kubectl** (Kubernetes CLI)
- **gcloud CLI** (Google Cloud CLI with fallback installation)
- **Terraform** (Infrastructure as Code)
- **Terragrunt** (Terraform wrapper)
- **Helm** (Kubernetes package manager)
- **Git** (Version control)
- **jq** (JSON processor)
- **curl** (HTTP client)
- **Docker Desktop** (Container platform - optional)

## 🔍 Features

### Intelligent Installation
- ✅ **Checks existing installations** - Only installs what's missing
- ✅ **Version verification** - Ensures minimum required versions
- ✅ **Microsoft Store alias handling** - Automatically disables problematic Python aliases
- ✅ **Fallback installation methods** - Multiple installation strategies for reliability
- ✅ **Comprehensive logging** - Detailed logs saved to `logs/` directory
- ✅ **Error resilience** - Continues installation even if some tools fail

### Smart Detection
- Detects already installed tools and their versions
- Skips installation if tool meets requirements
- Handles version conflicts and updates
- Manages environment variables automatically

## 📁 Files

- `install-prerequisites.bat` - Windows batch file wrapper
- `verify-prerequisites.ps1` - Verification script (Windows)
- `windows/install-windows.ps1` - Windows installer
- `install-prerequisites.sh` - Linux/macOS entrypoint
- `linux/` - Linux installer scripts (if present)
- `macos/` - macOS installer scripts (if present)
- `logs/` - Installation logs directory

## 🔧 Usage Examples

### Run Complete Installation (Windows)
```powershell
# Run as Administrator
.\windows\install-windows.ps1
```

### Verify Installation
```powershell
.\verify-prerequisites.ps1
```

### Linux/macOS
```bash
chmod +x install-prerequisites.sh
./install-prerequisites.sh
```

## 📊 Installation Logs

All installations are logged to the `logs/` directory with timestamps:
- `logs/install-YYYYMMDD-HHMMSS.log`

## ⚠️ Requirements

- **Windows 10/11** or Windows Server 2016+
- **PowerShell 5.1** or later
- **Administrator privileges**
- **Internet connection**

## 🎯 After Installation

1. **Restart your terminal/PowerShell session**
2. **Configure cloud provider credentials**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **Run the Fast.BI CLI**:
   ```bash
   python cli.py --help
   ```

## 🐛 Troubleshooting

### Common Issues

1. **Python Microsoft Store aliases**
   - The installer automatically handles this
   - If issues persist, manually disable in Windows Settings > Apps > Advanced app settings > App execution aliases

2. **gcloud CLI installation fails**
   - The installer has a fallback method
   - If both fail, install manually from: https://cloud.google.com/sdk/docs/install

3. **Tools not found after installation**
   - Restart your terminal/PowerShell session
   - Run `refreshenv` in PowerShell
   - Check the installation logs in `logs/` directory

### Getting Help

- Check installation logs in `logs/` directory
- Run verification script: `.\verify-prerequisites.ps1`
- Ensure you're running as Administrator
- Verify internet connection and disk space

## 🔄 Re-running Installation

The installer is safe to run multiple times:
- Skips already installed tools
- Updates tools if newer versions are available
- Only installs missing components
- Preserves existing configurations