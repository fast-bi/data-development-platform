# Fast.BI CLI Prerequisites Installer

This directory contains intelligent installation scripts that check what's already installed and only install missing components.

## Version Consistency

All tools are now standardized to use consistent versions across platforms to ensure identical behavior:


### Core Requirements
- **Python >=3.9**: For running the Fast.BI CLI
- **kubectl**: Kubernetes command-line tool
- **gcloud CLI**: Google Cloud command-line tool (required for authentication)
- **Terraform**: Infrastructure as Code tool for GCP resource management
- **Terragrunt v0.88.1**: Terraform wrapper for keeping configurations DRY (specific version required)

See `versions.yaml` for detailed version configuration and compatibility information.

## 🚀 Quick Start

### Option 1: Batch File (Recommended)
```cmd
install-prerequisites.bat
```

=======
**Windows (WSL2):**
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
=======
**Windows (WSL2):**

```powershell
# Run as Administrator
.\windows\install-windows.ps1
```

### Verify Installation
=======
## Windows Installation (WSL2)

**Important:** Fast.BI CLI now requires WSL2 (Windows Subsystem for Linux) for Windows compatibility. This ensures consistent behavior across all platforms and eliminates Windows-specific issues.

### WSL2 Installation Process:
1. **Automatic WSL2 Setup**: The installer will detect if WSL2 is installed
2. **Ubuntu Installation**: If WSL2 is not found, it will install WSL2 and Ubuntu automatically
3. **Setup Instructions**: After WSL2 is ready, you'll get instructions to complete setup in WSL2
4. **Linux Environment**: All tools are installed in the Ubuntu WSL2 environment
5. **Consistent Experience**: Same installation process as native Linux

### Why WSL2?
- ✅ **Eliminates Windows-specific issues** (PATH problems, line continuations, etc.)
- ✅ **Consistent behavior** across all platforms
- ✅ **Native Linux compatibility** for all tools
- ✅ **Better performance** than traditional virtualization
- ✅ **Easy file system access** between Windows and Linux

### Option 3: Individual Tool Installation
Use the individual tool installers in each platform directory.

## Platform Support

### macOS
- Supports both Intel and Apple Silicon (M1/M2) processors
- Uses Homebrew for package management
- Automatically detects architecture and installs appropriate versions

### Linux
- Supports Ubuntu 18.04+, CentOS 7+, RHEL 7+, and similar distributions
- Uses system package managers (apt, yum, dnf)
- Automatically detects distribution and uses appropriate commands

### Windows
- Supports Windows 10/11 and Windows Server 2016+
- Uses Chocolatey for package management
- Includes PowerShell execution policy configuration
- Provides both user and system-wide installation options

## Verification

After installation, run the verification script:

**macOS/Linux:**
```bash
./verify-prerequisites.sh
```

**Windows:**
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