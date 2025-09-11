#!/bin/bash

# Fast.BI CLI Prerequisites Installer for Linux
# Installs all required tools based on detected distribution

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect Linux distribution
detect_distribution() {
    log "Detecting Linux distribution..."
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        local distro="$ID"
        local version="$VERSION_ID"
        log "Distribution: $distro $version"
        echo "$distro"
    elif command_exists lsb_release; then
        local distro=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        local version=$(lsb_release -sr)
        log "Distribution: $distro $version"
        echo "$distro"
    else
        warn "Could not detect distribution, assuming generic Linux"
        echo "linux"
    fi
}

# Function to check if running as root
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log "Running as root"
        return 0
    else
        warn "Some installations may require sudo privileges"
        warn "If you encounter permission errors, run with: sudo $0"
        return 1
    fi
}

# Function to update package manager
update_package_manager() {
    local distro=$1
    
    log "Updating package manager..."
    
    case $distro in
        "ubuntu"|"debian")
            sudo apt-get update
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            if command_exists dnf; then
                sudo dnf update -y
            else
                sudo yum update -y
            fi
            ;;
        "fedora")
            sudo dnf update -y
            ;;
        "amzn")
            sudo yum update -y
            ;;
        *)
            warn "Unknown distribution, skipping package manager update"
            ;;
    esac
    
    success "Package manager updated"
}

# Function to install Python
install_python() {
    log "Installing Python..."
    
    if command_exists python3; then
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        local major_version=$(echo "$python_version" | cut -d. -f1)
        local minor_version=$(echo "$python_version" | cut -d. -f2)
        
        if [[ $major_version -ge 3 ]] && [[ $minor_version -ge 9 ]]; then
            log "Python $python_version already installed (meets requirements)"
            return 0
        else
            warn "Python $python_version installed but doesn't meet requirements (need 3.9+)"
        fi
    fi
    
    local distro=$1
    
    case $distro in
        "ubuntu"|"debian")
            log "Installing Python 3.9+ via apt..."
            sudo apt-get install -y python3 python3-pip python3-venv
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            if command_exists dnf; then
                sudo dnf install -y python3 python3-pip python3-devel
            else
                sudo yum install -y python3 python3-pip python3-devel
            fi
            ;;
        "fedora")
            sudo dnf install -y python3 python3-pip python3-devel
            ;;
        "amzn")
            sudo yum install -y python3 python3-pip python3-devel
            ;;
        *)
            error "Unsupported distribution for Python installation: $distro"
            exit 1
            ;;
    esac
    
    # Verify installation
    if command_exists python3; then
        local new_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        success "Python $new_version installed successfully"
    else
        error "Python installation failed"
        exit 1
    fi
}

# Function to install kubectl
install_kubectl() {
    log "Installing kubectl..."
    
    if command_exists kubectl; then
        log "kubectl already installed"
        return 0
    fi
    
    # Download latest kubectl
    log "Downloading latest kubectl..."
    local kubectl_version=$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)
    local kubectl_url="https://storage.googleapis.com/kubernetes-release/release/${kubectl_version}/bin/linux/amd64/kubectl"
    
    curl -LO "$kubectl_url"
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/
    
    # Verify installation
    if command_exists kubectl; then
        local version=$(kubectl version --client --short 2>/dev/null || kubectl version --client 2>/dev/null)
        success "kubectl installed successfully: $version"
    else
        error "kubectl installation failed"
        exit 1
    fi
}

# Function to install gcloud CLI
install_gcloud() {
    log "Installing Google Cloud CLI..."
    
    if command_exists gcloud; then
        log "gcloud CLI already installed"
        return 0
    fi
    
    # Download and install gcloud CLI
    log "Downloading gcloud CLI..."
    curl https://sdk.cloud.google.com | bash
    
    # Add to PATH for current session
    source "$HOME/google-cloud-sdk/path.bash.inc"
    source "$HOME/google-cloud-sdk/completion.bash.inc"
    
    # Verify installation
    if command_exists gcloud; then
        local version=$(gcloud --version | head -n1)
        success "gcloud CLI installed successfully: $version"
    else
        error "gcloud CLI installation failed"
        exit 1
    fi
}

# Function to install Terraform
install_terraform() {
    log "Installing Terraform..."
    
    if command_exists terraform; then
        log "Terraform already installed"
        return 0
    fi
    
    local distro=$1
    
    case $distro in
        "ubuntu"|"debian")
            log "Installing Terraform via apt repository..."
            wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
            echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
            sudo apt-get update
            sudo apt-get install -y terraform
            ;;
        "centos"|"rhel"|"rocky"|"almalinux"|"fedora"|"amzn")
            log "Installing Terraform via yum/dnf repository..."
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
            if command_exists dnf; then
                sudo dnf install -y terraform
            else
                sudo yum install -y terraform
            fi
            ;;
        *)
            error "Unsupported distribution for Terraform installation: $distro"
            exit 1
            ;;
    esac
    
    # Verify installation
    if command_exists terraform; then
        local version=$(terraform --version | head -n1)
        success "Terraform installed successfully: $version"
    else
        error "Terraform installation failed"
        exit 1
    fi
}

# Function to install Terragrunt
install_terragrunt() {
    log "Installing Terragrunt..."
    
    if command_exists terragrunt; then
        log "Terragrunt already installed"
        return 0
    fi
    
    # Download specific Terragrunt version for consistency
    log "Downloading Terragrunt v0.84.0..."
    local terragrunt_version="v0.84.0"
    local terragrunt_url="https://github.com/gruntwork-io/terragrunt/releases/download/${terragrunt_version}/terragrunt_linux_amd64"
    
    curl -LO "$terragrunt_url"
    chmod +x terragrunt_linux_amd64
    sudo mv terragrunt_linux_amd64 /usr/local/bin/terragrunt
    
    # Verify installation
    if command_exists terragrunt; then
        local version=$(terragrunt --version | head -n1)
        success "Terragrunt installed successfully: $version"
    else
        error "Terragrunt installation failed"
        exit 1
    fi
}

# Function to install Helm
install_helm() {
    log "Installing Helm..."
    
    if command_exists helm; then
        log "Helm already installed"
        return 0
    fi
    
    # Download and install Helm
    log "Downloading Helm..."
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    
    # Verify installation
    if command_exists helm; then
        local version=$(helm version --short 2>/dev/null || helm version 2>/dev/null)
        success "Helm installed successfully: $version"
    else
        error "Helm installation failed"
        exit 1
    fi
}

# Function to install additional tools
install_additional_tools() {
    log "Installing additional tools..."
    
    local distro=$1
    
    # Install Git
    if ! command_exists git; then
        log "Installing Git..."
        case $distro in
            "ubuntu"|"debian")
                sudo apt-get install -y git
                ;;
            "centos"|"rhel"|"rocky"|"almalinux"|"fedora"|"amzn")
                if command_exists dnf; then
                    sudo dnf install -y git
                else
                    sudo yum install -y git
                fi
                ;;
        esac
        success "Git installed successfully"
    else
        log "Git already installed"
    fi
    
    # Install jq
    if ! command_exists jq; then
        log "Installing jq..."
        case $distro in
            "ubuntu"|"debian")
                sudo apt-get install -y jq
                ;;
            "centos"|"rhel"|"rocky"|"almalinux"|"fedora"|"amzn")
                if command_exists dnf; then
                    sudo dnf install -y jq
                else
                    sudo yum install -y jq
                fi
                ;;
        esac
        success "jq installed successfully"
    else
        log "jq already installed"
    fi
    
    # Install Docker (optional but recommended)
    if ! command_exists docker; then
        log "Installing Docker..."
        case $distro in
            "ubuntu"|"debian")
                sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
                curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
                echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
                sudo apt-get update
                sudo apt-get install -y docker-ce docker-ce-cli containerd.io
                sudo usermod -aG docker $USER
                ;;
            "centos"|"rhel"|"rocky"|"almalinux"|"fedora"|"amzn")
                if command_exists dnf; then
                    sudo dnf install -y docker
                else
                    sudo yum install -y docker
                fi
                sudo systemctl start docker
                sudo systemctl enable docker
                sudo usermod -aG docker $USER
                ;;
        esac
        success "Docker installed successfully"
        warn "Docker requires logout/login to work without sudo"
    else
        log "Docker already installed"
    fi
    
    # Install curl if not present
    if ! command_exists curl; then
        log "Installing curl..."
        case $distro in
            "ubuntu"|"debian")
                sudo apt-get install -y curl
                ;;
            "centos"|"rhel"|"rocky"|"almalinux"|"fedora"|"amzn")
                if command_exists dnf; then
                    sudo dnf install -y curl
                else
                    sudo yum install -y curl
                fi
                ;;
        esac
        success "curl installed successfully"
    else
        log "curl already installed"
    fi
}

# Function to configure shell profiles
configure_shell_profiles() {
    log "Configuring shell profiles..."
    
    local shell_profile=""
    
    # Determine shell and profile files
    case "$SHELL" in
        */zsh)
            shell_profile="$HOME/.zshrc"
            ;;
        */bash)
            shell_profile="$HOME/.bashrc"
            ;;
        *)
            warn "Unknown shell: $SHELL"
            return 0
            ;;
    esac
    
    # Add gcloud CLI to profile if not already there
    if [[ -f "$shell_profile" ]] && grep -q "google-cloud-sdk" "$shell_profile"; then
        log "gcloud CLI path already configured in $shell_profile"
    else
        log "Adding gcloud CLI to $shell_profile..."
        echo "" >> "$shell_profile"
        echo "# Google Cloud SDK" >> "$shell_profile"
        echo 'source "$HOME/google-cloud-sdk/path.bash.inc"' >> "$shell_profile"
        echo 'source "$HOME/google-cloud-sdk/completion.bash.inc"' >> "$shell_profile"
        success "gcloud CLI path added to $shell_profile"
    fi
    
    # Configure Terragrunt cache location to prevent long path issues
    if [[ -f "$shell_profile" ]] && grep -q "TERRAGRUNT_DOWNLOAD" "$shell_profile"; then
        log "Terragrunt cache location already configured in $shell_profile"
    else
        log "Adding Terragrunt cache configuration to $shell_profile..."
        echo "" >> "$shell_profile"
        echo "# Terragrunt cache configuration (prevents long path issues)" >> "$shell_profile"
        echo 'export TERRAGRUNT_DOWNLOAD="/tmp/terragrunt-cache"' >> "$shell_profile"
        success "Terragrunt cache location configured in $shell_profile"
    fi
    
    # Create the cache directory
    mkdir -p /tmp/terragrunt-cache
    success "Created Terragrunt cache directory: /tmp/terragrunt-cache"
    
    # Reload shell profile for current session
    if [[ -f "$shell_profile" ]]; then
        source "$shell_profile"
    fi
}

# Function to verify all installations
verify_installations() {
    log "Verifying all installations..."
    
    local tools=("python3" "kubectl" "gcloud" "terraform" "terragrunt" "helm" "git" "jq" "curl")
    local all_installed=true
    
    for tool in "${tools[@]}"; do
        if command_exists "$tool"; then
            success "✅ $tool: installed"
        else
            error "❌ $tool: not found"
            all_installed=false
        fi
    done
    
    if [[ "$all_installed" == true ]]; then
        success "All tools verified successfully!"
    else
        warn "Some tools may not be properly installed"
        return 1
    fi
}

# Function to show next steps
show_next_steps() {
    log "Installation completed! Next steps:"
    echo ""
    echo "🔧 Configure your tools:"
    echo "  1. gcloud auth login"
    echo "  2. gcloud config set project YOUR_PROJECT_ID"
    echo "  3. kubectl config set-cluster my-cluster --server=https://your-cluster-endpoint"
    echo ""
    echo "🚀 Start using Fast.BI CLI:"
    echo "  1. cd .."
    echo "  2. python3 cli.py"
    echo ""
    echo "📚 Documentation:"
    echo "  - CLI help: python3 cli.py --help"
    echo "  - Deployment guide: docs/"
    echo ""
    echo "⚠️  Note: You may need to restart your terminal or run 'source ~/.bashrc' (or ~/.zshrc)"
    echo "   to ensure all tools are in your PATH"
    echo ""
    echo "🐳 Docker users: You may need to logout and login again for Docker group permissions"
}

# Main installation function
main() {
    echo "🐧 Fast.BI CLI Prerequisites Installer for Linux"
    echo "================================================"
    echo ""
    
    # Detect distribution
    local distro=$(detect_distribution)
    
    # Check privileges
    check_privileges
    
    # Update package manager
    update_package_manager "$distro"
    
    # Install Python
    install_python "$distro"
    
    # Install kubectl
    install_kubectl
    
    # Install gcloud CLI
    install_gcloud
    
    # Install Terraform
    install_terraform "$distro"
    
    # Install Terragrunt
    install_terragrunt
    
    # Install Helm
    install_helm
    
    # Install additional tools
    install_additional_tools "$distro"
    
    # Configure shell profiles
    configure_shell_profiles
    
    # Verify installations
    verify_installations
    
    # Show next steps
    show_next_steps
}

# Handle script interruption
trap 'error "Installation interrupted"; exit 1' INT TERM

# Run main function
main "$@"
