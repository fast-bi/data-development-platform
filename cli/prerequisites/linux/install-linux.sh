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
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        local distro="$ID"
        local version="$VERSION_ID"
        echo "$distro"
    elif command_exists lsb_release; then
        local distro=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        local version=$(lsb_release -sr)
        echo "$distro"
    else
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

# Ensure 'python' and 'pip' commands are available (alias to Python 3)
ensure_python_shims() {
    log "Ensuring 'python' and 'pip' commands resolve to Python 3..."
    local distro=$1
    case $distro in
        "ubuntu"|"debian")
            # Prefer distro-provided shim if available
            if command_exists apt-get; then
                sudo apt-get install -y python-is-python3 || true
            fi
            ;;
    esac
    # Fallback symlinks if still missing
    if ! command_exists python && command_exists python3; then
        if [[ -w /usr/bin ]]; then
            sudo ln -sf "$(command -v python3)" /usr/bin/python
        else
            warn "/usr/bin not writable; skipping python shim"
        fi
    fi
    if ! command_exists pip && command_exists pip3; then
        if [[ -w /usr/bin ]]; then
            sudo ln -sf "$(command -v pip3)" /usr/bin/pip
        else
            warn "/usr/bin not writable; skipping pip shim"
        fi
    fi
    # Verify
    if command_exists python; then
        success "python -> $(python -V 2>&1)"
    else
        warn "'python' command still not available"
    fi
    if command_exists pip; then
        success "pip -> $(pip --version 2>&1)"
    else
        warn "'pip' command still not available"
    fi
}

# Function to install Python requirements
install_python_requirements() {
    log "Installing Python dependencies..."
    
    # Resolve repo root and requirements path
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local repo_root
    repo_root="$(cd "$script_dir/../../.." && pwd)"
    local requirements_file="$repo_root/cli/prerequisites/requirements.txt"
    
    if [[ ! -f "$requirements_file" ]]; then
        warn "requirements.txt not found at $requirements_file; skipping"
        return 0
    fi
    
    # Ensure pip present
    if ! python3 -m pip --version >/dev/null 2>&1; then
        warn "pip for Python3 not found; attempting to install"
        if command_exists apt-get; then
            sudo apt-get install -y python3-pip || true
        fi
    fi
    
    # Upgrade pip tooling (best effort)
    python3 -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
    
    # Install requirements - handle externally-managed-environment
    log "Installing Python packages from requirements.txt..."
    if [[ $EUID -eq 0 ]]; then
        python3 -m pip install --break-system-packages -r "$requirements_file"
    else
        python3 -m pip install --user --break-system-packages -r "$requirements_file"
    fi
    
    success "Python dependencies installed"
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
    
    local distro=$1
    case $distro in
        "ubuntu"|"debian")
            log "Installing gcloud via apt repository"
            sudo apt-get install -y apt-transport-https ca-certificates gnupg
            curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
            echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list > /dev/null
            sudo apt-get update
            sudo apt-get install -y google-cloud-cli
            ;;
        *)
            log "Installing gcloud to /opt via official installer (non-interactive)..."
            curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts --install-dir=/opt
            # Create symlinks for key commands
            for cmd in gcloud gsutil bq; do
                if [[ -f "/opt/google-cloud-sdk/bin/$cmd" ]]; then
                    sudo ln -sf "/opt/google-cloud-sdk/bin/$cmd" "/usr/local/bin/$cmd"
                fi
            done
            ;;
    esac
    
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
    log "Installing Terragrunt >= 0.84.0 (latest 0.84.x if install/upgrade needed)..."

    if command_exists terragrunt; then
        local current_version=$(terragrunt --version | head -n1)
        # Extract semantic version like X.Y.Z
        local current_semver=$(echo "$current_version" | sed -E 's/.*v?([0-9]+)\.([0-9]+)\.([0-9]+).*/\1.\2.\3/')
        local required_min="0.84.0"
        # Compare versions: return 0 if $1 >= $2
        version_ge() {
            local IFS=.
            local a=($1) b=($2)
            while [ ${#a[@]} -lt 3 ]; do a+=(0); done
            while [ ${#b[@]} -lt 3 ]; do b+=(0); done
            for i in 0 1 2; do
                if ((10#${a[i]} > 10#${b[i]})); then return 0; fi
                if ((10#${a[i]} < 10#${b[i]})); then return 1; fi
            done
            return 0
        }
        if version_ge "$current_semver" "$required_min"; then
            log "Terragrunt $current_semver already installed (>= $required_min)"
            return 0
        else
            warn "Terragrunt $current_semver installed, but >= $required_min is required"
            log "Updating Terragrunt..."
        fi
    fi

    # Determine latest 0.84.x version from GitHub tags without jq
    local minor_track="0.84"
    local latest_patch=$(curl -s "https://api.github.com/repos/gruntwork-io/terragrunt/tags?per_page=100" \
        | grep -o '"name":"v[0-9]\+\.[0-9]\+\.[0-9]\+"' \
        | sed -E 's/\"name\":\"v([0-9]+\.[0-9]+\.[0-9]+)\"/\1/' \
        | grep -E "^${minor_track}\\.[0-9]+$" \
        | sort -V \
        | tail -1)

    if [ -z "$latest_patch" ]; then
        warn "Could not resolve latest ${minor_track}.x version from GitHub; falling back to ${minor_track}.0"
        latest_patch="${minor_track}.0"
    fi

    local terragrunt_version="v${latest_patch}"

    # Detect CPU architecture for correct binary
    local arch=$(uname -m)
    local tg_binary_name=""
    if [[ "$arch" == "arm64" || "$arch" == "aarch64" ]]; then
        tg_binary_name="terragrunt_linux_arm64"
    else
        tg_binary_name="terragrunt_linux_amd64"
    fi

    log "Downloading Terragrunt ${terragrunt_version} (${tg_binary_name})..."
    local terragrunt_url="https://github.com/gruntwork-io/terragrunt/releases/download/${terragrunt_version}/${tg_binary_name}"

    curl -fL -o "$tg_binary_name" "$terragrunt_url"
    chmod +x "$tg_binary_name"
    sudo mv "$tg_binary_name" /usr/local/bin/terragrunt

    # Verify installation
    if command_exists terragrunt; then
        local version_line=$(terragrunt --version | head -n1)
        local installed_semver=$(echo "$version_line" | sed -E 's/.*v?([0-9]+)\.([0-9]+)\.([0-9]+).*/\1.\2.\3/')
        local required_min="0.84.0"
        version_ge() {
            local IFS=.
            local a=($1) b=($2)
            while [ ${#a[@]} -lt 3 ]; do a+=(0); done
            while [ ${#b[@]} -lt 3 ]; do b+=(0); done
            for i in 0 1 2; do
                if ((10#${a[i]} > 10#${b[i]})); then return 0; fi
                if ((10#${a[i]} < 10#${b[i]})); then return 1; fi
            done
            return 0
        }
        if version_ge "$installed_semver" "$required_min"; then
            success "Terragrunt installed successfully: $version_line (>= $required_min)"
        else
            error "Terragrunt version too low. Required >= $required_min, got: $version_line"
            exit 1
        fi
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
    
    # If gcloud already resolves on PATH, no profile edits needed
    if command_exists gcloud; then
        log "gcloud already on PATH; skipping profile configuration"
        return 0
    fi
    
    # Prefer system locations first
    local gcloud_path=""
    if [[ -d "/opt/google-cloud-sdk" ]]; then
        gcloud_path="/opt/google-cloud-sdk"
        log "Using /opt/google-cloud-sdk for PATH sourcing"
    elif [[ -d "/usr/lib/google-cloud-sdk" ]]; then
        gcloud_path="/usr/lib/google-cloud-sdk"
        log "Using /usr/lib/google-cloud-sdk for PATH sourcing"
    elif [[ -d "$HOME/google-cloud-sdk" ]]; then
        gcloud_path="$HOME/google-cloud-sdk"
        log "Using $HOME/google-cloud-sdk for PATH sourcing"
    elif [[ -d "/root/google-cloud-sdk" ]]; then
        # Do NOT write /root paths into user profiles; only use for system profile
        gcloud_path="/root/google-cloud-sdk"
        log "gcloud only found under /root; will configure system profile only"
    else
        warn "gcloud CLI installation not found for profile configuration"
        return 0
    fi
    
    # Get the actual user (not root if running with sudo)
    local actual_user="${SUDO_USER:-$USER}"
    local user_home="/home/$actual_user"
    if [[ "$actual_user" == "root" ]]; then
        user_home="$HOME"
    fi
    
    # Configure Terragrunt cache location to prevent long path issues
    if [[ -f "$shell_profile" ]] && grep -q "TG_DOWNLOAD_DIR" "$shell_profile"; then
        log "Terragrunt cache location already configured in $shell_profile"
    else
        log "Adding Terragrunt cache configuration to $shell_profile..."
        echo "" >> "$shell_profile"
        echo "# Terragrunt cache configuration (prevents long path issues)" >> "$shell_profile"
        echo 'export TG_DOWNLOAD_DIR="/tmp/terragrunt-cache"' >> "$shell_profile"
        success "Terragrunt cache location configured in $shell_profile"
    fi
    
    # Create the cache directory
    mkdir -p /tmp/terragrunt-cache
    success "Created Terragrunt cache directory: /tmp/terragrunt-cache"
    
    # Reload shell profile for current session
    if [[ -f "$shell_profile" ]]; then
        if grep -q "google-cloud-sdk" "$shell_profile"; then
            log "Cleaning stale google-cloud-sdk entries in $shell_profile (if any)"
            sed -i '\~google-cloud-sdk~d' "$shell_profile"
        fi
    fi
    
    # Only add user profile sourcing if not using apt (apt puts gcloud in /usr/bin)
    if ! command_exists gcloud; then
        if [[ -f "$gcloud_path/path.bash.inc" ]]; then
            log "Adding gcloud sourcing to $shell_profile"
            echo "" >> "$shell_profile"
            echo "# Google Cloud SDK" >> "$shell_profile"
            echo "source \"$gcloud_path/path.bash.inc\"" >> "$shell_profile"
            if [[ -f "$gcloud_path/completion.bash.inc" ]]; then
                echo "source \"$gcloud_path/completion.bash.inc\"" >> "$shell_profile"
            fi
        fi
    fi
    
    # System-wide profile for all users; safe to reference /opt or /usr/lib
    if [[ -f "/etc/profile.d/gcloud.sh" ]]; then
        log "System-wide gcloud profile already exists"
    else
        log "Creating system-wide gcloud profile at /etc/profile.d/gcloud.sh"
        sudo tee /etc/profile.d/gcloud.sh > /dev/null << EOF
# Google Cloud SDK - Global Configuration
if [ -f "/opt/google-cloud-sdk/path.bash.inc" ]; then
    . "/opt/google-cloud-sdk/path.bash.inc"
elif [ -f "/usr/lib/google-cloud-sdk/path.bash.inc" ]; then
    . "/usr/lib/google-cloud-sdk/path.bash.inc"
elif [ -f "$HOME/google-cloud-sdk/path.bash.inc" ]; then
    . "$HOME/google-cloud-sdk/path.bash.inc"
fi
if [ -f "/opt/google-cloud-sdk/completion.bash.inc" ]; then
    . "/opt/google-cloud-sdk/completion.bash.inc"
elif [ -f "/usr/lib/google-cloud-sdk/completion.bash.inc" ]; then
    . "/usr/lib/google-cloud-sdk/completion.bash.inc"
elif [ -f "$HOME/google-cloud-sdk/completion.bash.inc" ]; then
    . "$HOME/google-cloud-sdk/completion.bash.inc"
fi
EOF
        success "System-wide gcloud CLI profile created"
    fi
    
    # Also add to /etc/bash.bashrc (idempotent)
    if ! grep -q "google-cloud-sdk" /etc/bash.bashrc; then
        log "Adding gcloud sourcing to /etc/bash.bashrc"
        echo "" | sudo tee -a /etc/bash.bashrc > /dev/null
        echo "# Google Cloud SDK" | sudo tee -a /etc/bash.bashrc > /dev/null
        echo "[ -f /etc/profile.d/gcloud.sh ] && . /etc/profile.d/gcloud.sh" | sudo tee -a /etc/bash.bashrc > /dev/null
        success "gcloud sourcing added to /etc/bash.bashrc"
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
    echo "⚠️  Important PATH Notes:"
    echo "  - gcloud CLI has been configured globally for all users"
    echo "  - Added to: /etc/profile.d/gcloud.sh and /etc/bash.bashrc"
    echo "  - You may need to restart your terminal or run:"
    echo "    source /etc/profile.d/gcloud.sh"
    echo "  - Or start a new terminal session"
    echo "  - gcloud CLI is now accessible from any user account"
    echo ""
    echo "🐳 Docker users: You may need to logout and login again for Docker group permissions"
}

# Main installation function
main() {
    echo "🐧 Fast.BI CLI Prerequisites Installer for Linux"
    echo "================================================"
    echo ""
    
    # Detect distribution
    log "Detecting Linux distribution..."
    local distro=$(detect_distribution)
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        log "Distribution: $ID $VERSION_ID"
    elif command_exists lsb_release; then
        local version=$(lsb_release -sr)
        log "Distribution: $distro $version"
    else
        log "Distribution: $distro (generic Linux)"
    fi
    
    # Check privileges
    check_privileges
    
    # Update package manager
    update_package_manager "$distro"
    
    # Install Python
    install_python "$distro"
    # Ensure python/pip shims
    ensure_python_shims "$distro"
    
    # Install kubectl
    install_kubectl
    
    # Install gcloud CLI
    install_gcloud "$distro"
    
    # Install Terraform
    install_terraform "$distro"
    
    # Install Terragrunt
    install_terragrunt
    
    # Install Helm
    install_helm
    
    # Install additional tools
    install_additional_tools "$distro"
    
    # Install Python requirements
    install_python_requirements
    
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
