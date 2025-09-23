# Google Cloud Platform (GCP) Deployment Guide

This guide provides step-by-step instructions for deploying Fast.BI on Google Cloud Platform using the Fast.BI CLI tool.

## 🎯 Overview

Fast.BI GCP deployment creates a complete data platform with:
- **GKE Cluster**: Kubernetes cluster for running Fast.BI services
- **VPC Network**: Secure networking with proper firewall rules
- **Load Balancer**: External IP for accessing the platform
- **Storage**: Persistent storage for databases and data
- **Monitoring**: Built-in observability and logging

## 📋 Prerequisites

### Required GCP Resources
- **GCP Account**: Active Google Cloud Platform account
- **Billing Account**: Enabled billing account (required for CLI deployment)
- **Domain**: Custom domain for the platform (e.g., `mycompany.com`)

> 💰 **Free Tier Available!** GCP offers $300 in free credits when you sign up, which is enough to run Fast.BI for approximately 14 days for testing and evaluation.

### Required Git Repositories
- **Data Models Repository**: For dbt models and data transformations
  - Example: `https://github.com/mycompany/dbt-data-models.git`
- **Data Orchestration Repository**: For Airflow DAGs and workflows
  - Example: `https://github.com/mycompany/data-orchestration-dags.git`

> ⚠️ **Important**: These repositories are mandatory for the platform to function. You must have access to create or use existing repositories in GitHub, GitLab, Bitbucket, or GitLab.

> 🔒 **Security Note**: The examples above use placeholder values (`mycompany`) to protect sensitive information. Never use real repository URLs, billing account IDs, or folder IDs in public documentation.

### Required Tools
- **Python >=3.9**: For running the Fast.BI CLI
- **kubectl**: Kubernetes command-line tool
- **gcloud CLI**: Google Cloud command-line tool (required for authentication)
- **Terraform**: Infrastructure as Code tool for GCP resource management
- **Terragrunt**: Terraform wrapper for keeping configurations DRY
- **Helm**: Kubernetes package manager for deploying applications

### Simple Setup Process
1. **Create GCP Account**: Sign up at [cloud.google.com](https://cloud.google.com) and get $300 free credits
2. **Enable Billing**: Set up billing account (required for CLI deployment)
3. **Install Required Tools**: Use the appropriate installation guide for your operating system
4. **Authenticate**: Run these two commands:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
5. **Start Deployment**: Run `python cli.py` and follow the wizard

### GCP Permissions
Your GCP account needs the following roles:
- **Project Creator** (for creating new projects)
- **Billing Account User** (for associating projects with billing)
- **Compute Admin** (for managing compute resources)
- **Kubernetes Engine Admin** (for managing GKE clusters)
- **Network Admin** (for managing VPC and networking)
- **Service Account Admin** (for creating service accounts)

> ℹ️ **Note**: Organization and folder access are optional. The CLI can create projects directly under your account if you don't have organization/folder access.

## 🚀 Quick Start

### Free Tier Experience
Fast.BI is designed to work seamlessly with GCP's free tier:
- **$300 Free Credits**: Enough for 14 days of testing
- **Simple Setup**: Just 4 steps to get started
- **No Complex Configuration**: CLI handles everything automatically
- **Easy Cleanup**: Destroy environment when done testing

### 1. Clone the Repository
```bash
git clone https://github.com/fast-bi/data-development-platform.git
cd data-development-platform
```

### 2. Authenticate with GCP
```bash
gcloud auth login
gcloud auth application-default login
```

### 3. Run the CLI
```bash
python cli.py
```

### 4. Follow the Interactive Wizard
The CLI will guide you through 6 deployment phases:
1. **Infrastructure Deployment** - Create GKE cluster and networking
2. **Generate Platform Secrets** - Set up authentication and repositories
3. **Configure Repositories** - Connect your Git repositories
4. **Deploy Infrastructure Services** - Core platform services
5. **Deploy Data Services** - Data platform components
6. **Finalize Deployment** - Save configuration and access info

## 📝 Configuration Options

> 🔒 **Security First**: All configuration examples in this guide use placeholder values to protect sensitive information. Never commit real credentials, billing account IDs, or repository URLs to version control.

### Deployment Types

#### Basic Deployment (Recommended for Testing)
- **Single Zone GKE**: Faster deployment, lower cost
- **Default Settings**: Uses recommended configurations
- **Local State**: Infrastructure files saved locally

#### Advanced Deployment (Production)
- **Multi-Zone GKE**: Higher availability, production-ready
- **Custom CIDR Blocks**: Tailored network configuration
- **Remote State**: Infrastructure files saved in GCS bucket

### State Management

#### Local State (Default)
```yaml
terraform_state: "local"
```
- ✅ **Pros**: No external dependencies, faster setup
- ⚠️ **Cons**: Files must be kept safe, manual cleanup required

#### Remote State (Team Collaboration)
```yaml
terraform_state: "remote"
state_project: "your-state-project"
state_location: "us-central1"
state_bucket: "fast-bi-terraform-state"
```
- ✅ **Pros**: Team collaboration, automatic state management
- ⚠️ **Cons**: Requires additional GCP project setup

## 🔧 Detailed Configuration

### Basic Configuration
```yaml
basic:
  customer: "mycompany"                      # Company/tenant name
  user_email: "admin@mycompany.com"          # Admin email
  cloud_provider: "gcp"                      # Cloud provider
  project_region: "us-central1"              # GCP region
  domain_name: "mycompany.com"               # Custom domain
```

### GCP Infrastructure Configuration
```yaml
infrastructure_deployment:
  gcp:
    deployment_type: "basic"                  # basic or advanced
    billing_account_id: "0XXXXXXX-XXXXXX-XXXXXX"  # Your GCP billing account ID
    parent_folder: "0XXXXXXXXX"                    # Your GCP folder ID (optional)
    whitelisted_ips: "0.0.0.0/0"                  # Allowed IP ranges (0.0.0.0/0 for all)
    
    # 🔒 SECURITY: Replace placeholder values with your actual GCP information
    
    # State Management
    terraform_state: "local"                 # local or remote
    gke_deployment_type: "zonal"            # zonal or multizone
```

### Platform Configuration
```yaml
secrets:
  vault_method: "local_vault"                # local_vault or external_infisical
  data_analysis_platform: "superset"         # superset, lightdash, metabase, looker
  data_warehouse_platform: "bigquery"        # bigquery, snowflake, redshift
  orchestrator_platform: "Airflow"           # Airflow or Composer
  git_provider: "github"                     # github, gitlab, bitbucket, fastbi
```

## 📋 Step-by-Step Deployment

### Phase 1: Infrastructure Deployment

#### Interactive Mode
1. Run `python cli.py`
2. Select "Start new deployment"
3. Choose "Deploy new infrastructure"
4. Select GCP as cloud provider
5. Enter basic configuration:
   - Customer name (1-64 characters)
   - Admin email
   - Project region (e.g., `us-central1`)
   - Domain name
6. Enter GCP-specific details:
   - Billing account ID
   - Parent folder ID
   - Whitelisted IP addresses
7. Choose deployment type:
   - **Basic**: Single zone, default settings
   - **Advanced**: Multi-zone, custom configuration
8. Choose state management:
   - **Local**: Files saved locally
   - **Remote**: Files saved in GCS bucket
9. Confirm deployment

#### Non-Interactive Mode
1. Create configuration file:
```bash
cp cli/deployment_configuration.yaml_gcp_example cli/deployment_configuration.yaml
```

2. Edit the configuration file with your values

3. Run deployment:
```bash
python cli.py --config cli/deployment_configuration.yaml --non-interactive
```

#### 🔒 Security Best Practices
- **Never commit** configuration files with real credentials to version control
- **Use environment variables** for sensitive values when possible
- **Store configurations securely** and limit access to authorized users
- **Rotate credentials regularly** for production environments
- **Use .gitignore** to exclude configuration files from repositories

#### What Gets Created
- **GCP Project**: `fast-bi-{customer}`
- **VPC Network**: Custom network with subnets
- **GKE Cluster**: Kubernetes cluster with node pools
- **Firewall Rules**: Secure access control
- **Load Balancer**: External IP for services
- **Service Accounts**: Platform and data service accounts

### Phase 2: Generate Platform Secrets

The CLI will automatically:
1. **Create Vault Instance**: Local HashiCorp Vault for secrets
2. **Generate SSH Keys**: For repository access
3. **Configure Service Accounts**: GCP service account credentials
4. **Set Platform Secrets**: Database passwords, API keys, etc.

#### Required Inputs
- **Vault Method**: Choose `local_vault` (recommended)
- **Data Analysis Platform**: Select your preferred BI tool
- **Data Warehouse**: Choose BigQuery (recommended for GCP)
- **Git Provider**: Select your Git hosting service
- **Repository URLs**: DAG and data model repositories
- **Access Method**: Deploy keys (recommended) or access tokens

#### BigQuery Configuration (Required)
If using BigQuery as data warehouse:
- **Project ID**: Usually auto-filled from GCP project
- **Region**: Usually auto-filled from deployment region
- **Service Account Files**: Automatically loaded from infrastructure deployment

### Phase 3: Configure Repositories

> ⚠️ **Critical**: This phase requires two Git repositories to be set up before deployment.

#### Repository Requirements
1. **Data Models Repository**: For dbt models and data transformations
   - **Purpose**: Stores your data transformation logic
   - **Example**: `https://github.com/mycompany/dbt-data-models.git`
   - **Content**: dbt models, tests, documentation

2. **Data Orchestration Repository**: For Airflow DAGs and workflows
   - **Purpose**: Stores your data pipeline definitions
   - **Example**: `https://github.com/mycompany/data-orchestration-dags.git`
   - **Content**: Airflow DAGs, Python scripts, configurations

#### Repository Setup Steps
1. **Create or Use Existing Repositories**: Set up repositories in GitHub, GitLab, Bitbucket, or Fast.BI GitLab
2. **Add Deploy Keys**: Copy SSH public keys from CLI to your repositories
3. **Verify Access**: CLI tests repository connectivity
4. **Configure Branches**: Set main branch for data models (usually `main` or `master`)

#### Repository Access Methods
- **Deploy Keys (Recommended)**: SSH-based access, more secure
- **Access Tokens**: Personal access tokens for repository access
- **SSH Keys**: Direct SSH key authentication

### Phase 4: Deploy Infrastructure Services

The CLI deploys these services in order:
1. **Secret Operator**: Manages secrets across the platform
2. **Cert Manager**: SSL/TLS certificate management
3. **External DNS**: Automatic DNS record management
4. **Traefik Load Balancer**: Ingress controller and load balancing
5. **StackGres PostgreSQL**: Database cluster
6. **Log Collector**: Centralized logging
7. **Services Monitoring**: Prometheus and Grafana
8. **Cluster Cleaner**: Resource cleanup and maintenance
9. **IDP SSO Manager**: Keycloak for authentication
10. **Cluster PVC Autoscaler**: Storage management

#### Keycloak Setup (Important!)
After Phase 4 completes:
1. **Access Keycloak**: `https://login.{customer}.{domain}`
2. **Import Realm**: Use the generated realm file
3. **Configure SSO**: Set up authentication for your users

### Phase 5: Deploy Data Services

The CLI deploys these services in order:
1. **CICD Workload Runner**: GitLab/GitHub runners for CI/CD
2. **Object Storage Operator**: MinIO for S3-compatible storage
3. **Argo Workflows**: Workflow orchestration
4. **Data Replication**: Airbyte for data ingestion
5. **Data Orchestration**: Apache Airflow for workflows
6. **Data Modeling**: dbt for transformations
7. **DCDQ Metadata Collector**: Data quality and metadata
8. **Data Analysis**: Your chosen BI platform
9. **Data Governance**: DataHub for catalog and governance
10. **User Console**: Fast.BI web interface

### Phase 6: Finalize Deployment

1. **Save Configuration**: Deployment files saved to Git repository
2. **Encryption**: Files encrypted for security
3. **Documentation**: Complete deployment summary generated

## 🌐 Access Your Platform

### Platform URLs
- **Fast.BI Console**: `https://{customer}.{domain}`
- **Keycloak Admin**: `https://login.{customer}.{domain}`

### Default Credentials
- **Keycloak Admin**: Generated during deployment
- **Database**: Auto-configured with secure passwords
- **Service Accounts**: Automatically managed

## 🔍 Monitoring and Troubleshooting

### Check Deployment Status
```bash
python cli.py --show-config
```

### View Service Status
```bash
kubectl get pods --all-namespaces
```

### Check Logs
```bash
kubectl logs -n {namespace} {pod-name}
```

### Common Issues

#### Infrastructure Deployment Fails
- Verify billing account is enabled
- Check GCP quotas and limits
- Ensure proper IAM permissions

#### Services Won't Start
- Check kubeconfig is valid
- Verify cluster has sufficient resources
- Check service account permissions

#### DNS Issues
- Verify domain nameserver configuration
- Check External DNS service status
- Ensure domain is properly configured

## 🗑️ Cleanup and Destruction

### Free Tier Cost Management
- **$300 Free Credits**: Typically lasts 14 days for testing
- **Monitor Usage**: Check GCP Console billing dashboard
- **Destroy Promptly**: Remove environment when done testing to avoid charges
- **Set Budget Alerts**: Configure billing alerts in GCP Console

### Destroy Environment
```bash
python cli.py --destroy --destroy-confirm
```

This will:
1. **Remove Kubernetes Resources**: All Helm charts and namespaces
2. **Destroy GCP Infrastructure**: VPC, GKE cluster, load balancers
3. **Clean Up State**: Remove local configuration files
4. **Stop Billing**: All resources are completely removed

### Manual Cleanup
If automatic destruction fails:
1. **Delete GKE Cluster**: Remove from GCP Console
2. **Delete VPC**: Remove network resources
3. **Delete Project**: Remove entire GCP project

## 📚 Additional Resources

### Configuration Examples
- **Basic GCP**: `cli/deployment_configuration.yaml_gcp_example`
- **Advanced GCP**: Custom configuration with advanced features
- **Multi-Environment**: Separate configurations for dev/staging/prod

### CLI Commands
```bash
# Show help
python cli.py --help

# Run specific phase
python cli.py --phase 3

# Non-interactive deployment
python cli.py --config config.yaml --non-interactive

# Show current configuration
python cli.py --show-config

# Get Keycloak setup help
python cli.py --keycloak-help
```

### Support and Community
- **GitHub Issues**: Report bugs and request features
- **Documentation**: [wiki.fast.bi](https://wiki.fast.bi)
- **Community**: Join discussions and get help

## 🎉 Next Steps

After successful deployment:
1. **Configure Users**: Set up SSO authentication in Keycloak
2. **Connect Data Sources**: Configure data replication in Airbyte
3. **Create Data Models**: Build dbt models in your data repository
4. **Set Up Dashboards**: Create visualizations in your BI platform
5. **Monitor Performance**: Use built-in monitoring and alerting

### After Free Tier Expires
- **Continue Using**: Platform continues to work with billing account
- **Cost Optimization**: Use spot instances and right-sizing for production
- **Scale Up**: Add more resources as your needs grow
- **Production Ready**: Same platform, now with production-grade resources

---

**Need Help?** Check the [troubleshooting section](#monitoring-and-troubleshooting) or open an issue on GitHub.
