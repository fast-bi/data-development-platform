# Fast.BI CLI Prerequisites Installation

This directory contains scripts to install all required tools and dependencies for the Fast.BI CLI on different operating systems.

## Required Tools

Based on the Fast.BI CLI requirements, the following tools need to be installed:

### Core Requirements
- **Python >=3.9**: For running the Fast.BI CLI
- **kubectl**: Kubernetes command-line tool
- **gcloud CLI**: Google Cloud command-line tool (required for authentication)
- **Terraform**: Infrastructure as Code tool for GCP resource management
- **Terragrunt**: Terraform wrapper for keeping configurations DRY
- **Helm**: Kubernetes package manager for deploying applications

### Additional Dependencies
- **Git**: For repository operations
- **Docker**: For container operations (optional but recommended)
- **jq**: JSON processor for configuration files
- **curl/wget**: For downloading tools

## Installation Methods

### Option 1: Automatic Installation (Recommended)
Run the main installer script for your platform:

**macOS/Linux:**
```bash
./install-prerequisites.sh
```

**Windows:**
```powershell
.\install-prerequisites.ps1
```

### Option 2: Manual Installation
Use the platform-specific scripts:

**macOS:**
```bash
./macos/install-macos.sh
```

**Linux:**
```bash
./linux/install-linux.sh
```

**Windows:**
```powershell
.\windows\install-windows.ps1
```

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

## Troubleshooting

### Common Issues

1. **Permission Denied**: Run with sudo (Linux/macOS) or as Administrator (Windows)
2. **Python Version**: Ensure Python 3.9+ is installed and in PATH
3. **Network Issues**: Check firewall and proxy settings
4. **Disk Space**: Ensure sufficient disk space for tool installations

### Platform-Specific Issues

#### macOS
- If Homebrew is not installed, the script will install it automatically
- For M1/M2 Macs, ensure Rosetta 2 is installed if needed

#### Linux
- Some distributions may require enabling additional repositories
- SELinux/AppArmor may need configuration for certain tools

#### Windows
- PowerShell execution policy may need to be set to RemoteSigned
- Chocolatey installation may require administrative privileges

## Manual Tool Installation

If automatic installation fails, you can install tools manually:

### Python
- **macOS**: Download from python.org or use Homebrew
- **Linux**: Use system package manager or download from python.org
- **Windows**: Download from python.org or use Chocolatey

### kubectl
```bash
# Download latest version
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

### gcloud CLI
```bash
# Download and install
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### Terraform
```bash
# Download and install
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs)"
sudo apt-get update && sudo apt-get install terraform
```

### Terragrunt
```bash
# Download and install
sudo curl -fsSL -o /usr/local/bin/terragrunt https://github.com/gruntwork-io/terragrunt/releases/download/v0.45.0/terragrunt_linux_amd64
sudo chmod +x /usr/local/bin/terragrunt
```

### Helm
```bash
# Download and install
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Configuration

After installation, some tools may require configuration:

### gcloud CLI
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### kubectl
```bash
# Configure context for your cluster
kubectl config set-cluster my-cluster --server=https://your-cluster-endpoint
kubectl config set-context my-context --cluster=my-cluster
kubectl config use-context my-context
```

### Terraform
```bash
# Initialize Terraform (when using in a project)
terraform init
```

## Updates

To update installed tools, run the installation script again. It will check for newer versions and update if available.

## Support

For issues with the prerequisites installation:

1. Check the troubleshooting section above
2. Review the platform-specific logs in the `logs/` directory
3. Ensure your system meets the minimum requirements
4. Check for platform-specific documentation in each subdirectory
