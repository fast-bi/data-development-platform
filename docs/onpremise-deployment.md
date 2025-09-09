# On-Premise Deployment Guide

This guide provides step-by-step instructions for deploying Fast.BI on your existing Kubernetes infrastructure using the Fast.BI CLI tool.

## 🎯 Overview

Fast.BI on-premise deployment leverages your existing Kubernetes cluster to create a complete data platform. This approach is ideal when you:
- **Already have Kubernetes**: Running on-premise or in any cloud
- **Want full control**: Over infrastructure and networking
- **Need compliance**: Meet regulatory or security requirements
- **Have existing resources**: Want to utilize current infrastructure

## 📋 Prerequisites

### Required Infrastructure
- **Kubernetes Cluster**: Version 1.24+ with sufficient resources
- **Storage Class**: Default storage class for persistent volumes
- **Load Balancer**: External load balancer or ingress controller
- **DNS Management**: Ability to configure DNS records
- **Network Access**: Outbound internet access for container images

### Cluster Requirements
- **CPU**: Minimum 4 cores, recommended 8+ cores
- **Memory**: Minimum 16GB RAM, recommended 32GB+ RAM
- **Storage**: Minimum 100GB available storage
- **Nodes**: Minimum 6 worker nodes for production

### Required Tools
- **Python >=3.9+**: For running the Fast.BI CLI
- **kubectl**: Configured to access your cluster
- **kubeconfig**: Valid kubeconfig file for cluster access

### Cluster Permissions
Your kubeconfig needs access to:
- **Create Namespaces**: For Fast.BI services
- **Deploy Helm Charts**: For service installation
- **Create ServiceAccounts**: For service authentication
- **Manage Secrets**: For platform configuration
- **Create PersistentVolumeClaims**: For data storage

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/fast-bi/data-development-platform.git
cd data-development-platform
```

### 2. Run the CLI
```bash
python cli.py
```

### 3. Follow the Interactive Wizard
The CLI will guide you through 6 deployment phases:
1. **Infrastructure Configuration** - Provide kubeconfig and cluster details
2. **Generate Platform Secrets** - Set up authentication and configuration
3. **Configure Repositories** - Connect Git repositories
4. **Deploy Infrastructure Services** - Core platform services
5. **Deploy Data Services** - Data platform components
6. **Finalize Deployment** - Save configuration

## 📝 Configuration Options

### On-Premise Configuration
```yaml
basic:
  customer: "mycompany"                      # Company/tenant name
  user_email: "admin@mycompany.com"          # Admin email
  cloud_provider: "onprem"                   # Cloud provider
  project_region: "datacenter-1"             # Location identifier
  domain_name: "mycompany.com"               # Custom domain

infrastructure_deployment:
  onprem:
    kubeconfig_path: "/path/to/kubeconfig"   # Path to kubeconfig file
    cluster_name: "mycompany-cluster"        # Cluster identifier
    storage_class: "local-storage"           # Storage class name
```

### Platform Configuration
```yaml
secrets:
  vault_method: "local_vault"                # local_vault or external_infisical
  data_analysis_platform: "superset"         # superset, lightdash, metabase, looker
  data_warehouse_platform: "bigquery"        # bigquery, snowflake, redshift, postgres
  orchestrator_platform: "Airflow"           # Airflow or Composer
  git_provider: "github"                     # github, gitlab, bitbucket, fastbi
```

## 📋 Step-by-Step Deployment

### Phase 1: Infrastructure Configuration

#### Interactive Mode
1. Run `python cli.py`
2. Select "Start new deployment"
3. Choose "Use existing infrastructure (provide kubeconfig)"
4. Enter basic configuration:
   - Customer name (1-64 characters)
   - Admin email
   - Deployment location (e.g., `datacenter-1`, `office`)
   - Domain name
5. Provide cluster details:
   - **Kubeconfig Path**: Full path to your kubeconfig file
   - **Cluster Name**: Identifier for your cluster
   - **Storage Class**: Default storage class name
6. Confirm configuration

#### Non-Interactive Mode
1. Create configuration file:
```bash
cp cli/deployment_configuration_onprem_example.yaml cli/deployment_configuration.yaml
```

2. Edit the configuration file with your values

3. Run deployment:
```bash
python cli.py --config cli/deployment_configuration.yaml --non-interactive
```

#### What Gets Configured
- **Cluster Access**: Validates kubeconfig and cluster connectivity
- **Storage Verification**: Confirms storage class availability
- **Resource Check**: Verifies cluster has sufficient resources
- **Network Test**: Tests outbound connectivity for images

### Phase 2: Generate Platform Secrets

The CLI will automatically:
1. **Create Vault Instance**: Local HashiCorp Vault for secrets
2. **Generate SSH Keys**: For repository access
3. **Configure Platform Secrets**: Database passwords, API keys, etc.
4. **Set Service Accounts**: Kubernetes service accounts

#### Required Inputs
- **Vault Method**: Choose `local_vault` (recommended)
- **Data Analysis Platform**: Select your preferred BI tool
- **Data Warehouse**: Choose your data warehouse solution
- **Git Provider**: Select your Git hosting service
- **Repository URLs**: DAG and data model repositories
- **Access Method**: Deploy keys (recommended) or access tokens

#### Data Warehouse Options
- **BigQuery**: Requires GCP service account credentials
- **Snowflake**: Requires AWS/Azure credentials
- **PostgreSQL**: Uses built-in StackGres database
- **Custom**: Configure your existing data warehouse

### Phase 3: Configure Repositories

1. **Add Deploy Keys**: Copy SSH public keys to your Git repositories
2. **Verify Access**: CLI tests repository connectivity
3. **Configure Branches**: Set main branch for data models

#### Repository Setup
- **DAG Repository**: For Airflow workflows and orchestration
- **Data Repository**: For dbt models and data transformations

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

#### Kubeconfig Issues
- Verify kubeconfig file path is correct
- Check cluster connectivity with `kubectl cluster-info`
- Ensure proper cluster permissions

#### Storage Issues
- Verify storage class exists: `kubectl get storageclass`
- Check storage class is default: `kubectl get storageclass -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}'`
- Ensure sufficient storage capacity

#### Network Issues
- Check outbound internet access from pods
- Verify DNS resolution works in cluster
- Check firewall rules for required ports

#### Resource Issues
- Monitor cluster resources: `kubectl top nodes`
- Check pod resource requests/limits
- Scale cluster if needed

## 🗑️ Cleanup and Destruction

### Destroy Environment
```bash
python cli.py --destroy --destroy-confirm
```

This will:
1. **Remove Kubernetes Resources**: All Helm charts and namespaces
2. **Clean Up State**: Remove local configuration files
3. **Preserve Infrastructure**: Your cluster remains intact

### Manual Cleanup
If automatic destruction fails:
1. **Delete Namespaces**: Remove Fast.BI namespaces
2. **Remove Helm Releases**: Uninstall all Helm charts
3. **Clean Up Secrets**: Remove platform secrets

## 📚 Additional Resources

### Configuration Examples
- **On-Premise**: `cli/deployment_configuration_onprem_example.yaml`
- **Custom Storage**: Modify storage class configuration
- **Multi-Cluster**: Separate configurations for different clusters

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

## 🔧 Advanced Configuration

### Custom Storage Classes
If you need custom storage configuration:
```yaml
infrastructure_deployment:
  onprem:
    storage_class: "fast-ssd-storage"
    storage_config:
      reclaim_policy: "Retain"
      volume_binding_mode: "WaitForFirstConsumer"
```

### Network Policies
Configure network policies for enhanced security:
```yaml
infrastructure_services:
  network_policies:
    enabled: true
    default_deny: true
    allowed_namespaces: ["fastbi", "monitoring"]
```

---

**Need Help?** Check the [troubleshooting section](#monitoring-and-troubleshooting) or open an issue on GitHub.
