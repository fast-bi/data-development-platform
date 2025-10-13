#!/usr/bin/env zsh#

# Fast.BI CLI Prerequisites Installer for macOS
# Installs all required tools using Homebrew and other methods

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

# Function to check macOS version
check_macos_version() {
    log "Checking macOS version..."
    
    local macos_version=$(sw_vers -productVersion)
    local major_version=$(echo "$macos_version" | cut -d. -f1)
    local minor_version=$(echo "$macos_version" | cut -d. -f2)
    
    log "macOS version: $macos_version"
    
    if [[ $major_version -lt 10 ]] || ([[ $major_version -eq 10 ]] && [ $minor_version -lt 14 ]); then
        error "macOS 10.14 (Mojave) or later is required"
        error "Current version: $macos_version"
        exit 1
    fi
    
    success "macOS version check passed"
}

# Function to check architecture
check_architecture() {
    log "Checking system architecture..."
    
    local arch=$(uname -m)
    log "Architecture: $arch"
    
    if [[ "$arch" == "arm64" ]]; then
        log "Apple Silicon (M1/M2) detected"
        # Check if Rosetta 2 is installed
        if ! command_exists arch; then
            warn "Rosetta 2 not detected. Some tools may need it for x86_64 compatibility."
            read -p "Install Rosetta 2? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                log "Installing Rosetta 2..."
                softwareupdate --install-rosetta --agree-to-license
                success "Rosetta 2 installed"
            fi
        fi
    elif [[ "$arch" == "x86_64" ]]; then
        log "Intel processor detected"
    else
        warn "Unknown architecture: $arch"
    fi
}

# Function to install Homebrew
install_homebrew() {
    if command_exists brew; then
        log "Homebrew already installed"
        log "Updating Homebrew..."
        brew update
        return 0
    fi
    
    log "Installing Homebrew..."
    
    # Install Homebrew
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for current session
    if [[ "$(uname -m)" == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    # Verify installation
    if command_exists brew; then
        success "Homebrew installed successfully"
    else
        error "Homebrew installation failed"
        exit 1
    fi
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
    
    # Install Python 3.9+ via Homebrew
    log "Installing Python 3.9+ via Homebrew..."
    brew install python@3.11
    
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
    # On macOS with Homebrew, python3 is installed; create shims if missing
    if ! command_exists python && command_exists python3; then
        sudo ln -sf "$(command -v python3)" /usr/local/bin/python || true
        sudo ln -sf "$(command -v python3)" /opt/homebrew/bin/python || true
    fi
    if ! command_exists pip && command_exists pip3; then
        sudo ln -sf "$(command -v pip3)" /usr/local/bin/pip || true
        sudo ln -sf "$(command -v pip3)" /opt/homebrew/bin/pip || true
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
    # Resolve requirements path: prefer git root, fallback to local path
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local requirements_file=""
    if command -v git >/dev/null 2>&1; then
        local git_root
        git_root="$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null || echo "")"
        if [[ -n "$git_root" && -f "$git_root/cli/prerequisites/requirements.txt" ]]; then
            requirements_file="$git_root/cli/prerequisites/requirements.txt"
        fi
    fi
    if [[ -z "$requirements_file" ]]; then
        requirements_file="$script_dir/../requirements.txt"
    fi
    
    if [[ ! -f "$requirements_file" ]]; then
        warn "requirements.txt not found at $requirements_file; skipping"
        return 0
    fi
    
    # Ensure pip present
    if ! python3 -m pip --version >/dev/null 2>&1; then
        warn "pip for Python3 not found; attempting to install via Homebrew python"
        brew install python@3.11 || true
    fi
    
    # Upgrade pip tooling (best effort)
    python3 -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
    
    # Set pip defaults to avoid silent hangs and reduce noise
    export PIP_DEFAULT_TIMEOUT=60
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    
    # Proactively remove any already-installed conflicting packages from the user site
    log "Cleaning previously installed packages listed in requirements.txt (user site)..."
    # Extract base package names from requirements (strip version specifiers and comments)
    local pkgs
    pkgs=$(grep -E '^[A-Za-z0-9_.-]+' "$requirements_file" | sed 's/[[:space:]]#.*$//' | sed 's/[<>=!~].*$//' | sed 's/[[:space:]]//g' | sort -u)
    for pkg in $pkgs; do
        if python3 -m pip show "$pkg" >/dev/null 2>&1; then
            log "Uninstalling existing $pkg from user site..."
            python3 -m pip uninstall -y "$pkg" >/dev/null 2>&1 || true
        fi
    done

    # Install requirements into user site to comply with PEP 668 (Homebrew-managed Python)
    log "Installing Python packages from requirements.txt (clean, verbose, non-interactive, user site)..."
    python3 -m pip install --user -r "$requirements_file" --upgrade --force-reinstall -vvv --no-input --no-cache-dir --progress-bar off --no-warn-script-location
    
    success "Python dependencies installed"
}

# Function to install kubectl
install_kubectl() {
    log "Installing kubectl..."
    
    if command_exists kubectl; then
        log "kubectl already installed"
        return 0
    fi
    
    # Install kubectl via Homebrew
    log "Installing kubectl via Homebrew..."
    brew install kubectl
    
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
    
    # Install gcloud CLI via Homebrew
    log "Installing gcloud CLI via Homebrew..."
    brew install --cask google-cloud-sdk
    
    # Add to PATH for current session
    source "$(brew --prefix)/share/google-cloud-sdk/path.bash.inc"
    source "$(brew --prefix)/share/google-cloud-sdk/completion.bash.inc"
    
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
    
    # Install Terraform via Homebrew
    log "Installing Terraform via Homebrew..."
    brew install terraform
    
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
            # pad with zeros to length 3
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
        tg_binary_name="terragrunt_darwin_arm64"
    else
        tg_binary_name="terragrunt_darwin_amd64"
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
    
    # Install Helm via Homebrew
    log "Installing Helm via Homebrew..."
    brew install helm
    
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
    
    # Install Git if not present
    if ! command_exists git; then
        log "Installing Git..."
        brew install git
        success "Git installed successfully"
    else
        log "Git already installed"
    fi
    
    # Install jq for JSON processing
    if ! command_exists jq; then
        log "Installing jq..."
        brew install jq
        success "jq installed successfully"
    else
        log "jq already installed"
    fi
    
    # Install Docker (optional but recommended)
    if ! command_exists docker; then
        log "Installing Docker Desktop..."
        brew install --cask docker
        success "Docker Desktop installed successfully"
        warn "Docker Desktop requires manual setup and login"
    else
        log "Docker already installed"
    fi
    
    # Install curl if not present
    if ! command_exists curl; then
        log "Installing curl..."
        brew install curl
        success "curl installed successfully"
    else
        log "curl already installed"
    fi
}

# Function to configure shell profiles
configure_shell_profiles() {
    log "Configuring shell profiles..."
    
    local shell_profile=""
    local shell_rc=""
    
    # Determine shell and profile files
    case "$SHELL" in
        */zsh)
            shell_profile="$HOME/.zshrc"
            shell_rc="$HOME/.zshrc"
            ;;
        */bash)
            shell_profile="$HOME/.bash_profile"
            shell_rc="$HOME/.bashrc"
            ;;
        *)
            warn "Unknown shell: $SHELL"
            return 0
            ;;
    esac
    
    # Add Homebrew to PATH if not already there
    local homebrew_path=""
    if [[ "$(uname -m)" == "arm64" ]]; then
        homebrew_path="/opt/homebrew/bin"
    else
        homebrew_path="/usr/local/bin"
    fi
    
    # Check if Homebrew path is already in profile
    if [[ -f "$shell_profile" ]] && grep -q "$homebrew_path" "$shell_profile"; then
        log "Homebrew path already configured in $shell_profile"
    else
        log "Adding Homebrew to $shell_profile..."
        echo "" >> "$shell_profile"
        echo "# Homebrew" >> "$shell_profile"
        echo 'eval "$('"$homebrew_path"'/brew shellenv)"' >> "$shell_profile"
        success "Homebrew path added to $shell_profile"
    fi
    
    # Add gcloud CLI to profile with shell-appropriate init scripts
    if [[ -f "$shell_profile" ]] && grep -q "google-cloud-sdk" "$shell_profile"; then
        log "gcloud CLI path already configured in $shell_profile"
    else
        log "Adding gcloud CLI to $shell_profile..."
        echo "" >> "$shell_profile"
        echo "# Google Cloud SDK" >> "$shell_profile"
        if [[ "$SHELL" == *"zsh"* ]]; then
            echo 'source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"' >> "$shell_profile"
            echo 'source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"' >> "$shell_profile"
        else
            echo 'source "$(brew --prefix)/share/google-cloud-sdk/path.bash.inc"' >> "$shell_profile"
            echo 'source "$(brew --prefix)/share/google-cloud-sdk/completion.bash.inc"' >> "$shell_profile"
        fi
        success "gcloud CLI path added to $shell_profile"
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
    
    # Do not source zsh/bash profiles from this bash script to avoid shell builtin errors (e.g., zsh 'autoload')
    # Prompt user to reload manually instead
    warn "Profile updates made to $shell_profile. Restart your terminal or run:"
    echo "   source $shell_profile"
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
    echo "⚠️  Note: You may need to restart your terminal or run 'source ~/.zshrc' (or ~/.bash_profile)"
    echo "   to ensure all tools are in your PATH"
}

# Main installation function
main() {
    echo "🍎 Fast.BI CLI Prerequisites Installer for macOS"
    echo "================================================"
    echo ""
    
    # Check macOS version
    check_macos_version
    
    # Check architecture
    check_architecture
    
    # Install Homebrew
    install_homebrew
    
    # Install Python
    install_python
    # Ensure python/pip shims
    ensure_python_shims
    
    # Install kubectl
    install_kubectl
    
    # Install gcloud CLI
    install_gcloud
    
    # Install Terraform
    install_terraform
    
    # Install Terragrunt
    install_terragrunt
    
    # Install Helm
    install_helm
    
    # Install additional tools
    install_additional_tools
    
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
