# Fast.BI Platform Deployment CLI

This CLI provides a comprehensive deployment solution for the Fast.BI platform across multiple cloud providers.

## ⚠️ Security Warning

**IMPORTANT**: The configuration files in this directory contain example values only. Never use real credentials, API keys, or sensitive information in public repositories. Always:

- Replace all example values with your actual credentials
- Use environment variables or secure secret management for sensitive data
- Never commit real credentials to version control
- Use `.gitignore` to exclude configuration files with real credentials

## 📋 Prerequisites

Before using the Fast.BI CLI, you need to install the required tools and dependencies.

### Required Tools

| Tool | Purpose | Installation |
|------|---------|-------------|
| **Python >=3.9** | CLI runtime | [Download](https://python.org) or use system package manager |
| **kubectl** | Kubernetes management | [Install kubectl](https://kubernetes.io/docs/tasks/tools/) |
| **gcloud CLI** | Google Cloud authentication | [Install gcloud](https://cloud.google.com/sdk/docs/install) |
| **Terraform** | Infrastructure as Code | [Install Terraform](https://terraform.io/downloads) |
| **Terragrunt** | Terraform wrapper | [Install Terragrunt](https://terragrunt.gruntwork.io/docs/getting-started/install/) |
| **Helm** | Kubernetes package manager | [Install Helm](https://helm.sh/docs/intro/install/) |
| **Git** | Repository operations | [Install Git](https://git-scm.com/downloads) |
| **Docker** | Container operations (optional) | [Install Docker](https://docker.com/get-started) |
| **jq** | JSON processing | [Install jq](https://jqlang.github.io/jq/download/) |

### Quick Installation

**Option 1: Automatic Installation (Recommended)**

The prerequisites folder contains cross-platform installation scripts that automatically detect your OS and install the required tools:

#### macOS/Linux
```bash
# Run the cross-platform installer
./cli/prerequisites/install-prerequisites.sh

# Verify installation
./cli/prerequisites/verify-prerequisites.sh
```

#### Windows (PowerShell)
```powershell
# Run the PowerShell installer
.\cli\prerequisites\install-prerequisites.ps1

# Verify installation
.\cli\prerequisites\verify-prerequisites.sh
```

#### Windows (Batch File)
```cmd
# Run the batch installer (recommends PowerShell)
.\cli\prerequisites\install-prerequisites.bat
```

**Note**: The installation scripts automatically detect your operating system and run the appropriate installation method for your platform.

**Option 2: Manual Installation**

#### macOS
```bash
# Install using Homebrew
brew install python kubectl google-cloud-sdk terraform terragrunt helm git docker jq

# Verify installation
python --version
kubectl version --client
gcloud --version
terraform --version
terragrunt --version
helm version
```

#### Linux (Ubuntu/Debian)
```bash
# Update package list
sudo apt update

# Install Python
sudo apt install python3 python3-pip

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install Terraform
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# Install Terragrunt v0.88.1
sudo curl -fsSL -o /usr/local/bin/terragrunt https://github.com/gruntwork-io/terragrunt/releases/download/v0.88.1/terragrunt_linux_amd64
sudo chmod +x /usr/local/bin/terragrunt

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install other tools
sudo apt install git docker.io jq
```

#### Windows (WSL2)
```powershell
# Fast.BI CLI now requires WSL2 for Windows compatibility
# The installer will automatically install WSL2 and Ubuntu if needed
.\cli\prerequisites\install-prerequisites.ps1

# After WSL2 installation, complete setup in WSL2:
wsl -d Ubuntu
git clone https://github.com/fast-bi/data-development-platform.git
cd data-development-platform
chmod +x cli/prerequisites/install-prerequisites.sh
./cli/prerequisites/install-prerequisites.sh
python3 cli.py
```

**Why WSL2?**
- Eliminates Windows-specific compatibility issues
- Provides consistent behavior across all platforms
- Native Linux environment for all tools

### Cloud Provider Setup

#### Google Cloud Platform (GCP)
```bash
# Authenticate with GCP
gcloud auth login

# Set default project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable dns.googleapis.com
```

#### Amazon Web Services (AWS)
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-west-2
```

#### Microsoft Azure
```bash
# Login to Azure
az login

# Set subscription
az account set --subscription "your-subscription-id"
```

### Verification

After installation, verify all tools are working:

```bash
# Check Python version
python --version  # Should be 3.9+

# Check kubectl
kubectl version --client

# Check gcloud
gcloud --version

# Check Terraform
terraform --version

# Check Terragrunt
terragrunt --version

# Check Helm
helm version

# Check Git
git --version
```

### Troubleshooting Prerequisites

#### Common Issues

1. **Python Version Too Old**
   ```bash
   # Update Python to 3.9+
   python --version
   # If < 3.9, install newer version
   ```

2. **kubectl Not Found**
   ```bash
   # Add kubectl to PATH
   export PATH=$PATH:/usr/local/bin
   ```

3. **gcloud Authentication Issues**
   ```bash
   # Re-authenticate
   gcloud auth login
   gcloud auth application-default login
   ```

4. **Terraform/Terragrunt Issues**
   ```bash
   # Verify installation
   which terraform
   which terragrunt
   ```

For detailed installation instructions, see [Prerequisites Documentation](prerequisites/README.md).

## Features

- **Multi-Cloud Support**: GCP, AWS, Azure, and On-Premises deployments
- **Phase-Based Deployment**: 6 distinct phases for controlled deployment
- **State Management**: Resume deployments from any phase
- **Non-Interactive Mode**: Automated deployment using configuration files
- **Service Tracking**: Skip already deployed services
- **Security**: Encrypted deployment files with key management

## Quick Start

### Interactive Mode
```bash
# Run all phases interactively
python cli.py

# Run specific phase
python cli.py --phase 1

# Use simple input (better for pasting)
python cli.py --simple-input
```

### Non-Interactive Mode
```bash
# First, copy an example configuration file
cp cli/deployment_configuration_gcp_example.yaml cli/deployment_configuration.yaml
# Edit cli/deployment_configuration.yaml with your real credentials

# Deploy using configuration file
python cli.py --config cli/deployment_configuration.yaml --non-interactive

# Run specific phases
python cli.py --config cli/deployment_configuration.yaml --non-interactive --phase 1,2,3
```

## Configuration Files Structure

Fast.BI CLI uses a structured approach to configuration management:

### Main Configuration Files

1. **`deployment_configuration.yaml`** - **Local deployment file** (git-ignored, contains real credentials)
2. **`deployment_configuration_gcp_example.yaml`** - GCP-specific example
3. **`deployment_configuration_aws_example.yaml`** - AWS-specific example
4. **`deployment_configuration_onprem_example.yaml`** - On-premise example
5. **`config/`** - Service version management and metadata

**Important**: 
- `deployment_configuration.yaml` is **git-ignored** and should contain your real credentials
- Example files (`*_example.yaml`) are **safe for public repositories** and contain anonymized data
- Copy an example file to `deployment_configuration.yaml` and customize with your real values

### Configuration File Structure

The configuration file uses a Helm-like structure with different cloud provider sections:

```yaml
# Basic Configuration (Phase 1)
basic:
  customer: "*mycompany"
  user_email: "*admin@mycompany.com"
  cloud_provider: "*gcp"  # Options: gcp, aws, azure, onprem
  project_region: "*us-central1"
  domain_name: "*mycompany.com"

# Infrastructure Configuration (Phase 1)
infrastructure_deployment:
  # GCP Configuration (enabled for GCP deployments)
  gcp:
    enabled: true  # Set to true for GCP deployment
    deployment_type: "basic"  # Options: basic, advanced
    billing_account_id: "*01A393-2D8A12-EXAMPLE"
    parent_folder: "*6570382EXAMPLE"
    whitelisted_ips: "*xx.xx.xx.xx/24"
  
  # AWS Configuration (disabled for GCP deployments)
  aws:
    enabled: false
    # aws_access_key_id: "*AKIAIOSFODNN7EXAMPLE"
    # aws_secret_access_key: "*wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    # aws_region: "*us-west-2"
  
  # Azure Configuration (disabled for GCP deployments)
  azure:
    enabled: false
    # subscription_id: "*12345678-1234-1234-1234-123456789012"
    # tenant_id: "*12345678-1234-1234-1234-123456789012"
  
  # On-Premises Configuration (disabled for GCP deployments)
  onprem:
    enabled: false
    # kubeconfig_path: "*path/to/kubeconfig"
```

## Deployment Phases

### Phase 1: Infrastructure Deployment
- Deploy cloud infrastructure (GCP/AWS/Azure)
- Or configure existing infrastructure with kubeconfig
- Sets up Kubernetes cluster and networking

### Phase 2: Generate Platform Secrets
- Configure vault method (local_vault/external_infisical)
- Set up data analysis and warehouse platforms
- Configure Git repositories and access methods
- Generate platform secrets

### Phase 3: Configure Data Platform Repositories
- Configure data orchestration and modeling repositories
- Set up repository access (deploy keys, access tokens)
- Verify repository connectivity

### Phase 4: Deploy Infrastructure Services
- Deploy Kubernetes infrastructure services:
  - Secret Operator
  - Cert Manager
  - External DNS
  - Traefik Load Balancer
  - StackGres PostgreSQL
  - Log Collector
  - Services Monitoring
  - Cluster Cleaner
  - IDP SSO Manager
  - Cluster PVC Autoscaler

### Phase 5: Deploy Data Services
- Deploy Kubernetes data services:
  - CICD Workload Runner
  - Object Storage Operator
  - Argo Workflows
  - Data Replication
  - Data Orchestration
  - Data Modeling
  - DCDQ Metadata Collector
  - Data Analysis
  - Data Governance
  - Data Platform User Console

### Phase 6: Finalize Deployment
- Save deployment files to Git repository
- Generate encryption key for secure storage
- Provide access information

## Cloud Provider Configuration

### GCP Deployment
```yaml
infrastructure_deployment:
  gcp:
    enabled: true
    deployment_type: "basic"  # or "advanced"
    billing_account_id: "*01A393-2D8A12-EXAMPLE"
    parent_folder: "*6570382EXAMPLE"
    whitelisted_ips: "*xx.xx.xx.xx/24"
```

### AWS Deployment
```yaml
infrastructure_deployment:
  aws:
    enabled: true
    aws_access_key_id: "*AKIAIOSFODNN7EXAMPLE"
    aws_secret_access_key: "*wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    aws_region: "*us-west-2"
    vpc_cidr: "10.0.0.0/16"
    cluster_name: "fast-bi-cluster"
    instance_type: "t3.medium"
```

### Azure Deployment
```yaml
infrastructure_deployment:
  azure:
    enabled: true
    subscription_id: "*12345678-1234-1234-1234-123456789012"
    tenant_id: "*12345678-1234-1234-1234-123456789012"
    client_id: "*12345678-1234-1234-1234-123456789012"
    client_secret: "*your-client-secret"
    resource_group: "*fast-bi-rg"
    location: "*eastus"
```

### On-Premises Deployment
```yaml
infrastructure_deployment:
  onprem:
    enabled: true
    kubeconfig_path: "*path/to/kubeconfig"
    cluster_name: "*onprem-cluster"
    storage_class: "*local-storage"
```

## CLI Options

```bash
python cli.py [OPTIONS]

Options:
  --config, -c TEXT           Path to configuration file (YAML)
  --interactive / --no-interactive  Run in interactive mode
  --phase INTEGER             Execute specific phase only (1-6)
  --simple-input              Use simple input method (better for pasting)
  --state-file TEXT           Path to state file
  --show-config               Show configuration summary and exit
  --keycloak-help             Show Keycloak setup help and exit
  --non-interactive           Run in non-interactive mode (requires config file)
  --destroy                   Destroy entire environment (infrastructure + Kubernetes resources)
  --destroy-confirm           Skip confirmation for destroy operation
```

## Destroy Functionality

The CLI includes a comprehensive destroy feature that removes the entire environment:

### Basic Usage
```bash
# Destroy with confirmation prompt
python cli.py --destroy

# Destroy without confirmation (use with caution)
python cli.py --destroy --destroy-confirm
```

### What Gets Destroyed

1. **Kubernetes Resources** (in reverse deployment order):
   - Data Services (User Console, Data Governance, Data Analysis, etc.)
   - Infrastructure Services (IDP SSO Manager, Traefik, Cert Manager, etc.)
   - Custom Namespaces (vault, datahub, elastic-system, etc.)

2. **Cloud Infrastructure**:
   - GCP: Uses `terragrunt destroy --all` to remove all Terraform resources
   - AWS: Infrastructure destruction (to be implemented)
   - Azure: Infrastructure destruction (to be implemented)

3. **State and Configuration**:
   - Deployment state file
   - Kubeconfig file
   - Temporary Terraform files

### Destroy Process

The destroy operation follows a specific order to ensure clean removal:

1. **Step 1**: Destroy Kubernetes resources (Helm charts and namespaces)
2. **Step 2**: Destroy cloud infrastructure (Terraform/Terragrunt)
3. **Step 3**: Clean up state and configuration files

### Safety Features

- **Confirmation Prompt**: By default, requires user confirmation before destruction
- **Destruction Summary**: Shows what will be destroyed before proceeding
- **Error Handling**: Continues with partial destruction even if some resources fail
- **Timeout Protection**: Prevents hanging on stuck resources

### Example Output

```bash
$ python cli.py --destroy

⚠️  WARNING: This will destroy the entire environment!
   This includes:
   - All Kubernetes resources (Helm charts, namespaces)
   - Cloud infrastructure (GCP/AWS/Azure resources)
   - All data and configurations

Are you sure you want to proceed with destruction? [y/N]: y

🗑️  ENVIRONMENT DESTRUCTION
==================================================
📋 Destruction Summary:
  Customer: mycompany
  Cloud Provider: gcp
  Domain: mycompany.com
  Infrastructure Services: 9 deployed
  Data Services: 10 deployed

🔧 Step 1: Destroying Kubernetes resources...
  📊 Destroying data services...
    🗑️  Destroying 10.0_user_console...
      ✅ 10.0_user_console destroyed
    🗑️  Destroying 9.0_data_governance...
      ✅ 9.0_data_governance destroyed
  🏗️  Destroying infrastructure services...
    🗑️  Destroying 9.0_idp_sso_manager...
      ✅ 9.0_idp_sso_manager destroyed
  🗂️  Cleaning up custom namespaces...
    ✅ Namespace vault deleted
    ✅ Namespace datahub deleted
✅ Kubernetes resources destroyed successfully

☁️  Step 2: Destroying cloud infrastructure...
  🗑️  Destroying GCP infrastructure...
    🔧 Running 'terragrunt destroy --all'...
    ✅ GCP infrastructure destroyed successfully

🧹 Step 3: Cleaning up state and configuration...
  ✅ State file deleted
  ✅ Kubeconfig file deleted
  ✅ Cleanup completed

✅ Environment destruction completed successfully!
💡 You can now run 'python cli.py' to start a fresh deployment.
```

## State Management

The CLI maintains deployment state in `cli/state/deployment_state.json`:
- Configuration parameters
- Phase completion status
- Individual service deployment tracking
- Kubeconfig path

## Security Features

- **Encrypted Deployment Files**: All deployment files are encrypted before saving to Git
- **Encryption Key Management**: Secure key generation and storage
- **Access Token Handling**: Secure handling of cloud provider credentials
- **Vault Integration**: Integration with HashiCorp Vault for secret management

## Access Information

After successful deployment, you'll get access to:

- **IDP Console**: `https://login.{customer}.{domain}` (SSO administration)
- **Fast.BI Platform**: `https://{customer}.{domain}` (main platform)

## Examples

See the cloud-specific example files for complete configuration examples:
- **GCP**: `cli/deployment_configuration_gcp_example.yaml`
- **AWS**: `cli/deployment_configuration_aws_example.yaml`
- **On-Premise**: `cli/deployment_configuration_onprem_example.yaml`

## Troubleshooting

### Common Issues

1. **Configuration File Not Found**
   ```bash
   python cli.py --config path/to/config.yaml --non-interactive
   ```

2. **Phase Already Completed**
   - The CLI will skip already completed phases
   - Check state file for current progress

3. **Service Deployment Failed**
   - Check Kubernetes cluster connectivity
   - Verify service account permissions
   - Review logs for specific error messages

### Debug Mode

```bash
# Show current configuration
python cli.py --show-config

# Show Keycloak setup help
python cli.py --keycloak-help
```

## 📋 Service Version Management

Fast.BI uses a centralized version management system in the `cli/config/` directory to ensure compatibility and proper service deployment.

### Config Directory Structure

```
cli/config/
├── data_services_config.json      # Data services versions and metadata
└── infrastructure_services_config.json  # Infrastructure services versions
```

### Data Services Configuration (`data_services_config.json`)

This file defines all data services with their:
- **Chart versions** (Helm chart versions)
- **App versions** (Application versions)
- **Required parameters** for deployment
- **Deployment phases** (for complex services)

**Example Data Services:**
- **CICD Workload Runner**: `chart_version: "0.23.7"`
- **Data Orchestration (Airflow)**: `chart_version: "1.16.0"`, `app_version: "v2.11.0"`
- **Data Analysis**: `chart_version: "1.7.4"`, `app_version: "0.1975.0"`
- **Data Governance (DataHub)**: `chart_version: "0.6.17"`, `app_version: "v1.2.0"`

### Infrastructure Services Configuration (`infrastructure_services_config.json`)

This file defines infrastructure services with:
- **Chart versions** for different deployment methods
- **Vault method variations** (local_vault vs external_infisical)
- **Required parameters** for each service

**Example Infrastructure Services:**
- **Secret Operator**: Different versions for `local_vault` vs `external_infisical`
- **Cert Manager**: `chart_version: "v1.18.2"`
- **Traefik Load Balancer**: `chart_version: "37.0.0"`

### Version Management Best Practices

#### 1. **Data Analysis Platform Selection**
When choosing different data analysis platforms, ensure compatible versions:

```yaml
# In your deployment_configuration.yaml
secrets:
  data_analysis_platform: "*superset"  # Options: lightdash, superset, metabase, looker
```

**Supported Platforms:**
- **Lightdash**: Open-source BI platform
- **Superset**: Apache Superset (default)
- **Metabase**: User-friendly BI tool
- **Looker**: Google's BI platform

#### 2. **Data Warehouse Platform Selection**
Different warehouse platforms require specific configurations:

```yaml
secrets:
  data_warehouse_platform: "*bigquery"  # Options: bigquery, snowflake, redshift
  # BigQuery specific (only if using BigQuery)
  bigquery_project_id: "your-project-id"
  bigquery_region: "us-central1"
```

#### 3. **Git Provider Integration**
Different Git providers require specific runner configurations:

```yaml
secrets:
  git_provider: "*github"  # Options: github, gitlab, bitbucket, fastbi
  repo_access_method: "*deploy_keys"  # Options: access_token, deploy_keys, ssh_keys
```

#### 4. **Vault Method Selection**
Choose between local or external vault management:

```yaml
secrets:
  vault_method: "*local_vault"  # Options: local_vault, external_infisical
```

**Local Vault**: HashiCorp Vault deployed in Kubernetes  
**External Infisical**: External secret management service

### Updating Service Versions

To update service versions:

1. **Check current versions** in `cli/config/*.json`
2. **Update chart versions** in the JSON files
3. **Test compatibility** with your chosen platforms
4. **Update deployment configuration** if needed

**Example version update:**
```json
{
  "8.0_data_analysis": {
    "chart_version": "1.7.5",  // Updated from 1.7.4
    "app_version": "0.1976.0"  // Updated from 0.1975.0
  }
}
```

### Service Dependencies

Some services have complex dependencies:

#### Data Governance (DataHub)
- **Elasticsearch Operator**: `chart_version: "0.16.0"`
- **Elasticsearch Cluster**: `app_version: "8.17.0"`
- **Elasticsearch Operator**: `chart_version: "3.1.0"`
- **DataHub Prerequisites**: Custom deployment phase
- **DataHub**: Main application

#### Secret Operator
- **Local Vault**: HashiCorp Vault + Secret Operator
- **External Infisical**: Infisical client only

### Troubleshooting Version Issues

1. **Chart Version Conflicts**: Check Helm repository compatibility
2. **App Version Mismatches**: Ensure app_version matches chart_version requirements
3. **Parameter Validation**: Verify all required parameters are provided
4. **Dependency Issues**: Check service deployment order and dependencies

For version compatibility issues, refer to the individual service documentation or contact support.

## Support

For issues and questions:
1. Check the state file for deployment progress
2. Review Kubernetes cluster logs
3. Verify configuration file syntax
4. Ensure all required parameters are provided 