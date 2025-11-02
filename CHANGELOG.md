# 📋 Changelog

All notable changes to Fast.BI will be documented in this file.

## [0.1.0] - 2025-09-23

### Added
- 🎉 **First Public Release**: Fast.BI Data Development Platform
- 🧰 **Production-Ready CLI**: Interactive and non-interactive deployment tools
- ☁️ **Multi-Cloud Support**: GCP, AWS, and On-Premise deployment options
- 🐳 **Containerized Architecture**: Docker-based deployment and development
- 🔐 **Enterprise Security**: Vault integration, SSL/TLS, authentication
- 📊 **Full Monitoring Stack**: Prometheus, Grafana, and comprehensive logging
- 🔄 **CI/CD Integration**: Argo Workflows and GitLab/GitHub runners
- 📚 **Complete Documentation**: Deployment guides, user manuals, and API references

### Infrastructure
- **Kubernetes Orchestration**: Automated cluster creation and management
- **Load Balancing**: Traefik ingress controller with SSL/TLS termination
- **Database Services**: StackGres PostgreSQL cluster with high availability
- **Object Storage**: MinIO integration for data lake capabilities
- **Networking**: Custom VPC with security groups and firewall rules
- **DNS Management**: External DNS with automatic record management

## [0.1.2] - 2025-11-02

### Added
- 🧪 **Dry-Run Mode**: Comprehensive dry-run functionality across all deployment phases
  - Generate all configuration files (Terraform, Helm values, Kubernetes manifests) without executing deployment commands
  - Preview commands that would be executed with `[DRY-RUN]` prefix
  - Zero infrastructure changes - no cloud resources created, no deployments executed
  - Automatic fake resources (kubeconfig, service accounts) for seamless dry-run execution
  - Complete documentation in `docs/dry-run.md` with examples, best practices, and troubleshooting
- 📋 **Command Preview**: All deployment commands shown with `[DRY-RUN]` prefix when in dry-run mode
- 🔍 **Configuration Validation**: Ability to review all generated files before actual deployment
- 📚 **Enhanced Documentation**: Added comprehensive dry-run guide with CI/CD integration examples

### Changed
- **Phase 2 Default**: Changed default data analysis platform from `lightdash` to `superset` in platform selection
- **Phase 3 Logic**: Fixed repository configuration flow - "Would you like to modify settings?" now only appears when user says "No" to proceeding, not after confirming "Yes"

### Infrastructure Services
- ✅ **All 10 Infrastructure Service Deployers** now support dry-run mode:
  - Secret Operator (`1.0_secret_operator.py`)
  - Cert Manager (`2.0_cert_manager.py`)
  - External DNS (`3.0_external_dns.py`)
  - Traefik Load Balancer (`4.0_traefik_lb.py`)
  - StackGres PostgreSQL (`5.0_stackgres_postgresql.py`)
  - Log Collector (`6.0_log_collector.py`)
  - Services Monitoring (`7.0_services_monitoring.py`) - includes `execute_kubectl` method support
  - Cluster Cleaner (`8.0_cluster_cleaner.py`)
  - IDP SSO Manager (`9.0_idp_sso_manager.py`)
  - Cluster PVC Autoscaler (`10.0_cluster_pvc_autoscaller.py`)

### Data Services
- ✅ **All 11 Data Service Deployers** now support dry-run mode:
  - CI/CD Workload Runner (`1.0_cicd_workload_runner.py`)
  - Data Lineage (`2.0_data_lineage.py`)
  - Data Catalog (`3.0_data_catalog.py`)
  - Data Quality (`4.0_data_quality.py`)
  - Data Ingestion (`5.0_data_ingestion.py`)
  - Data Orchestrator (`6.0_data_orchestrator.py`)
  - Data Transformation (`7.0_data_transformation.py`)
  - Data Analysis (`8.0_data_analysis.py`)
  - Data Governance (`9.0_data_governance.py`)
  - User Console (`10.0_user_console.py`)
  - Data Image Puller (`11.0_data_image_puller.py`)

### Utility Classes
- ✅ **GoogleCloudManager** (`deployers/clouds/google_cloud.py`): Skips terraform/terragrunt execution in dry-run mode
- ✅ **CustomerSecretManager** (`utils/customer_secret_manager_operations.py`): Skips vault operations, generates secrets locally
- ✅ **CustomerDataPlatformRepositoryOperator** (`utils/customer_data_platform_repository_operator.py`): 
  - Skips git clone, commit, and push operations
  - Renders all repository templates locally in separate `_prepare_repository_structure_dry_run()` method
- ✅ **InfrastructureDeploymentOperator** (`utils/infrastructure_deployment_operator.py`):
  - Skips git clone and push operations
  - Skips vault encryption key saving
  - Keeps generated files for review (no cleanup)

### CLI Enhancements
- **New Flag**: `--dry-run` option added to CLI for enabling dry-run mode
- **Dry-Run Banner**: Informative banner at start of dry-run execution explaining what will/won't happen
- **Completion Summary**: Summary at end showing all generated file locations
- **Fake Resources**: Automatically uses mock kubeconfig and GCP service accounts without user prompts in Phase 2 and Phase 4
- **Secret Handling**: In dry-run mode, skips fetching `ARGO_WORKFLOW_SA_TOKEN` from Kubernetes with informative message

### Documentation
- ✅ **New Document**: `docs/dry-run.md` - Comprehensive 400+ line guide covering:
  - Overview and quick start
  - Phase-by-phase behavior details
  - Generated files reference table
  - Review checklist
  - Interactive and non-interactive modes
  - Converting dry-run to actual deployment
  - Troubleshooting guide
  - Best practices and CI/CD integration
  - Complete example workflows
- ✅ **Updated**: `docs/gcp-deployment.md` - Added dry-run mode section as recommended first step

### Technical Details
- **Dry-Run Pattern**: Consistent implementation pattern across all deployers:
  ```python
  if self.dry_run:
      logger.info(f"[DRY-RUN] Would execute: {cmd}")
      print(f"[DRY-RUN] Would execute: {cmd}")
      return ""  # Mock success
  ```
- **File Generation**: All template rendering and file writing still executes (Jinja2 processing, config file generation)
- **State Management**: Dry-run saves state file for resuming or converting to actual deployment
- **Separation of Concerns**: Clean separation between dry-run and normal execution flows

### Benefits
- 🧪 **Safe Testing**: Test configurations without creating infrastructure
- 📋 **Documentation**: Generate deployment configurations for documentation
- 🔍 **Validation**: Validate inputs before committing to deployment
- 🎓 **Learning**: Understand deployment process by seeing all commands
- ⚡ **Speed**: Complete in ~2-3 minutes vs 15-30 minutes for actual deployment

## [0.1.1] - 2025-10-01

### Fixed
- Data Governance prerequisites: switched Zookeeper image from `bitnami/zookeeper` to
  `bitnamilegacy/zookeeper` in `charts/data_services_charts/data_governance/template_dh_prerequisites_values.yaml`
  due to Bitnami/Broadcom repository changes (original repo no longer available).

## [0.1.0] - 2025-09-23

### Data Services
- **Data Ingestion**: Airbyte integration for multi-source data replication
- **Data Transformation**: dbt Core for data modeling and transformation
- **Workflow Orchestration**: Apache Airflow for complex data pipelines
- **Data Governance**: DataHub and Re_Data integration for data quality
- **Business Intelligence**: Lightdash, Superset, and Metabase support

### Security & Compliance
- **Single Sign-On**: Keycloak SSO integration with multiple providers
- **Secrets Management**: HashiCorp Vault for secure credential storage
- **Access Control**: Role-based access control (RBAC) with fine-grained permissions
- **Encryption**: End-to-end TLS/SSL encryption for all communications
- **Audit & Compliance**: Comprehensive activity logging and audit trails

### Notes
- This is the first stable public release after extensive development and testing
- Production-ready with enterprise-grade security and monitoring capabilities
- Comprehensive multi-cloud support with automated deployment options

## [0.0.9] - 2025-09-XX

### Added
- 🧪 **Beta Release**: Fast.BI Data Development Platform Beta
- 🔧 **Advanced CLI Features**: Enhanced deployment automation
- ☁️ **Extended Cloud Support**: Additional cloud provider integrations
- 🏢 **Enterprise Features**: Advanced security and compliance tools
- 📊 **Enhanced Monitoring**: Improved observability and alerting
- 🔄 **CI/CD Enhancements**: Advanced workflow automation
- 📚 **Beta Documentation**: Comprehensive guides and tutorials

### Changed
- Improved deployment reliability and error handling
- Enhanced user experience with better CLI feedback
- Optimized resource utilization and performance

### Known Issues
- Some advanced features still in development
- Limited third-party integrations

## [0.0.1] - 2024-XX-XX

### Added
- 🧪 **Alpha Release**: Initial Fast.BI framework
- 🔧 **Core CLI Framework**: Basic deployment functionality
- ☁️ **GCP Support**: Initial Google Cloud Platform integration
- 🐳 **Docker Foundation**: Containerized deployment architecture
- 📚 **Documentation Foundation**: Initial guides and references

### Changed
- Development and testing phase
- Core architecture refinement

### Known Issues
- Limited cloud provider support
- Basic deployment options only
- Alpha-level stability

## [Pre-Release] - 2023-2024

### Development Phase
- 🏗️ **Core Framework Development**: Initial architecture and design
- 💡 **Concept Validation**: Proof of concept and feasibility studies
- 🔬 **Technology Research**: Evaluation of data platform technologies
- 📋 **Requirements Gathering**: Analysis of enterprise data platform needs
- 🎯 **MVP Definition**: Minimum viable product specification

### Key Milestones
- **2023**: Core idea development and initial framework design
- **2024**: First beta version (0.1.0) development and testing
- **2025-09-23**: First stable public release (0.1.0)

---

## 📝 Release Notes Format

### Version Numbering
- **Major.Minor.Patch** (e.g., 1.0.0)
- **Major**: Breaking changes or major new features
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes and minor improvements

### Change Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Features that will be removed
- **Removed**: Features that have been removed
- **Fixed**: Bug fixes
- **Security**: Security improvements

### Breaking Changes
Breaking changes are marked with ⚠️ and include:
- Migration instructions
- Configuration changes required
- API changes
- Deprecation notices

---

## 🔗 Related Links

- [Release Notes](https://github.com/fast-bi/data-development-platform/releases)
- [Migration Guide](docs/migration/)
- [Upgrade Instructions](docs/upgrading.md)
- [API Changes](docs/api/changes.md)

---

**Note**: This changelog is maintained by the Fast.BI team. For detailed technical information, please refer to the [documentation](docs/) and [release notes](https://github.com/fast-bi/data-development-platform/releases).
