# Dry-Run Mode Documentation

## Overview

The dry-run mode allows you to generate all deployment configuration files and preview deployment commands without actually executing them. This is useful for:

- **Testing configurations** before actual deployment
- **Reviewing generated files** (Terraform, Helm values, Kubernetes manifests)
- **Understanding the deployment process** by seeing what commands would be executed
- **Validating inputs** without making infrastructure changes
- **Documentation purposes** - capturing deployment configurations

## Quick Start

To run the deployment in dry-run mode, simply add the `--dry-run` flag:

```bash
python cli.py --dry-run
```

Or with a configuration file:

```bash
python cli.py --config deployment-config.yaml --dry-run
```

## What Dry-Run Mode Does

### ✅ What HAPPENS in Dry-Run Mode

- **Generates all configuration files** (Terraform, Helm values, Kubernetes manifests)
- **Renders Jinja2 templates** with your configuration values
- **Creates local directory structures**
- **Generates SSH keys** for repository access
- **Encrypts infrastructure files** (Phase 6)
- **Shows preview of commands** that would be executed
- **Saves state file** for resuming later
- **Keeps all generated files** for review (no cleanup)

### ❌ What DOES NOT Happen in Dry-Run Mode

- **No cloud infrastructure provisioning** (no Terragrunt/Terraform execution)
- **No Kubernetes deployments** (no kubectl/helm commands executed)
- **No git operations** (no clone, commit, push)
- **No secret storage** (keys/secrets not saved to vault)
- **No actual service deployments**

## Phase-by-Phase Behavior

### Phase 1: Infrastructure Deployment

**What happens:**
- Generates Terragrunt/Terraform configuration files
- Renders `.hcl` files with your project configuration
- Creates directory structure: `terraform/google_cloud/terragrunt/bi-platform/`

**What is skipped:**
- `terragrunt plan` commands
- `terragrunt apply` commands
- Cloud resource provisioning

**Output example:**
```
[DRY-RUN] Would execute: terragrunt apply --auto-approve
[DRY-RUN] Would execute: terragrunt output external_ip
```

**Generated files location:**
```
terraform/google_cloud/terragrunt/bi-platform/
├── 01-vpc/
├── 02-gke-cluster/
├── 03-kubeconfig/
└── ... (all infrastructure modules)
```

### Phase 2: Secrets Generation

**What happens:**
- Generates all required secrets (passwords, tokens, API keys)
- Creates secret structure file: `/tmp/{customer}_customer_vault_structure.json`
- Automatically uses fake GCP service account JSON (no prompts)
- Generates encryption keys

**What is skipped:**
- Saving secrets to Kubernetes vault
- Vault initialization commands

**Output example:**
```
[DRY-RUN] Using fake GCP service account JSON for dry-run mode
✅ [DRY-RUN] Fake GCP service account files loaded
```

**Generated files location:**
```
/tmp/{customer}_customer_vault_structure.json
```

### Phase 3: Repository Configuration

**What happens:**
- Generates SSH keys for repository access
- Renders DAG and dbt template files
- Creates repository structure locally
- Renders CI/CD workflow files

**What is skipped:**
- Git clone operations
- Git commit operations
- Git push operations
- Deploy key configuration in remote repositories

**Output example:**
```
[DRY-RUN] Skipping git clone for repository
[DRY-RUN] Repository files generated in: /tmp/{customer}_repos_xxx/
```

**Generated files location:**
```
/tmp/{customer}_repos_{random}/
├── {customer}_data_orchestrator/
│   ├── dags/
│   └── .github/ or .gitlab-ci.yml
└── {customer}_data_model/
    ├── models/
    └── dbt_project.yml
```

### Phase 4: Infrastructure Services Deployment

**What happens:**
- Generates Helm values files for all infrastructure services
- Renders Kubernetes manifests
- Creates namespace configurations
- Generates service-specific configurations

**What is skipped:**
- Helm repository operations (`helm repo add`, `helm repo update`)
- Helm install/upgrade commands
- Kubectl apply commands
- Cluster validation (uses fake kubeconfig)

**Automatically provided in dry-run:**
- Fake kubeconfig file (no prompts)

**Output example:**
```
[DRY-RUN] Using fake kubeconfig for dry-run mode
[DRY-RUN] Would execute: helm upgrade -i cert-manager jetstack/cert-manager --version v1.18.2
[DRY-RUN] Would execute: kubectl apply -f charts/infra_services_charts/cert_manager/values_extra.yaml
```

**Generated files location:**
```
charts/infra_services_charts/
├── secret_manager/values.yaml
├── cert_manager/values.yaml
├── external_dns/values.yaml
├── traefik_lb/values.yaml
├── stackgres_postgres_db/values.yaml
├── log_collector/values.yaml
├── services_monitoring/values.yaml
└── ... (all service charts)
```

### Phase 5: Data Services Deployment

**What happens:**
- Generates Helm values files for all data services
- Renders application configurations
- Creates ingress configurations
- Generates database schemas

**What is skipped:**
- Helm install/upgrade commands
- Kubectl apply commands
- Database initialization
- Service health checks
- Token fetching from Kubernetes secrets

**Output example:**
```
[DRY-RUN] Would execute: helm upgrade -i data-orchestrator oci://registry/data-orchestrator --version 1.2.3
[DRY-RUN] Skipping ARGO_WORKFLOW_SA_TOKEN fetch - secrets cannot be accessed in dry-run mode
```

**Generated files location:**
```
charts/data_services_charts/
├── cicd_workload_runner/values.yaml
├── data_lineage/values.yaml
├── data_catalog/values.yaml
├── data_quality/values.yaml
└── ... (all data service charts)
```

### Phase 6: Deployment Finalization

**What happens:**
- Collects all infrastructure files
- Generates encryption key
- Encrypts sensitive files
- Prepares deployment package locally

**What is skipped:**
- Git clone of deployment repository
- Git commit operations
- Git push operations
- Saving encryption key to vault
- Port-forward to vault

**Output example:**
```
[DRY-RUN] Skipping git clone for repository
[DRY-RUN] Encryption key generated: {key}
[DRY-RUN] Skipping encryption key save to vault
[DRY-RUN] Would commit and push changes to repository
[DRY-RUN] Infrastructure files available for review at: /tmp/{customer}_infrastructure_deployment_files
```

**Generated files location:**
```
/tmp/{customer}_infrastructure_deployment_files/
├── terraform/
├── charts/
├── manifests/
└── README.md
```

## Command Preview Format

All commands that would be executed are shown with the `[DRY-RUN]` prefix:

```
[DRY-RUN] Would execute: terragrunt apply --auto-approve
[DRY-RUN] Would execute: helm upgrade -i traefik traefik/traefik --version 37.0.0
[DRY-RUN] Would execute: kubectl apply -f manifest.yaml
[DRY-RUN] Would execute: git clone https://github.com/example/repo.git
```

## Generated Files Summary

After a successful dry-run, you'll have the following files available for review:

### Configuration Files
| Type | Location | Description |
|------|----------|-------------|
| Terragrunt | `terraform/google_cloud/terragrunt/bi-platform/` | Infrastructure as Code configurations |
| Helm Values | `charts/infra_services_charts/` | Infrastructure service configurations |
| Helm Values | `charts/data_services_charts/` | Data service configurations |
| Secrets | `/tmp/{customer}_customer_vault_structure.json` | All generated secrets and credentials |
| Repository | `/tmp/{customer}_repos_{random}/` | DAG and dbt model templates |
| Deployment | `/tmp/{customer}_infrastructure_deployment_files/` | Encrypted deployment package |

### Review Checklist

After a dry-run, review these key files:

1. **Terraform Configurations**
   - Check resource naming conventions
   - Verify CIDR blocks and network configuration
   - Review IAM permissions and service accounts

2. **Helm Values**
   - Verify image repositories and versions
   - Check resource limits (CPU, memory)
   - Review ingress configurations
   - Validate storage configurations

3. **Secrets**
   - Review generated passwords (complexity, length)
   - Check API tokens and keys
   - Verify database credentials

4. **Repository Templates**
   - Check DAG templates
   - Review dbt model structure
   - Verify CI/CD workflow configurations

## Interactive Mode with Dry-Run

Dry-run mode works seamlessly with interactive mode. The CLI will still ask all configuration questions:

```bash
python cli.py --dry-run
```

You'll be prompted for:
- Customer name
- Domain name
- Cloud provider settings
- Git repository URLs
- Service configurations

All prompts work normally - dry-run only affects command execution, not configuration collection.

## Non-Interactive Mode with Dry-Run

You can also use dry-run with a pre-configured YAML file:

```bash
python cli.py --config my-deployment.yaml --dry-run
```

This is useful for:
- CI/CD pipelines (validate configurations)
- Automated testing
- Documentation generation

## Fake Resources in Dry-Run Mode

To prevent errors when actual resources don't exist, dry-run automatically provides fake resources:

| Resource | Fake Location | Purpose |
|----------|---------------|---------|
| GCP Service Account | `utils/templates/dry_run/gcp_sa.json` | BigQuery authentication |
| Kubeconfig | `utils/templates/dry_run/kubeconfig.yaml` | Kubernetes cluster access |

These files are automatically used without prompting the user.

## State File Handling

Dry-run saves state to: `cli/state/deployment_state.json`

This allows you to:
- Resume from a specific phase
- Review configuration choices
- Compare multiple dry-runs

## Converting Dry-Run to Actual Deployment

After reviewing dry-run output, deploy for real:

**Option 1: Run same command without --dry-run**
```bash
# First: Dry-run
python cli.py --dry-run

# Then: Actual deployment (uses saved state)
python cli.py
```

**Option 2: Use state file**
```bash
# First: Dry-run with config
python cli.py --config deployment.yaml --dry-run

# Then: Actual deployment with same config
python cli.py --config deployment.yaml
```

**Option 3: Phase-by-phase deployment**
```bash
# Review Phase 1 in dry-run
python cli.py --dry-run --phase 1

# Deploy Phase 1 for real
python cli.py --phase 1

# Continue with other phases...
```

## Troubleshooting

### Issue: "Module not found" errors

**Cause:** Missing Python dependencies

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: Files not generated in expected location

**Cause:** Permissions or path issues

**Solution:**
- Check write permissions in `/tmp/` directory
- Verify working directory is project root
- Check disk space availability

### Issue: Jinja2 template rendering errors

**Cause:** Invalid configuration values

**Solution:**
- Review configuration file format
- Check for missing required parameters
- Validate YAML syntax (if using config file)

### Issue: State file conflicts

**Cause:** Previous dry-run state exists

**Solution:**
```bash
# Remove old state file
rm cli/state/deployment_state.json

# Run fresh dry-run
python cli.py --dry-run
```

## Best Practices

### 1. Always Dry-Run First
```bash
# Test configuration before deploying
python cli.py --config prod-deployment.yaml --dry-run

# Review generated files
ls -la terraform/google_cloud/terragrunt/bi-platform/

# Deploy for real
python cli.py --config prod-deployment.yaml
```

### 2. Version Control Generated Configs

Save dry-run outputs for documentation:
```bash
# Run dry-run
python cli.py --dry-run

# Copy generated configs to version control
mkdir -p deployment-configs/$(date +%Y%m%d)
cp -r terraform/ deployment-configs/$(date +%Y%m%d)/
cp -r charts/ deployment-configs/$(date +%Y%m%d)/
```

### 3. Use Dry-Run in CI/CD

Example GitHub Actions:
```yaml
name: Validate Deployment Configuration
on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Dry-run deployment
        run: python cli.py --config deployment.yaml --dry-run
      - name: Upload generated configs
        uses: actions/upload-artifact@v2
        with:
          name: deployment-configs
          path: |
            terraform/
            charts/
```

### 4. Document Your Configuration

After successful dry-run, document what was generated:
```bash
# Generate deployment manifest
python cli.py --dry-run 2>&1 | tee deployment-manifest.txt

# Review and commit
git add deployment-manifest.txt
git commit -m "Add deployment configuration manifest"
```

## Advanced Usage

### Selective Phase Dry-Run

Test individual phases:

```bash
# Test only infrastructure generation
python cli.py --dry-run --phase 1

# Test only secrets generation
python cli.py --dry-run --phase 2

# Test repository configuration
python cli.py --dry-run --phase 3
```

### Combining with Other Flags

```bash
# Dry-run with specific state file
python cli.py --dry-run --state-file my-deployment-state.json

# Dry-run with non-interactive mode
python cli.py --config deployment.yaml --non-interactive --dry-run

# Dry-run showing configuration
python cli.py --dry-run --show-config
```

## Limitations

1. **No Actual Validation**
   - Dry-run doesn't validate cloud credentials
   - Repository URLs are not checked for existence
   - Service versions are not verified in registries

2. **Mock Success**
   - All commands return success (no error simulation)
   - Doesn't test actual deployment failures

3. **No Cluster State**
   - Can't check existing resources
   - Can't validate upgrade paths

4. **Time Estimates**
   - Dry-run completes much faster than actual deployment
   - Doesn't reflect real deployment time

## Getting Help

If you encounter issues with dry-run mode:

1. Check this documentation
2. Review logs: Look for `[DRY-RUN]` prefixed messages
3. Examine generated files in `/tmp/` directories
4. Check state file: `cli/state/deployment_state.json`
5. Open an issue with dry-run output attached

## Example Workflow

Complete example from start to finish:

```bash
# 1. Initial dry-run to test configuration
python cli.py --dry-run

# 2. Review generated files
ls -la terraform/google_cloud/terragrunt/bi-platform/
cat /tmp/mycompany_customer_vault_structure.json

# 3. Fix any configuration issues
vim cli/config/infrastructure_services_config.json

# 4. Re-run dry-run to verify fixes
python cli.py --dry-run

# 5. When satisfied, run actual deployment
python cli.py

# 6. Save dry-run output for documentation
python cli.py --dry-run > deployment-plan.txt
git add deployment-plan.txt
git commit -m "Add deployment plan documentation"
```

## Summary

Dry-run mode is a powerful tool for:
- 🧪 Testing configurations safely
- 📋 Generating documentation
- 🔍 Understanding the deployment process
- ✅ Validating inputs before deployment
- 🎓 Learning the platform architecture

Use it liberally - it's fast, safe, and helps prevent deployment mistakes!

---

**Next Steps:**
- Review [GCP Deployment Guide](gcp-deployment.md) for full deployment instructions
- Check [Deployment Overview](deployment-overview.md) for architecture details
- See [AWS Deployment](aws-deployment.md) or [Azure Deployment](azure-deployment.md) for other cloud providers

