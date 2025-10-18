#!/bin/bash

# Fast.BI CLI Prerequisites Verification Script
# Checks if all required tools are properly installed

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

# Function to check Python version
check_python() {
    log "Checking Python installation..."
    
    if command_exists python3; then
        local version=$(python3 --version 2>&1 | cut -d' ' -f2)
        local major_version=$(echo "$version" | cut -d. -f1)
        local minor_version=$(echo "$version" | cut -d. -f2)
        
        if [[ $major_version -ge 3 ]] && [[ $minor_version -ge 9 ]]; then
            success "✅ Python $version: installed (meets requirements)"
            return 0
        else
            error "❌ Python $version: installed but doesn't meet requirements (need 3.9+)"
            return 1
        fi
    elif command_exists python; then
        local version=$(python --version 2>&1 | cut -d' ' -f2)
        local major_version=$(echo "$version" | cut -d. -f1)
        local minor_version=$(echo "$version" | cut -d. -f2)
        
        if [[ $major_version -ge 3 ]] && [[ $minor_version -ge 9 ]]; then
            success "✅ Python $version: installed (meets requirements)"
            return 0
        else
            error "❌ Python $version: installed but doesn't meet requirements (need 3.9+)"
            return 1
        fi
    else
        error "❌ Python: not found"
        return 1
    fi
}

# Function to check kubectl
check_kubectl() {
    log "Checking kubectl installation..."
    
    if command_exists kubectl; then
        local version=$(kubectl version --client --short 2>/dev/null || kubectl version --client 2>/dev/null)
        success "✅ kubectl: installed ($version)"
        return 0
    else
        error "❌ kubectl: not found"
        return 1
    fi
}

# Function to check gcloud CLI
check_gcloud() {
    log "Checking gcloud CLI installation..."
    
    if command_exists gcloud; then
        local version=$(gcloud --version | head -n1)
        success "✅ gcloud CLI: installed ($version)"
        return 0
    else
        error "❌ gcloud CLI: not found"
        return 1
    fi
}

# Function to check Terraform
check_terraform() {
    log "Checking Terraform installation..."
    
    if command_exists terraform; then
        local version=$(terraform --version | head -n1)
        success "✅ Terraform: installed ($version)"
        return 0
    else
        error "❌ Terraform: not found"
        return 1
    fi
}

# Function to check Terragrunt
check_terragrunt() {
    log "Checking Terragrunt installation..."
    
    if command_exists terragrunt; then
        local version=$(terragrunt --version | head -n1)
        success "✅ Terragrunt: installed ($version)"
        return 0
    else
        error "❌ Terragrunt: not found"
        return 1
    fi
}

# Function to check Helm
check_helm() {
    log "Checking Helm installation..."
    
    if command_exists helm; then
        local version=$(helm version --short 2>/dev/null || helm version 2>/dev/null)
        success "✅ Helm: installed ($version)"
        return 0
    else
        error "❌ Helm: not found"
        return 1
    fi
}

# Function to check Git
check_git() {
    log "Checking Git installation..."
    
    if command_exists git; then
        local version=$(git --version | cut -d' ' -f3)
        success "✅ Git: installed ($version)"
        return 0
    else
        error "❌ Git: not found"
        return 1
    fi
}

# Function to check jq
check_jq() {
    log "Checking jq installation..."
    
    if command_exists jq; then
        local version=$(jq --version)
        success "✅ jq: installed ($version)"
        return 0
    else
        error "❌ jq: not found"
        return 1
    fi
}

# Function to check curl
check_curl() {
    log "Checking curl installation..."
    
    if command_exists curl; then
        local version=$(curl --version | head -n1 | cut -d' ' -f2)
        success "✅ curl: installed ($version)"
        return 0
    else
        error "❌ curl: not found"
        return 1
    fi
}

# Function to check Docker (optional)
check_docker() {
    log "Checking Docker installation..."
    
    if command_exists docker; then
        local version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        success "✅ Docker: installed ($version)"

        # Detect daemon status without requiring root
        local daemon_running=false
        # Prefer systemd status if available
        if command_exists systemctl; then
            if systemctl is-active --quiet docker 2>/dev/null; then
                daemon_running=true
            fi
        fi
        # Fallback: check Docker socket presence
        if [[ "$daemon_running" == false ]] && [[ -S /var/run/docker.sock ]]; then
            daemon_running=true
        fi

        if [[ "$daemon_running" == true ]]; then
            success "✅ Docker daemon: running"
            # Check current user's permission to talk to daemon
            if ! docker info >/dev/null 2>&1; then
                if command_exists id && id -nG 2>/dev/null | grep -qw docker; then
                    warn "⚠️  Docker permission issue: daemon is running but CLI cannot connect"
                else
                    warn "⚠️  Docker permission: add your user to 'docker' group, then re-login"
                    warn "   Command: sudo usermod -aG docker $USER && newgrp docker"
                fi
            fi
        else
            warn "⚠️  Docker daemon: not running (start the docker service)"
            if command_exists systemctl; then
                warn "   Try: sudo systemctl start docker"
            fi
        fi
        return 0
    else
        warn "⚠️  Docker: not installed (optional but recommended)"
        return 0
    fi
}

# Function to check PATH configuration
check_path_configuration() {
    log "Checking PATH configuration..."
    
    local missing_in_path=()
    local tools=("python3" "kubectl" "gcloud" "terraform" "terragrunt" "helm")
    
    for tool in "${tools[@]}"; do
        if ! command_exists "$tool"; then
            missing_in_path+=("$tool")
        fi
    done
    
    if [[ ${#missing_in_path[@]} -eq 0 ]]; then
        success "✅ All tools are accessible from PATH"
        return 0
    else
        warn "⚠️  Some tools are not accessible from PATH: ${missing_in_path[*]}"
        warn "   You may need to restart your terminal or source your shell profile"
        return 1
    fi
}

# Function to check cloud provider configuration
check_cloud_configuration() {
    log "Checking cloud provider configuration..."
    
    # Check gcloud configuration
    if command_exists gcloud; then
        local account=$(gcloud config get-value account 2>/dev/null || echo "Not configured")
        local project=$(gcloud config get-value project 2>/dev/null || echo "Not configured")
        
        if [[ "$account" != "Not configured" ]]; then
            success "✅ gcloud account: $account"
        else
            warn "⚠️  gcloud account: not configured (run 'gcloud auth login')"
        fi
        
        if [[ "$project" != "Not configured" ]]; then
            success "✅ gcloud project: $project"
        else
            warn "⚠️  gcloud project: not configured (run 'gcloud config set project PROJECT_ID')"
        fi
    else
        warn "⚠️  gcloud CLI not available for configuration check"
    fi
}

# Function to check Kubernetes configuration
check_kubernetes_configuration() {
    log "Checking Kubernetes configuration..."
    
    if command_exists kubectl; then
        # Check if kubectl can connect to a cluster
        if kubectl cluster-info >/dev/null 2>&1; then
            local context=$(kubectl config current-context 2>/dev/null || echo "Unknown")
            local cluster=$(kubectl config view --minify --output 'jsonpath={.clusters[0].name}' 2>/dev/null || echo "Unknown")
            
            success "✅ Kubernetes cluster: connected"
            success "✅ Current context: $context"
            success "✅ Cluster name: $cluster"
        else
            warn "⚠️  Kubernetes cluster: not connected or no cluster configured"
            warn "   Run 'kubectl config set-cluster' to configure cluster access"
        fi
    else
        warn "⚠️  kubectl not available for configuration check"
    fi
}

# Function to check Python packages
check_python_packages() {
    log "Checking Python packages..."
    
    if command_exists python3; then
        local python_cmd="python3"
    elif command_exists python; then
        local python_cmd="python"
    else
        warn "⚠️  Python not available for package check"
        return 0
    fi
    
    # Check for required Python packages (map distribution name -> import module)
    # PyYAML's import module name is 'yaml'
    declare -A dist_to_module=(
        ["click"]="click"
        ["PyYAML"]="yaml"
        ["questionary"]="questionary"
    )
    local missing_packages=()
    
    for dist in "${!dist_to_module[@]}"; do
        local module_name="${dist_to_module[$dist]}"
        if $python_cmd -c "import ${module_name}" 2>/dev/null; then
            success "✅ Python package '${dist}': installed"
        else
            missing_packages+=("$dist")
            warn "⚠️  Python package '${dist}': not installed"
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        warn "⚠️  Missing Python packages: ${missing_packages[*]}"
        warn "   Install with: ${python_cmd} -m pip install ${missing_packages[*]}"
        return 1
    fi
    
    return 0
}

# Function to run all checks
run_all_checks() {
    echo "🔍 Fast.BI CLI Prerequisites Verification"
    echo "========================================="
    echo ""
    
    local all_passed=true
    local check_results=()
    
    # Run all checks
    check_python && check_results+=("python:pass") || { check_results+=("python:fail"); all_passed=false; }
    check_kubectl && check_results+=("kubectl:pass") || { check_results+=("kubectl:fail"); all_passed=false; }
    check_gcloud && check_results+=("gcloud:pass") || { check_results+=("gcloud:fail"); all_passed=false; }
    check_terraform && check_results+=("terraform:pass") || { check_results+=("terraform:fail"); all_passed=false; }
    check_terragrunt && check_results+=("terragrunt:pass") || { check_results+=("terragrunt:fail"); all_passed=false; }
    check_helm && check_results+=("helm:pass") || { check_results+=("helm:fail"); all_passed=false; }
    check_git && check_results+=("git:pass") || { check_results+=("git:fail"); all_passed=false; }
    check_jq && check_results+=("jq:pass") || { check_results+=("jq:fail"); all_passed=false; }
    check_curl && check_results+=("curl:pass") || { check_results+=("curl:fail"); all_passed=false; }
    check_docker && check_results+=("docker:pass") || { check_results+=("docker:pass"); }  # Docker is optional
    
    echo ""
    echo "📋 Configuration Checks:"
    echo "========================"
    
    check_path_configuration
    check_cloud_configuration
    check_kubernetes_configuration
    check_python_packages
    
    echo ""
    echo "📊 Verification Summary:"
    echo "========================"
    
    local passed_count=0
    local failed_count=0
    
    for result in "${check_results[@]}"; do
        if [[ $result == *":pass" ]]; then
            ((passed_count++))
        else
            ((failed_count++))
        fi
    done
    
    echo "✅ Passed: $passed_count"
    echo "❌ Failed: $failed_count"
    echo "📊 Total: ${#check_results[@]}"
    
    if [[ "$all_passed" == true ]]; then
        echo ""
        success "🎉 All required prerequisites are properly installed!"
        echo ""
        echo "Next steps:"
        echo "1. Configure your cloud provider credentials"
        echo "2. Run the Fast.BI CLI: python3 cli.py"
        echo "3. Follow the deployment guide in docs/"
        return 0
    else
        echo ""
        error "❌ Some prerequisites are missing or not properly configured"
        echo ""
        echo "To fix issues:"
        echo "1. Run the installation script: ./install-prerequisites.sh"
        echo "2. Check the error messages above for specific issues"
        echo "3. Ensure all tools are in your PATH"
        return 1
    fi
}

# Main function
main() {
    run_all_checks
}

# Handle script interruption
trap 'error "Verification interrupted"; exit 1' INT TERM

# Run main function
main "$@"
