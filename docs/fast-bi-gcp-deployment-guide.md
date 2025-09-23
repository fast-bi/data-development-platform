# 🚀 Fast.BI Data Development Platform - GCP Deployment Guide

> **Welcome to Fast.BI!** This guide will walk you through deploying a complete data development platform on Google Cloud Platform using our interactive CLI tool. The entire process takes about 30-45 minutes and creates a production-ready data platform with modern tools like Apache Airflow, dbt, Superset, and more.

## 📋 Table of Contents

- [🎯 Platform Overview](#-platform-overview)
- [📋 Prerequisites](#-prerequisites)
- [☁️ GCP Account Setup](#️-gcp-account-setup)
- [🔧 Git Repository Setup](#-git-repository-setup)
- [🔐 Keycloak Realm Setup](#-keycloak-realm-setup)
- [🚀 Step-by-Step Deployment](#-step-by-step-deployment)
- [🌐 Access Your Platform](#-access-your-platform)
- [🗑️ Cleanup & Cost Management](#️-cleanup--cost-management)
- [🔍 Troubleshooting](#-troubleshooting)

## 🎯 Platform Overview

Fast.BI creates a complete data development platform with:

- **🔧 Infrastructure Services:** Kubernetes cluster, load balancer, DNS, certificates, monitoring
- **📊 Data Services:** Apache Airflow, dbt, Superset, DataHub, MinIO, PostgreSQL
- **🔐 Security:** Keycloak SSO, encrypted secrets, secure networking
- **📈 Monitoring:** Prometheus, Grafana, centralized logging
- **🔄 CI/CD:** GitLab/GitHub runners, automated deployments

## 📋 Prerequisites

### Required Tools

- **Python ≥3.9** - For running the Fast.BI CLI
- **kubectl** - Kubernetes command-line tool
- **gcloud CLI** - Google Cloud command-line tool
- **Terraform** - Infrastructure as Code tool
- **Terragrunt** - Terraform wrapper
- **Helm** - Kubernetes package manager

### Required Accounts & Resources

- **GCP Account** with billing enabled
- **Custom Domain** (e.g., yourcompany.com)
- **GitHub/GitLab Account** for repositories
- **Keycloak Instance** (or use our hosted version)

## ☁️ GCP Account Setup

### Step 1: Create GCP Account

Visit [cloud.google.com](https://cloud.google.com) and sign up for a new account.

> **✅ Free Credits Available!** New GCP accounts receive $300 in free credits, which is enough to run Fast.BI for approximately 14 days for testing and evaluation.

### Step 2: Enable Billing

You must enable billing to use the Fast.BI CLI, even with free credits.

1. Go to the [GCP Billing Console](https://console.cloud.google.com/billing)
2. Click "Link a billing account" or create a new one
3. Add a payment method (required even for free tier)
4. Note your **Billing Account ID** (format: XXXXXX-XXXXXX-XXXXXX)

### Step 3: Install gcloud CLI

```bash
# macOS (using Homebrew)
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows
# Download from: https://cloud.google.com/sdk/docs/install
```

### Step 4: Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
```

## 🔧 Git Repository Setup

> **⚠️ Important:** You need to create two Git repositories before starting the deployment. These are mandatory for the platform to function.

### Step 1: Create Data Models Repository

This repository will store your dbt models and data transformations.

- Create a new repository in GitHub/GitLab (e.g., `dbt-data-models`)
- Initialize with a basic dbt project structure
- Note the repository URL (e.g., `https://github.com/mycompany/dbt-data-models.git`)

### Step 2: Create Data Orchestration Repository

This repository will store your Airflow DAGs and workflow definitions.

- Create a new repository in GitHub/GitLab (e.g., `data-orchestration-dags`)
- Initialize with a basic Airflow project structure
- Note the repository URL (e.g., `https://github.com/mycompany/data-orchestration-dags.git`)

### Step 3: Configure Deploy Keys (Recommended)

Deploy keys provide secure, read-only access to your repositories.

1. Go to your repository settings
2. Navigate to "Deploy keys" or "SSH keys"
3. Click "Add deploy key"
4. Give it a title (e.g., "Fast.BI Platform Access")
5. Copy the SSH public key that the CLI will generate
6. Paste it into the deploy key field
7. Enable "Write access" if needed for CI/CD

## 🔐 Keycloak Realm Setup

### Step 1: Access Keycloak Admin Console

After Phase 4 completes, you'll access Keycloak at: `https://login.{customer}.{domain}`

### Step 2: Import Realm Configuration

1. Log in to Keycloak admin console
2. Click "Import" in the realm dropdown
3. Upload the generated realm file from the CLI
4. Configure your organization's administrator user

## 🚀 Step-by-Step Deployment

### Step 1: Clone the Repository

```bash
git clone https://github.com/fast-bi/data-development-platform.git
cd data-development-platform
```

### Step 2: Start the CLI

```bash
python cli.py
```

## Phase 1: Infrastructure Deployment

The CLI will guide you through the following configuration:

**Basic Configuration:**
- Customer tenant name: `mycompany`
- Admin email: `admin@mycompany.com`
- Cloud provider: `gcp`
- Project region: `us-central1`
- Domain name: `mycompany.com`

**GCP Infrastructure Configuration:**
- Deployment type: `basic`
- GCP billing account ID: `01AXXX-XXXX-XXXX`
- GCP parent folder ID: `[Leave empty if not using folders]`
- Whitelisted IP addresses: `[Leave empty for 0.0.0.0/0]`

**State Management Configuration:**
- Terraform state backend type: `local` (Infrastructure files saved locally)

**GKE Deployment Type Configuration:**
- GKE deployment type: `zonal` (Single zone - cheaper, faster, good for demos/dev)

**What Gets Created:**
- GCP Project: `fast-bi-mycompany`
- VPC Network with subnets
- GKE Cluster with node pools
- Firewall rules and load balancer
- Service accounts for platform services

## Phase 2: Generate Platform Secrets

**Secrets Generation Configuration:**
- Vault method: `local_vault`
- Data analysis platform: `superset`
- Data warehouse platform: `bigquery`
- Orchestrator platform: `Airflow`
- Git provider: `gitlab`

**Secrets Generated:**
- SSH keys for repository access
- Database passwords and credentials
- API keys and service account tokens
- Platform configuration secrets

## Phase 3: Configure Repositories

**Repository Configuration:**
- Data models repository URL: `https://github.com/mycompany/dbt-data-models.git`
- Data orchestration repository URL: `https://github.com/mycompany/data-orchestration-dags.git`

> **⚠️ IMPORTANT:** Add the generated SSH public key as a deploy key to BOTH repositories!

**Repository Setup Required:**
1. Copy the SSH public key shown in the CLI
2. Go to your GitHub/GitLab repository settings
3. Add the key as a deploy key with read/write access
4. Repeat for both repositories

## Phase 4: Deploy Infrastructure Services

**Infrastructure Services Deployed:**
- ✅ 1.0_secret_operator - Deployed successfully
- ✅ 2.0_cert_manager - Deployed successfully
- ✅ 3.0_external_dns - Deployed successfully
- ✅ 4.0_traefik_lb - Deployed successfully
- ✅ 5.0_stackgres_postgresql - Deployed successfully
- ✅ 6.0_log_collector - Deployed successfully
- ✅ 7.0_services_monitoring - Deployed successfully
- ✅ 8.0_cluster_cleaner - Deployed successfully
- ✅ 9.0_idp_sso_manager - Deployed successfully
- ✅ 10.0_cluster_pvc_autoscaller - Deployed successfully

> **💡 Keycloak Setup Required:** After this phase completes, you'll need to import the realm configuration into Keycloak. The CLI will provide the realm file and access URL.

## Phase 5: Deploy Data Services

**Data Services Deployed:**
- ✅ 1.0_cicd_workload_runner - Deployed successfully
- ✅ 2.0_object_storage_operator - Deployed successfully
- ✅ 3.0_data-cicd-workflows - Deployed successfully
- ✅ 4.0_data_replication - Deployed successfully
- ✅ 5.0_data_orchestration - Deployed successfully
- ✅ 6.0_data_modeling - Deployed successfully
- ✅ 7.0_data_dcdq_meta_collect - Deployed successfully
- ✅ 8.0_data_analysis - Deployed successfully
- ✅ 9.0_data_governance - Deployed successfully
- ✅ 10.0_user_console - Deployed successfully

**Data Platform Components:**
- **Apache Airflow:** Workflow orchestration and scheduling
- **dbt:** Data transformation and modeling
- **Superset:** Business intelligence and visualization
- **DataHub:** Data catalog and governance
- **MinIO:** S3-compatible object storage
- **PostgreSQL:** Metadata and configuration database

## Phase 6: Finalize Deployment

**Deployment Finalization Configuration:**
- Git repository URL for deployment files: `https://github.com/mycompany/fast-bi-deployment.git`
- Git access token: `[Your GitHub Personal Access Token]`
- Cleanup local temporary files: `No`

**🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!**

**Deployed Services:**
- **🔧 Infrastructure Services:** All 10 services deployed
- **📊 Data Services:** All 10 services deployed

**Access Information:**
- IDP Console: `https://login.mycompany.mycompany.com`
- Fast.BI Platform: `https://mycompany.mycompany.com`

> **🔐 ENCRYPTION KEY**
> 
> **⚠️ IMPORTANT: Save this encryption key securely!**
> 
> Deployment files in the repository are encrypted for security. You will need this key to decrypt the files later.
> 
> Generated encryption key: `Ycs_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX=`
> 
> **💡 Tip:** Store this key in a secure password manager or vault.

## 🌐 Access Your Platform

### 🔗 Platform URLs

- **Fast.BI Console:** [https://mycompany.mycompany_domain.com](https://mycompany.mycompany_domain.com)

### 🔐 Default Credentials

- **Keycloak Admin:** Generated during deployment (check CLI output)
- **Database:** Auto-configured with secure passwords
- **Service Accounts:** Automatically managed

## 🗑️ Cleanup & Cost Management

> **⚠️ Free Tier Cost Management:**
> - **$300 Free Credits:** Typically lasts 14 days for testing
> - **Monitor Usage:** Check GCP Console billing dashboard
> - **Destroy Promptly:** Remove environment when done testing to avoid charges
> - **Set Budget Alerts:** Configure billing alerts in GCP Console

### Destroy Environment

```bash
python cli.py --destroy --destroy-confirm
```

This will completely remove all resources and stop billing.

## 🔍 Troubleshooting

### Common Issues & Solutions

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

### Clean Up Local Files

If you need to clean up local deployment files (Terraform state, temporary files, etc.):

```bash
python cli.py --cleanup
```

> This will remove local deployment files but won't affect your deployed infrastructure. Use this to free up disk space or clean up after a failed deployment.

## 🎉 Next Steps

After successful deployment:

1. **Configure Users:** Set up SSO authentication in Keycloak
2. **Connect Data Sources:** Configure data replication in Airbyte
3. **Create Data Models:** Build dbt models in your data repository
4. **Set Up Dashboards:** Create visualizations in your BI platform
5. **Monitor Performance:** Use built-in monitoring and alerting

## 📚 Additional Resources

- **GitHub Repository:** [fast-bi/data-development-platform](https://github.com/fast-bi/data-development-platform)
- **Documentation:** [wiki.fast.bi](https://wiki.fast.bi)
- **Community Support:** GitHub Issues and Discussions

---

**Need Help?** Check the troubleshooting section above or open an issue on GitHub.
