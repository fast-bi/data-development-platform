#!/bin/bash

# Fast.BI CLI Prerequisites Installer
# Cross-platform script that detects OS and runs appropriate installation

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

# Function to detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            echo "ubuntu"
        elif command -v yum &> /dev/null; then
            echo "centos"
        elif command -v dnf &> /dev/null; then
            echo "fedora"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows with Git Bash or similar
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to check if running as root/admin
check_privileges() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - check if running as root
        if [[ $EUID -eq 0 ]]; then
            warn "Running as root on macOS is not recommended"
            return 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - check if running as root
        if [[ $EUID -eq 0 ]]; then
            return 0
        else
            warn "Some installations may require sudo privileges"
            return 1
        fi
    fi
    return 0
}

# Function to create logs directory
setup_logging() {
    local logs_dir="logs"
    if [[ ! -d "$logs_dir" ]]; then
        mkdir -p "$logs_dir"
        log "Created logs directory: $logs_dir"
    fi
}

# Function to run platform-specific installation
run_platform_install() {
    local platform=$1
    local script_path=""
    
    case $platform in
        "macos")
            script_path="./macos/install-macos.sh"
            ;;
        "ubuntu"|"centos"|"fedora"|"linux")
            script_path="./linux/install-linux.sh"
            ;;
        "windows")
            error "Windows detected. Please run the PowerShell script instead:"
            error "  .\\install-prerequisites.ps1"
            exit 1
            ;;
        *)
            error "Unsupported operating system: $platform"
            exit 1
            ;;
    esac
    
    if [[ ! -f "$script_path" ]]; then
        error "Installation script not found: $script_path"
        exit 1
    fi
    
    log "Running $platform installation script..."
    chmod +x "$script_path"
    
    # Run the platform-specific script with logging
    if bash "$script_path" 2>&1 | tee "logs/install-${platform}-$(date +%Y%m%d-%H%M%S).log"; then
        success "Platform-specific installation completed successfully"
    else
        error "Platform-specific installation failed"
        exit 1
    fi
}

# Function to verify installation
verify_installation() {
    log "Verifying installation..."
    
    local verify_script="./verify-prerequisites.sh"
    if [[ -f "$verify_script" ]]; then
        chmod +x "$verify_script"
        if bash "$verify_script"; then
            success "All prerequisites verified successfully!"
        else
            warn "Some prerequisites may not be properly installed"
            warn "Check the verification output above for details"
        fi
    else
        warn "Verification script not found. Please run verification manually."
    fi
}

# Function to show installation summary
show_summary() {
    log "Installation Summary:"
    echo "===================="
    echo "✅ Prerequisites installation completed"
    echo "📁 Logs saved to: logs/"
    echo "🔍 Run verification: ./verify-prerequisites.sh"
    echo ""
    echo "Next steps:"
    echo "1. Configure your cloud provider credentials"
    echo "2. Run the Fast.BI CLI: python cli.py"
    echo "3. Follow the deployment guide in docs/"
}

# Main installation function
main() {
    echo "🚀 Fast.BI CLI Prerequisites Installer"
    echo "======================================"
    echo ""
    
    # Setup logging
    setup_logging
    
    # Detect OS
    log "Detecting operating system..."
    local os=$(detect_os)
    log "Detected OS: $os"
    
    # Check privileges
    check_privileges
    
    # Check if we're in the right directory
    if [[ ! -f "../../cli.py" ]]; then
        error "This script must be run from the cli/prerequisites/ directory"
        error "Please navigate to the correct directory and try again"
        exit 1
    fi
    
    # Check available disk space (at least 2GB)
    local available_space=$(df . | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 2097152 ]]; then
        warn "Low disk space detected. At least 2GB recommended for installation."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Installation cancelled"
            exit 1
        fi
    fi
    
    # Run platform-specific installation
    run_platform_install "$os"
    
    # Verify installation
    verify_installation
    
    # Show summary
    show_summary
}

# Handle script interruption
trap 'error "Installation interrupted"; exit 1' INT TERM

# Run main function
main "$@"
