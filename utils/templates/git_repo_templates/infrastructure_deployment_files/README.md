# Infrastructure Deployment Files Repository

This repository contains encrypted infrastructure deployment files for the Fast BI Platform. These files are used to manage and deploy infrastructure components across different cloud providers.

## File Organization

### Directory Structure
```
.
├── core-infrastructure-deployment/
│   ├── bi-platform/
│   │   ├── terragrunt.hcl
│   │   ├── backend.tf
│   │   ├── env.yaml
│   │   ├── 00-create-ou-folder/
│   │   │   ├── terragrunt.hcl
│   │   │   └── .terraform/
│   │   │       └── {customer}/
│   │   │           └── 00-create-ou-folder/
│   │   │               ├── terraform.tfstate
│   │   │               └── terraform.tfstate.backup
│   │   ├── 01-create-project/
│   │   │   ├── terragrunt.hcl
│   │   │   └── .terraform/
│   │   │       └── {customer}/
│   │   │           └── 01-create-project/
│   │   │               ├── terraform.tfstate
│   │   │               └── terraform.tfstate.backup
│   │   └── ... (other modules)
│   └── .gitignore
├── k8s-infrastructure-services-deployment/
│   ├── vault/
│   │   └── values.yaml
│   ├── cert_manager/
│   │   ├── values.yaml
│   │   └── values_extra.yaml
│   ├── idp_sso_manager/
│   │   ├── values.yaml
│   │   └── {customer}_realm.json
│   └── ... (other services)
├── k8s-data-platform-services-deployment/
│   ├── cicd_workload_runner/
│   │   ├── values.yaml
│   │   └── values_extra.yaml
│   ├── data_analysis/
│   │   ├── values.yaml
│   │   ├── postgresql_values.yaml
│   │   ├── lightdash/
│   │   │   └── values.yaml
│   │   ├── superset/
│   │   │   └── values.yaml
│   │   └── metabase/
│   │       └── values.yaml
│   └── ... (other services)
├── encrypt_files.py
├── decrypt_files.py
└── README.md
```

### File Naming Conventions
- **Terraform State Files**: Stored in `.terraform/{customer}/{module-name}/` directories
- **Helm Values Files**: Named `values.yaml` for basic configuration, `values_extra.yaml` for additional settings
- **Service-Specific Files**: Named according to service requirements (e.g., `{customer}_realm.json` for Keycloak)
- **Database Configurations**: Named `postgresql_values.yaml` for PostgreSQL-specific settings
- **OAuth2 Proxy Configurations**: Named `oauth2proxy_values.yaml` for authentication proxy settings

## Repository Structure

The repository is organized into three main directories:

1. **Core Infrastructure** (`core-infrastructure-deployment/`)
   - Contains encrypted Terraform/Terragrunt configuration files
   - Cloud provider-specific infrastructure components
   - Network, security, and access configurations
   - Service account and IAM configurations
   - DNS and networking setup
   - **Terraform State Files**: When using local state backend, includes encrypted `.terraform` directories with `terraform.tfstate` and `terraform.tfstate.backup` files

2. **Kubernetes Core Services** (`k8s-infrastructure-services-deployment/`)
   - Encrypted Helm values files for core Kubernetes services
   - Security and access management (cert-manager, Keycloak)
   - Network and DNS management (external-dns, Traefik)
   - Storage solutions (MinIO)
   - Monitoring and logging (Prometheus, Grafana)
   - CI/CD and workflows (Argo Workflows)
   - Cluster management tools

3. **Kubernetes Data Services** (`k8s-data-platform-services-deployment/`)
   - Encrypted Helm values files for data-related services
   - Data replication and integration (Airbyte)
   - Data orchestration (Apache Airflow)
   - Data governance (DataHub, Elasticsearch)
   - Data modeling and analysis (JupyterHub, Superset, Lightdash)
   - Data catalog and quality tools
   - User interface components

## Terraform State Management

### Local State Backend
When using local state backend (`terraform_state: local`), the following files are included:
- `terraform.tfstate` - Current Terraform state
- `terraform.tfstate.backup` - Backup of previous Terraform state
- These files are stored in customer-specific directories: `.terraform/{customer}/{module-name}/`

### Remote State Backend
When using remote state backend (`terraform_state: remote`), state files are stored in cloud storage (GCS/S3/Azure Blob) and are not included in this repository.

## Prerequisites

- Python 3.8 or higher
- `cryptography` package (`pip install cryptography`)
- `rich` package (`pip install rich`) for enhanced CLI output
- Access to the encryption key (stored in vault)
- Appropriate cloud provider credentials
- Kubernetes cluster access
- Helm v3.x
- Terragrunt
- kubectl configured with cluster access

## Working with Encrypted Files

### Decryption

To decrypt the files, use the provided `decrypt_files.py` script:

```bash
# Get the encryption key from vault
# For local vault:
kubectl get secret vault-init -n vault -o jsonpath='{.data.root-token}' | base64 --decode > vault_token.txt
# Then use the vault token to get the encryption key:
curl -H "X-Vault-Token: $(cat vault_token.txt)" \
  http://localhost:8200/v1/secret/data/infrastructure_value_files_encryption_key \
  | jq -r '.data.data.value' > encryption_key.txt

# For external vault (Infisical):
# The key is stored in your Infisical vault under the path: /infrastructure_value_files_encryption_key

# Decrypt files with verbose output
python decrypt_files.py $(cat encryption_key.txt) -v
```

**Note**: Some files may show "Invalid token" errors if they were not properly encrypted or if they are empty files. This is normal and these files will be skipped during decryption.

### Encryption

To encrypt new or modified files, use the provided `encrypt_files.py` script:

```bash
# Encrypt files with verbose output
python encrypt_files.py <encryption_key> -v
```

## Manual Infrastructure Updates

### Core Infrastructure Updates

1. Decrypt the files using the provided script
2. Make necessary modifications to the configuration files
3. Encrypt the modified files
4. Commit and push the changes
5. Apply the changes using Terragrunt:

```bash
# Navigate to the appropriate directory
cd bi-platform

# Initialize Terragrunt
terragrunt init

# Plan the changes
terragrunt plan

# Apply the changes
terragrunt apply
```

### Kubernetes Core Services Updates

1. Decrypt the files using the provided script
2. Make necessary modifications to the Helm values files
3. Encrypt the modified files
4. Commit and push the changes
5. Apply the changes using Helm:

**Note**: Each `values.yaml` file contains the correct version at the top of the file. You can also find the latest version by running `helm search repo <chart-repo>/<chart-name> --versions`.

```bash
# Security and Access Management
helm upgrade -i vault hashicorp/vault \
  --version <version_from_values.yaml> \
  --namespace vault \
  --wait \
  --values secret_manager/values.yaml \
  --kubeconfig kubeconfig.yaml

kubectl apply -f secret_manager/values_extra.yaml --namespace vault --kubeconfig kubeconfig.yaml

helm upgrade -i secret-operator external-secrets/external-secrets \
  --version <version_from_values.yaml> \
  --namespace vault \
  --wait \
  --values secret_manager_operator/values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i cert-manager jetstack/cert-manager \
  --version <version_from_values.yaml> \
  --namespace cert-manager \
  --wait \
  --values cert_manager/values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i idp-sso-manager bitnami/keycloak \
  --version <version_from_values.yaml> \
  --namespace sso-keycloak \
  --wait \
  --values idp_sso_manager/values.yaml \
  --kubeconfig kubeconfig.yaml

# Network and DNS Management
helm upgrade -i external-dns bitnami/external-dns \
  --version <version_from_values.yaml> \
  --namespace external-dns \
  --wait \
  --values external_dns/values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i traefik-ingress traefik/traefik \
  --version <version_from_values.yaml> \
  --namespace traefik-ingress \
  --wait \
  --values traefik_lb/values.yaml \
  --kubeconfig kubeconfig.yaml

# Global Database PostgreSQL Stackgres.io
helm upgrade -i stackgres-postgresql-operator stackgres-charts/stackgres-operator \
  --version <version_from_values.yaml> \
  --namespace global-postgresql \
  --wait \
  --values stackgres_postgres_db/values.yaml \
  --kubeconfig kubeconfig.yaml

# Monitoring and Logging
helm upgrade -i prometheus prometheus-community/prometheus \
  --version <version_from_values.yaml> \
  --namespace logging \
  --wait \
  --values log_collector/values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i monitoring grafana/grafana \
  --version <version_from_values.yaml> \
  --namespace monitoring \
  --values services_monitoring/values.yaml \
  --kubeconfig kubeconfig.yaml

# Cluster Management
helm upgrade -i k8s-cleanup lwolf-charts/kube-cleanup-operator \
  --version <version_from_values.yaml> \
  --namespace k8s-cleanup \
  --wait \
  --values cluster_cleaner/values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i pvc-autoscaler kubesphere/pvc-autoresizer \
  --version <version_from_values.yaml> \
  --namespace pvc-autoresizer \
  --wait \
  --values pvc_autoscaller/values.yaml \
  --kubeconfig kubeconfig.yaml

kubectl apply -f pvc_autoscaller/values_extra.yaml --namespace pvc-autoscaler --kubeconfig kubeconfig.yaml
```

### Kubernetes Data Services Updates

1. Decrypt the files using the provided script
2. Make necessary modifications to the Helm values files
3. Encrypt the modified files
4. Commit and push the changes
5. Apply the changes using Helm:

**Note**: Each `values.yaml` file contains the correct version at the top of the file. You can also find the latest version by running `helm search repo <chart-repo>/<chart-name> --versions`.

```bash
# CI/CD and Workflows
## Based on provider helm charts (gitlab: gitlab/gitlab-runner, github: actions-runner-controller/actions-runner-controller...)
helm upgrade -i fastbi-cicd-trigger-runner gitlab/gitlab-runner \
  --version <version_from_values.yaml> \
  --namespace cicd-workload-runner \
  --wait \
  --values cicd_workload_runner/values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i cicd-workflows argo/argo-workflows \
  --version <version_from_values.yaml> \
  --namespace cicd-workflows \
  --wait \
  --values argo_workflows/values.yaml \
  --kubeconfig kubeconfig.yaml

# Storage Solutions
helm upgrade -i object-storage-operator minio/operator \
  --version <version_from_values.yaml> \
  --namespace minio \
  --wait \
  --values object_storage_operator/operator_values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i object-storage minio/tenant \
  --version <version_from_values.yaml> \
  --namespace minio \
  --wait \
  --values object_storage_operator/values.yaml \
  --kubeconfig kubeconfig.yaml

# Data Replication
helm upgrade -i data-replication airbyte/airbyte \
  --version <version_from_values.yaml> \
  --namespace data-replication \
  --wait \
  --values data_replication/values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i data-replication-oauth oauth2-proxy/oauth2-proxy \
  --version <version_from_values.yaml> \
  --namespace data-replication \
  --wait \
  --values data_replication/oauth2proxy_values.yaml \
  --kubeconfig kubeconfig.yaml


# Data Orchestration
helm upgrade -i data-orchestration apache-airflow/airflow \
  --version <version_from_values.yaml> \
  --namespace data-orchestration \
  --values data_orchestration/values.yaml \
  --kubeconfig kubeconfig.yaml

# Data Governance
helm upgrade -i data-governance-eck-es-operator elastic/eck-operator \
  --version <version_from_values.yaml> \
  --namespace data-governance \
  --wait \
  --timeout 1h \
  --values data_governance/eck_operator_values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i data-governance-eck-es elastic/eck-elasticsearch \
  --version <version_from_values.yaml> \
  --namespace data-governance \
  --wait \
  --timeout 1h \
  --values data_governance/eck_es_values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i data-governance-sys datahub/datahub-prerequisites \
  --version <version_from_values.yaml> \
  --namespace data-governance \
  --wait \
  --timeout 1h \
  --values data_governance/dh_prerequisites_values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i data-governance datahub/datahub \
  --version <version_from_values.yaml> \
  --namespace data-governance \
  --wait \
  --timeout 1h \
  --values data_governance/dh_values.yaml \
  --kubeconfig kubeconfig.yaml

# Data Modeling and Analysis
helm upgrade -i data-modeling-hub jupyterhub/jupyterhub \
  --version <version_from_values.yaml> \
  --namespace data-modeling \
  --wait \
  --values data_modeling/values.yaml \
  --kubeconfig kubeconfig.yaml

## Based on Analysis services (Lighdash: lightdash/lightdash, Superset: superset/superset, Metabase: metabase/metabase )
helm upgrade -i data-analysis-hub superset/superset \
  --version < your_version_here > \
  --set image.tag=< your_version_here > \
  --namespace data-analysis \
  --wait \
  --timeout 1h \
  --values data_analysis/superset/values.yaml

# Data Catalog and Quality
helm upgrade -i data-dcdq-metacollect-hub kube-core/raw \
  --version <version_from_values.yaml> \
  --namespace data-dcdq-metacollect \
  --wait \
  --values data_dcdq_metacollect/values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i data-catalog-oauth oauth2-proxy/oauth2-proxy \
  --version <version_from_values.yaml> \
  --namespace data-catalog \
  --wait \
  --values data_dcdq_metacollect/data_catalog/oauth2proxy_values.yaml \
  --kubeconfig kubeconfig.yaml

helm upgrade -i data-quality-oauth oauth2-proxy/oauth2-proxy \
  --version <version_from_values.yaml> \
  --namespace data-quality \
  --wait \
  --values data_dcdq_metacollect/data_quality/oauth2proxy_values.yaml \
  --kubeconfig kubeconfig.yaml

# Data Platform Backup
helm upgrade -i data-platform-backup vmware-tanzu/velero \
  --version <version_from_values.yaml> \
  --namespace data-platform-backup \
  --wait \
  --values data_platform_backup/values.yaml \
  --kubeconfig kubeconfig.yaml

# Data DBT Server
helm upgrade -i data-dbt-server kube-core/raw \
  --version <version_from_values.yaml> \
  --namespace data-dbt-server \
  --wait \
  --values data_dbt_server/values.yaml \
  --kubeconfig kubeconfig.yaml

# User Console
helm upgrade -i data-platform-user-console kube-core/raw \
  --version <version_from_values.yaml> \
  --namespace user-console \
  --wait \
  --values user_console/values.yaml
```

## Troubleshooting

### Common Issues

1. **Decryption/Encryption Issues**
   - Verify the encryption key is correct
   - Ensure the key is properly formatted
   - Check file permissions
   - Use verbose mode (-v) for detailed logging
   - Some files may show "Invalid token" errors - this is normal for empty or non-encrypted files

2. **Terraform State File Issues**
   - Verify that Terraform state files exist in the expected locations
   - Check that the customer name in the directory structure matches your deployment
   - Ensure state files are not corrupted
   - For local state: Check `.terraform/{customer}/{module-name}/` directories
   - For remote state: Verify cloud storage bucket access

3. **Terragrunt/Helm Errors**
   - Verify cloud provider credentials
   - Check Kubernetes cluster access
   - Validate configuration files
   - Check service dependencies

4. **Service-Specific Issues**
   - Check pod status: `kubectl get pods -n <namespace>`
   - View logs: `kubectl logs -n <namespace> <pod-name>`
   - Describe resources: `kubectl describe -n <namespace> <resource-type> <resource-name>`
   - Check persistent volumes: `kubectl get pv,pvc -n <namespace>`

### Getting Help

For issues related to:
- Infrastructure deployment: Contact the infrastructure team
- Kubernetes services: Contact the platform team
- Security concerns: Contact the security team
- Data services: Contact the data platform team

## Best Practices

1. **File Management**
   - Always encrypt files before committing
   - Keep backup copies of important configurations
   - Document any custom configurations
   - Use version control for all changes

2. **Updates**
   - Test changes in a non-production environment first
   - Follow the change management process
   - Document all changes made
   - Consider service dependencies when updating

3. **Security**
   - Regularly rotate encryption keys
   - Audit access to the repository
   - Monitor for unauthorized changes
   - Follow the principle of least privilege

4. **Maintenance**
   - Regular updates for security and stability
   - Monitor resource usage
   - Backup critical data
   - Document all customizations

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Terragrunt Documentation](https://terragrunt.gruntwork.io/)

## Support

For support and questions, please contact:
- Infrastructure Team: infrastructure@example.com
- Platform Team: platform@example.com
- Security Team: security@example.com
- Data Platform Team: data-platform@example.com

## Service Dependencies

### Core Infrastructure Dependencies
- Vault must be installed first as it's used for secret management
- cert-manager must be installed before services requiring TLS certificates
- external-dns requires DNS provider credentials
- traefik-ingress should be installed before services needing ingress routes
- Keycloak requires a database (included in the chart)
- Stackgres PostgreSQL operator should be installed before services requiring databases

### Data Services Dependencies
- Airbyte requires PostgreSQL for state management
- DataHub requires Elasticsearch and PostgreSQL
- Argo Workflows requires PostgreSQL for workflow state
- All services require proper network and storage configurations
- Data Catalog and Quality services require OAuth2 proxy
- Analysis services (Lightdash/Superset/Metabase) require PostgreSQL

## Version Management

### Finding Correct Versions

#### Method 1: Check Values Files
Each `values.yaml` file contains the correct version at the top of the file. Look for comments like:
```yaml
# Helm Chart version 0.45.22
# Helm Chart version 1.7.2
```

#### Method 2: Use Helm Search Commands
You can find the latest available versions using Helm search commands:

```bash
# Search for specific chart versions
helm search repo argo/argo-workflows --versions
helm search repo hashicorp/vault --versions
helm search repo jetstack/cert-manager --versions
helm search repo bitnami/keycloak --versions
helm search repo airbyte/airbyte --versions
helm search repo apache-airflow/airflow --versions
helm search repo datahub/datahub --versions
helm search repo jupyterhub/jupyterhub --versions
helm search repo oauth2-proxy/oauth2-proxy --versions
helm search repo minio/operator --versions
helm search repo minio/tenant --versions
helm search repo elastic/eck-operator --versions
helm search repo elastic/eck-elasticsearch --versions
helm search repo prometheus-community/prometheus --versions
helm search repo grafana/grafana --versions
helm search repo traefik/traefik --versions
helm search repo bitnami/external-dns --versions
helm search repo stackgres-charts/stackgres-operator --versions
helm search repo external-secrets/external-secrets --versions
helm search repo gitlab/gitlab-runner --versions
helm search repo lwolf-charts/kube-cleanup-operator --versions
helm search repo kubesphere/pvc-autoresizer --versions
helm search repo kube-core/raw --versions
```

#### Method 3: Official Documentation
1. **Core Services**:
   - Check the official Helm chart repositories for the latest stable versions
   - For custom charts, refer to the internal chart repository
   - Version compatibility matrix is maintained in the platform documentation

2. **Data Services**:
   - Airbyte: https://airbyte.io/docs/upgrading-airbyte
   - Apache Airflow: https://airflow.apache.org/docs/apache-airflow/stable/installation/index.html
   - DataHub: https://datahubproject.io/docs/quickstart
   - Analysis Tools: Check respective documentation for version compatibility

3. **Infrastructure Components**:
   - Vault: https://www.vaultproject.io/docs/upgrading
   - cert-manager: https://cert-manager.io/docs/installation/supported-releases/
   - Traefik: https://doc.traefik.io/traefik/operations/upgrading/

### Version Update Process
1. Test new versions in a non-production environment
2. Update versions in the values files (replace the version comment at the top)
3. Document version changes in the commit message
4. Follow the upgrade procedures for each service

### Using Dynamic Version References
In the deployment commands, replace `<version_from_values.yaml>` with the actual version found in the values file. For example:
- If `values.yaml` shows `# Helm Chart version 0.45.22`, use `--version 0.45.22`
- If `values.yaml` shows `# Helm Chart version 1.7.2`, use `--version 1.7.2`
