import subprocess
import os
from datetime import datetime
import json
import requests
import logging
import sys
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

# Configure logging for import usage (no file handler by default)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('user_console_deployer')

class PlatformUserConsole:
    def __init__(self, chart_version, customer, metadata_collector, cloud_provider, domain_name="fast.bi",
                 method="local_vault", external_infisical_host=None, slug=None, vault_project_id=None,
                 secret_manager_client_id=None, secret_manager_client_secret=None,
                 tsb_fastbi_web_core_image_version=None, tsb_dbt_init_core_image_version=None,
                 project_id=None, bq_project_id=None, cluster_name=None, kube_config_path=None,
                 namespace="user-console", bi_system=None, data_replication_default_destination_type=None, fast_bi_statistics_id=None):
        # Initialize basic attributes
        self.deployment_environment = "data-services"
        self.external_infisical_host = external_infisical_host
        self.cloud_provider = cloud_provider
        self.domain_name = domain_name
        self.namespace = namespace
        self.slug = slug
        self.project_slug = slug
        self.vault_project_id = vault_project_id
        self.secret_manager_client_id = secret_manager_client_id
        self.secret_manager_client_secret = secret_manager_client_secret
        self.customer = customer
        self.metadata_collector = metadata_collector
        self.chart_version = chart_version
        self.bi_system = bi_system
        self.data_replication_default_destination_type = data_replication_default_destination_type
        # For local development only
        self.local_postgresql = "false"
        
        # Fast.bi Statistics
        self.fast_bi_statistics_id = fast_bi_statistics_id

        # Cloud Provider Specific
        try:
            if self.cloud_provider == "gcp":
                self.project_id = project_id if project_id else f"fast-bi-{customer}"
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for GCP with project ID: {self.project_id}")
            elif self.cloud_provider == "aws":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for AWS with cluster: {self.cluster_name}")
            elif self.cloud_provider == "azure":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for Azure with cluster: {self.cluster_name}")
            elif self.cloud_provider == "self-managed":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for self-managed with cluster: {self.cluster_name}")
            else:
                raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")
        except Exception as e:
            logger.error(f"Error during cloud provider configuration: {str(e)}")
            raise

        # Initialize data platform warehouse variables
        self.gcp_project_id = None
        self.bq_project_id = None
        self.gcp_sa_impersonate_email = None
        self.snowflake_project_id = None
        self.snowflake_account = None
        self.snowflake_username = None
        self.snowflake_password = None
        self.snowflake_database = None
        self.snowflake_schema = None
        
        # Set kubeconfig path
        self.kube_config = kube_config_path if kube_config_path else f'/tmp/{self.cluster_name}-kubeconfig.yaml'
        logger.info(f"Using kubeconfig: {self.kube_config}")

        # Check if kubeconfig exists
        if not os.path.exists(self.kube_config):
            logger.warning(f"Kubeconfig file not found at {self.kube_config}. Deployment may fail.")

        # Validate method and required parameters
        if method not in ["local_vault", "external_infisical"]:
            raise ValueError(f"Unsupported method: {method}")
        self.method = method

        # Validate method-specific requirements
        if method == "external_infisical":
            if not all([slug, vault_project_id, secret_manager_client_id, secret_manager_client_secret]):
                raise ValueError("slug, vault_project_id, secret_manager_client_id, and secret_manager_client_secret are required for external_infisical method")
        elif method == "local_vault":
            self.secret_file = f"/tmp/{customer}_customer_vault_structure.json"
            if not os.path.exists(self.secret_file):
                raise FileNotFoundError(f"Secret file not found: {self.secret_file}")

        # Service specific configurations
        self.customer_root_domain = f"{self.customer}.{self.domain_name}"
        self.ingress_host = self.customer_root_domain
        self.data_services_admin_email = f"root-fastbi-admin@{self.customer_root_domain}"
        
        # Service-specific settings
        # Data Platform User Console
        self.data_platform_user_console_chart_repo_name = "kube-core"
        self.data_platform_user_console_chart_name = "kube-core/raw"
        self.data_platform_user_console_chart_repo = "https://kube-core.github.io/helm-charts"
        self.data_platform_user_console_chart_version = self.chart_version
        self.data_platform_user_console_deployment_name = "data-platform-user-console"
        self.data_platform_user_console_values_path = "charts/data_services_charts/user_console/values.yaml"
        self.data_platform_user_console_render_template_values_path = "charts/data_services_charts/user_console/template_values.yaml"
        self.data_platform_user_console_app_name = "data-platform-user-console"
        
        # Image versions
        self.tsb_fastbi_web_core_image = "4fastbi/data-platform-ui-core"
        self.tsb_fastbi_web_core_image_version = tsb_fastbi_web_core_image_version
        self.embeded_grafana_image_version = "grafana/grafana:11.6.2"
        self.tsb_dbt_init_core_image = "4fastbi/data-platform-init-core"
        self.tsb_dbt_init_core_image_version = tsb_dbt_init_core_image_version
        self.data_platform_user_console_app_version = f"FastBI-{self.tsb_fastbi_web_core_image_version}-FastBI-API-{self.tsb_dbt_init_core_image_version}"
        
        # Endpoints and connections
        self.fastbi_dbt_project_variables_file = "dbt_airflow_variables.yml"
        self.data_replication_internal_k8s_web_svc = "data-replication-airbyte-webapp-svc.data-replication.svc.cluster.local"
        self.data_dcdq_metacollector_endpoint_url = "http://data-dcdq-metacollect.data-dcdq-metacollect.svc.cluster.local"
        self.main_endpoint = f"https://{self.ingress_host}"
        self.data_services_reply_email = f"no-reply@{self.ingress_host}"
        self.data_replication_endpoint = f"https://airbyte.{self.ingress_host}/oauth2/start"
        self.data_orchestration_endpoint = f"https://airflow.{self.ingress_host}/login/FastBI-SSO?next=/"
        self.data_orchestration_internal_k8s_web_svc = "http://data-orchestration-webserver.data-orchestration.svc.cluster.local"
        self.data_workflows_endpoint = f"https://workflows.{self.ingress_host}/oauth2/redirect?redirect=https://workflows.{self.ingress_host}/workflows"
        self.data_catalog_endpoint = f"https://data-catalog.{self.ingress_host}/"
        self.data_quality_endpoint = f"https://data-quality.{self.ingress_host}/"
        self.data_governance_endpoint = f"https://datahub.{self.ingress_host}/"
        self.data_manipulation_endpoint = f"https://ide.{self.ingress_host}/"
        self.data_platform_monitoring_endpoint = f"https://monitoring.{self.ingress_host}"
        self.data_platform_object_storage_endpoint = f"https://minio.{self.ingress_host}"
        self.data_platform_object_storage_svc_endpoint = "http://minio.minio.svc.cluster.local"
        self.data_platform_object_storage_api_endpoint = f"s3.{self.ingress_host}"
        self.dbt_project_archive_bucket = "dbt-project-archive"
        self.sso_idp_platform_endpoint = f"https://login.{self.ingress_host}/"
        self.sso_idp_platform_admin_endpoint = f"https://login.{self.ingress_host}/admin/{self.customer}/console/"
        self.sso_idp_platform_users_endpoint = f"https://login.{self.ingress_host}/realms/{self.customer}/account"
        self.sso_idp_platform_realm_endoint = f"{self.sso_idp_platform_endpoint}realms/{self.customer}"
        self.wiki_fastbi_endpoint = "https://wiki.fast.bi/"
        
        if self.bi_system == "superset":
            self.bi_endpoint = f"https://bi.{self.customer_root_domain}/login/FastBI-SSO?next="
        else:
            self.bi_endpoint = f"https://bi.{self.customer_root_domain}"
        
        # PostgreSQL configuration
        self.data_platform_user_console_psql_chart_version = "16.6.7"
        self.data_platform_user_console_psql_deployment_name = "data-platform-user-console-db"
        self.data_platform_user_console_psql_chart_repo_name = "bitnami"
        self.data_platform_user_console_psql_chart_name = "oci://registry-1.docker.io/bitnamicharts/postgresql"
        self.data_platform_user_console_psql_chart_repo = "https://charts.bitnami.com/bitnami"
        self.data_platform_user_console_psql_values_path = "charts/data_services_charts/user_console/postgresql_values.yaml"
        self.data_platform_user_console_psql_render_template_values_path = "charts/data_services_charts/user_console/template_postgresql_values.yaml"

        # Set app_name after BI system initialization
        self.app_name = self.data_platform_user_console_chart_name.split('/')[1] if '/' in self.data_platform_user_console_chart_name else self.data_platform_user_console_chart_name
        
        # Validate template paths
        self._validate_template_paths()

    def _validate_template_paths(self):
        """Validate that all required template files exist"""
        required_paths = [
            self.data_platform_user_console_psql_render_template_values_path,
            self.data_platform_user_console_render_template_values_path
        ]
        for path in required_paths:
            template_path = Path(path)
            if not template_path.exists():
                logger.error(f"Template file not found: {template_path}")
                raise FileNotFoundError(f"Template file not found: {template_path}")
            logger.debug(f"Template file validated: {template_path}")

    def deploy_service(self, chart_repo_name, chart_repo, deployment_name, chart_name, chart_version, namespace, values_path):
        """Deploy a Helm chart service"""
        logger.info(f"Deploying {deployment_name} in namespace {namespace}")
        
        # Check if values file exists
        if not os.path.exists(values_path):
            logger.error(f"Values file not found: {values_path}")
            raise FileNotFoundError(f"Values file not found: {values_path}")
        
        try:
            # Properly add and update the Helm repo
            self.execute_command(["helm", "repo", "add", chart_repo_name, chart_repo])
            self.execute_command(["helm", "repo", "update", chart_repo_name])
            
            # Formulate the Helm upgrade command properly as a list
            helm_command = [
                "helm", "upgrade", "-i", deployment_name, chart_name,
                "--version", chart_version,
                "--namespace", namespace,
                "--create-namespace",
                "--wait",
                "--values", values_path,
                "--kubeconfig", self.kube_config
            ]
            self.execute_command(helm_command)
            logger.info(f"Successfully deployed {deployment_name} in namespace {namespace}")
        except Exception as e:
            logger.error(f"Failed to deploy {deployment_name}: {str(e)}")
            raise

    def deploy_extra_resources(self):
        """Deploy additional Kubernetes resources from extra values file"""
        logger.info(f"Deploying extra resources from {self.bi_extra_values_path} in namespace {self.namespace}")
        
        # Check if extra values file exists
        if not os.path.exists(self.bi_extra_values_path):
            logger.error(f"Extra values file not found: {self.bi_extra_values_path}")
            raise FileNotFoundError(f"Extra values file not found: {self.bi_extra_values_path}")
        
        try:
            kubectl_command = [
                "kubectl", "apply", "-f", self.bi_extra_values_path, 
                "--namespace", self.namespace,
                "--kubeconfig", self.kube_config
            ]
            self.execute_command(kubectl_command)
            logger.info(f"Successfully deployed extra resources in namespace {self.namespace}")
        except Exception as e:
            logger.error(f"Failed to deploy extra resources: {str(e)}")
            raise

    def get_deployed_app_version(self, deployment_name, namespace):
        """Get the deployed application version from Helm"""
        logger.info(f"Getting deployed version for {deployment_name} in namespace {namespace}")
        try:
            command = ["helm", "ls", "--deployed", "-f", deployment_name, "-n", namespace, "--kubeconfig", self.kube_config, "--output", "json"]
            result = self.execute_command(command)
            if result:
                # Parse JSON output
                deployments = json.loads(result)
                if deployments and isinstance(deployments, list) and len(deployments) > 0:
                    app_version = deployments[0].get('app_version', "Unknown")
                    logger.info(f"Found app version: {app_version}")
                    return app_version
                else:
                    logger.warning(f"No deployments found for {deployment_name}")
            return "No deployed version found"
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Helm output as JSON: {str(e)}")
            return "Error parsing version"
        except Exception as e:
            logger.error(f"Error getting deployed version: {str(e)}")
            return "Error getting version"

    def execute_command(self, command):
        """Execute a shell command with proper error handling"""
        cmd_str = ' '.join(command)
        logger.debug(f"Executing command: {cmd_str}")
        
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logger.debug(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd_str}")
            logger.error(f"Status code: {e.returncode}")
            logger.error(f"Output: {e.stdout}")
            logger.error(f"Error: {e.stderr}")
            raise Exception(f"Execution failed for command {cmd_str}: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error executing command {cmd_str}: {str(e)}")
            raise

    def render_user_console_psql_values_file(self, user_console_psql_username, user_console_psql_database, user_console_psql_repl_username):
        """Render the PostgreSQL values file from template"""
        logger.info("Rendering PostgreSQL values file from template")
        try:
            context = {
                'chart_name': self.data_platform_user_console_psql_chart_name,
                'chart_repo': self.data_platform_user_console_psql_chart_repo,
                'chart_version': self.data_platform_user_console_psql_chart_version,
                'username': user_console_psql_username,
                'database': user_console_psql_database,
                'replication_username': user_console_psql_repl_username,
                'namespace': self.namespace,
                'project_slug': self.slug,
                'method': self.method
            }
            
            # Ensure output directory exists
            output_dir = os.path.dirname(self.data_platform_user_console_psql_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(self.data_platform_user_console_psql_render_template_values_path, self.data_platform_user_console_psql_values_path, context)
            logger.info(f"Successfully rendered PostgreSQL values file to {self.data_platform_user_console_psql_values_path}")
        except Exception as e:
            logger.error(f"Failed to render PostgreSQL values file: {str(e)}")
            raise

    def render_values_files(self, data_model_repo_url, data_orchestration_repo_url, user_console_psql_host, user_console_psql_port, data_replication_db_host, data_replication_db_port, data_replication_db_database, data_replication_db_password, data_replication_db_username, data_orchestration_db_host, data_orchestration_db_port, data_orchestration_db_database, data_orchestration_db_password, data_orchestration_db_username, user_console_sso_idp_platform_client_id, user_console_sso_idp_platform_client_secret, data_replication_default_destination_type, bi_system):
        """Render all template files for Data Platform User Console deployment"""
        logger.info("Rendering Data Platform User Console template files")
        try:
            context = {
                'customer': self.customer,
                'domain': self.domain_name,
                'chart_name': self.data_platform_user_console_chart_name,
                'chart_repo': self.data_platform_user_console_chart_repo,
                'chart_version': self.data_platform_user_console_chart_version,
                'namespace': self.namespace,
                'cloud_provider': self.cloud_provider,
                'data_platform_user_console_app_name': self.data_platform_user_console_app_name,
                'data_platform_user_console_app_version': self.data_platform_user_console_app_version,
                'method': self.method,
                'local_postgresql': self.local_postgresql,
                'project_slug': self.project_slug,
                'data_platform_warehouse': data_replication_default_destination_type,
                'bi_system': bi_system,
                'bq_project_id': self.bq_project_id,
                'gcp_project_id': self.gcp_project_id,
                'gcp_sa_impersonate_email': self.gcp_sa_impersonate_email,
                'airbyte_local_k8s_svc_url': self.data_replication_internal_k8s_web_svc,
                'airbyte_api_link': f"http://{self.data_replication_internal_k8s_web_svc}",
                'data_replication_endpoint': self.data_replication_endpoint,
                'data_orchestration_endpoint': self.data_orchestration_endpoint,
                'data_model_repo_url': data_model_repo_url,
                'data_catalog_endpoint': self.data_catalog_endpoint,
                'data_quality_endpoint': self.data_quality_endpoint,
                'data_governance_endpoint': self.data_governance_endpoint,
                'ide_endpoint': self.data_manipulation_endpoint,
                'bi_endpoint': self.bi_endpoint,
                'main_endpoint': self.main_endpoint,
                'monitoring_endpoint': self.data_platform_monitoring_endpoint,
                's3_link': self.data_platform_object_storage_endpoint,
                'sso_console_link': self.sso_idp_platform_endpoint,
                'wiki_fastbi_endpoint': self.wiki_fastbi_endpoint,
                'sso_idp_platform_admin_endpoint': self.sso_idp_platform_admin_endpoint,
                'sso_idp_platform_users_endpoint': self.sso_idp_platform_users_endpoint,
                'dbt_project_archive_bucket': self.dbt_project_archive_bucket,
                'bucket_s3_link': self.data_platform_object_storage_api_endpoint,
                'data_orchestration_internal_k8s_web_svc': self.data_orchestration_internal_k8s_web_svc,
                'data_orchestration_repo_url': data_orchestration_repo_url,
                'data_dcdq_metacollect_internal_k8s_web_svc': self.data_dcdq_metacollector_endpoint_url,
                'data_workflows_endpoint': self.data_workflows_endpoint,
                'sso_idp_platform_realm_endoint': self.sso_idp_platform_realm_endoint,
                'user_console_sso_idp_platform_client_id': user_console_sso_idp_platform_client_id,
                'user_console_sso_idp_platform_client_secret': user_console_sso_idp_platform_client_secret,
                'ingress_host': self.ingress_host,
                'embeded_grafana_image_version': self.embeded_grafana_image_version,
                'tsb_dbt_init_core_image': self.tsb_dbt_init_core_image,    
                'tsb_dbt_init_core_image_version': self.tsb_dbt_init_core_image_version,
                'tsb_fastbi_web_core_image': self.tsb_fastbi_web_core_image,
                'tsb_fastbi_web_core_image_version': self.tsb_fastbi_web_core_image_version,
                'mail_default_sender': self.data_services_reply_email,
                'user_console_db_host': user_console_psql_host,
                'user_console_db_port': user_console_psql_port,
                'data_replication_db_database': data_replication_db_database,
                'data_replication_db_password': data_replication_db_password,
                'data_replication_db_username': data_replication_db_username,
                'data_replication_db_host': data_replication_db_host,
                'data_replication_db_port': data_replication_db_port,
                'data_orchestration_db_database': data_orchestration_db_database,
                'data_orchestration_db_password': data_orchestration_db_password,
                'data_orchestration_db_username': data_orchestration_db_username,
                'data_orchestration_db_host': data_orchestration_db_host,
                'data_orchestration_db_port': data_orchestration_db_port,
                'fast_bi_statistics_id': self.fast_bi_statistics_id
            }

            # Ensure output directory exists
            output_dir = os.path.dirname(self.data_platform_user_console_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(self.data_platform_user_console_render_template_values_path, self.data_platform_user_console_values_path, context)
            logger.info(f"Successfully rendered Data Platform User Console values file to {self.data_platform_user_console_values_path}")
        except Exception as e:
            logger.error(f"Failed to render Data Platform User Console values file: {str(e)}")
            raise

    def render_template(self, template_path, output_path, context):
        """Render a Jinja2 template to a file"""
        try:
            logger.debug(f"Rendering template {template_path} to {output_path}")
            env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
            template = env.get_template(os.path.basename(template_path))
            output = template.render(context)
            
            with open(output_path, 'w') as f:
                f.write(output)
                logger.debug("Template rendered successfully")
        except TemplateNotFound:
            logger.error(f"Template not found: {template_path}")
            raise FileNotFoundError(f"Template not found: {template_path}")
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {str(e)}")
            raise

    def authenticate_with_vault(self):
        """Authenticate with vault and return access token"""
        try:
            if self.method == "external_infisical":
                logger.info("Authenticating with external Infisical vault")
                url = f"{self.external_infisical_host}/api/v1/auth/login"
                payload = {
                    "clientId": self.secret_manager_client_id,
                    "clientSecret": self.secret_manager_client_secret
                }
                response = requests.post(url, json=payload)
                response.raise_for_status()
                return response.json()["accessToken"]
            elif self.method == "local_vault":
                logger.info("Using local vault file")
                with open(self.secret_file, 'r') as f:
                    return json.load(f)
            else:
                raise ValueError(f"Unsupported method: {self.method}")
        except Exception as e:
            logger.error(f"Error during vault authentication: {str(e)}")
            raise

    def get_secret_from_vault(self, secret_name, secret_path, access_token=None, environment="prod", version=None, secret_type="shared", include_imports="false"):
        """Retrieve the secret from the vault using the appropriate method"""
        if self.method == "external_infisical":
            return self._get_secret_from_external_vault(
                secret_name, secret_path, access_token, environment, version, secret_type, include_imports
            )
        else:
            return self._get_secret_from_local_vault(secret_name, secret_path)

    def _get_secret_from_external_vault(self, secret_name, secret_path, access_token, environment, version, secret_type, include_imports):
        """Retrieve the secret from the external Infisical vault"""
        try:
            url = f"{self.external_infisical_host}/api/v3/secrets/raw/{secret_name}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "workspaceId": self.vault_project_id,
                "environment": environment,
                "secretPath": secret_path,
                "version": version,
                "type": secret_type,
                "include_imports": include_imports
            }
            params = {k: v for k, v in params.items() if v is not None}
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()['secret']['secretValue']
        except Exception as e:
            logger.error(f"Failed to get secret from external vault: {str(e)}")
            raise

    def _get_secret_from_local_vault(self, secret_name, secret_path):
        """Retrieve the secret from the local vault JSON file"""
        try:
            with open(self.secret_file, 'r') as f:
                vault_data = json.load(f)
            
            current = vault_data
            for part in secret_path.strip('/').split('/'):
                if part not in current:
                    raise KeyError(f"Path {secret_path} not found in vault structure")
                current = current[part]
            
            if secret_name not in current:
                raise KeyError(f"Secret {secret_name} not found at path {secret_path}")
            
            return current[secret_name]
        except Exception as e:
            logger.error(f"Failed to get secret from local vault: {str(e)}")
            raise
    
    def run(self):
        """Main execution method"""
        logger.info(f"Starting User Console deployment for customer: {self.customer}")
        try:
            # Debug
            if logger.level == logging.DEBUG:
                self.print_all_variables()
                
            # Get access token if using external vault
            access_token = self.authenticate_with_vault() if self.method == "external_infisical" else None
            
            # Get secrets from vault
            logger.info("Retrieving secrets from vault")

            data_model_repo_url = self.get_secret_from_vault(
                secret_name="data_repo_url", 
                secret_path="/data-platform-runner/git_provider_repo_urls",
                access_token=access_token
            )

            data_orchestration_repo_url = self.get_secret_from_vault(
                secret_name="dag_repo_url", 
                secret_path="/data-platform-runner/git_provider_repo_urls",
                access_token=access_token
            )
            data_replication_db_database = self.get_secret_from_vault(
                secret_name="database", 
                secret_path="/data-replication/database-secrets",
                access_token=access_token
            )
            data_replication_db_password = self.get_secret_from_vault(
                secret_name="password", 
                secret_path="/data-replication/database-secrets",
                access_token=access_token
            )
            data_replication_db_username = self.get_secret_from_vault(
                secret_name="username", 
                secret_path="/data-replication/database-secrets",
                access_token=access_token
            )
            data_orchestration_db_database = self.get_secret_from_vault(
                secret_name="database", 
                secret_path="/data-orchestration/database-secrets",
                access_token=access_token
            )
            data_orchestration_db_password = self.get_secret_from_vault(    
                secret_name="password", 
                secret_path="/data-orchestration/database-secrets",
                access_token=access_token
            )
            data_orchestration_db_username = self.get_secret_from_vault(
                secret_name="username", 
                secret_path="/data-orchestration/database-secrets",
                access_token=access_token
            )

            data_platform_user_console_db_username = self.get_secret_from_vault(
                secret_name="username", 
                secret_path="/user-console/database-secrets",
                access_token=access_token
            )

            data_platform_user_console_db_database = self.get_secret_from_vault(
                secret_name="database", 
                secret_path="/user-console/database-secrets",
                access_token=access_token
            )

            data_platform_user_console_db_repl_username = self.get_secret_from_vault(
                secret_name="replicationUsername", 
                secret_path="/user-console/database-secrets",
                access_token=access_token
            )

            user_console_sso_idp_platform_client_id = self.get_secret_from_vault(
                secret_name="client_id", 
                secret_path="/user-console/sso-clients-secrets",
                access_token=access_token
            )

            user_console_sso_idp_platform_client_secret = self.get_secret_from_vault(
                secret_name="client_secret", 
                secret_path="/user-console/sso-clients-secrets",
                access_token=access_token
            )

            if self.bi_system:
                bi_system = self.bi_system
            else:
                bi_system = self.get_secret_from_vault(
                    secret_name="DATA_ANALYSIS_PLATFORM",
                    secret_path="/data-cicd-workflows/customer-cicd-variables",
                    access_token=access_token
                )
            
            if self.data_replication_default_destination_type:
                data_replication_default_destination_type = self.data_replication_default_destination_type
            else:
                data_replication_default_destination_type = self.get_secret_from_vault(
                    secret_name="DATA_WAREHOUSE_PLATFORM",
                    secret_path="/data-cicd-workflows/customer-cicd-variables",
                    access_token=access_token
                )

            # Initialize bq_project_id
            bq_project_id = None

            # Get bq_project_id from vault if needed
            if data_replication_default_destination_type == "bigquery":
                bq_project_id = self.get_secret_from_vault(
                    secret_name="BQ_PROJECT_ID",
                    secret_path="/user-console/root-secrets",
                    access_token=access_token
                )

            # Configure data platform warehouse based on the destination type
            try:
                if data_replication_default_destination_type == "bigquery":
                    self.gcp_project_id = bq_project_id if bq_project_id else self.project_id
                    self.bq_project_id = bq_project_id if bq_project_id else self.project_id
                    self.gcp_sa_impersonate_email = f"dbt-sa@{self.gcp_project_id}.iam.gserviceaccount.com"
                elif data_replication_default_destination_type == "snowflake":
                    self.snowflake_project_id = None
                    self.snowflake_account = None
                    self.snowflake_username = None
                    self.snowflake_password = None
                    self.snowflake_database = None
                    self.snowflake_schema = None
                elif data_replication_default_destination_type == "redshift":
                    self.redshift_host = None
                    self.redshift_port = None
                    self.redshift_user = None
                    self.redshift_password = None
                    self.redshift_database = None
                    self.redshift_schema = None
                else:
                    raise ValueError(f"Unsupported data platform warehouse: {data_replication_default_destination_type}")
            except Exception as e:
                logger.error(f"Error during data platform warehouse configuration: {str(e)}")
                raise

            if self.local_postgresql == "true":
                user_console_psql_port = "5432"
                data_replication_db_port = "5432"
                data_orchestration_db_port = "5432"
                user_console_psql_host = f"data-platform-user-console-psql.{self.namespace}.svc.cluster.local"
                data_replication_db_host = "data-replication-db-psql.data-replication.svc.cluster.local"
                data_orchestration_db_host = "data-orchestration-db-psql.data-orchestration.svc.cluster.local"
            else:
                user_console_psql_port = "5432"
                data_replication_db_port = "5432"
                data_orchestration_db_port = "5432"
                user_console_psql_host = "fastbi-global-psql.global-postgresql.svc.cluster.local"
                data_replication_db_host = "fastbi-global-psql.global-postgresql.svc.cluster.local"
                data_orchestration_db_host = "fastbi-global-psql.global-postgresql.svc.cluster.local"


            # Deploy PostgreSQL if local_postgresql is True
            if self.local_postgresql == "true":
                # Render PostgreSQL values file
                self.render_user_console_psql_values_file(
                    user_console_psql_username=data_platform_user_console_db_username,
                    user_console_psql_database=data_platform_user_console_db_database,
                    user_console_psql_repl_username=data_platform_user_console_db_repl_username
                )

                # Deploy PostgreSQL first
                logger.info("Deploying PostgreSQL for Data Analysis")
                self.deploy_service(
                    chart_repo_name=self.data_platform_user_console_psql_chart_repo_name,
                    chart_repo=self.data_platform_user_console_psql_chart_repo,
                    deployment_name=self.data_platform_user_console_psql_deployment_name,
                    chart_name=self.data_platform_user_console_psql_chart_name,
                    chart_version=self.data_platform_user_console_psql_chart_version,
                    namespace=self.namespace,
                    values_path=self.data_platform_user_console_psql_values_path
                )
                
                # Wait for PostgreSQL to be ready
                logger.info("Waiting for PostgreSQL to be ready...")
                self.execute_command([
                    "kubectl", "wait", "--for=condition=ready", "pod",
                    "-l", "app.kubernetes.io/instance=data-platform-user-console-psql",
                    "-n", self.namespace,
                    "--timeout=300s",
                    "--kubeconfig", self.kube_config
                ])
            else:
                logger.info("Using external PostgreSQL, skipping local deployment")
            
            # Render values files
            logger.info("Rendering Data Platform User Console values files")
            self.render_values_files(
                data_model_repo_url = data_model_repo_url,
                data_orchestration_repo_url=data_orchestration_repo_url,
                user_console_psql_host=user_console_psql_host,
                user_console_psql_port=user_console_psql_port,
                data_replication_db_host=data_replication_db_host,
                data_replication_db_port=data_replication_db_port,
                data_replication_db_database=data_replication_db_database,
                data_replication_db_password=data_replication_db_password,
                data_replication_db_username=data_replication_db_username,
                data_orchestration_db_host=data_orchestration_db_host,
                data_orchestration_db_port=data_orchestration_db_port,
                data_orchestration_db_database=data_orchestration_db_database,
                data_orchestration_db_password=data_orchestration_db_password,
                data_orchestration_db_username=data_orchestration_db_username,
                user_console_sso_idp_platform_client_id=user_console_sso_idp_platform_client_id,
                user_console_sso_idp_platform_client_secret=user_console_sso_idp_platform_client_secret,
                bi_system=bi_system,
                data_replication_default_destination_type=data_replication_default_destination_type
            )
            
            # Deploy User Console
            logger.info(f"Deploying {self.data_platform_user_console_chart_name} for User Console")
            self.deploy_service(
                chart_repo_name=self.data_platform_user_console_chart_repo_name,
                chart_repo=self.data_platform_user_console_chart_repo,
                deployment_name=self.data_platform_user_console_deployment_name,
                chart_name=self.data_platform_user_console_chart_name,
                chart_version=self.data_platform_user_console_chart_version,
                namespace=self.namespace,
                values_path=self.data_platform_user_console_values_path
            )
            
            # Wait for User Console to be ready
            logger.info("Waiting for User Console to be ready...")
            self.execute_command([
                "kubectl", "wait", "--for=condition=ready", "pod",
                "-l", "fastbi=data-platform-user-console",
                "-n", self.namespace,
                "--timeout=300s",
                "--kubeconfig", self.kube_config
            ])

            # Metadata Collection
            app_version_data_platform_user_console = self.get_deployed_app_version(deployment_name=self.data_platform_user_console_deployment_name, namespace=self.namespace)
            app_version_data_platform_user_console_core = self.tsb_fastbi_web_core_image_version
            app_version_data_platform_user_console_grafana = self.embeded_grafana_image_version
            app_version_data_platform_user_console_api = self.tsb_dbt_init_core_image_version

            app_version = {
                "data_platform_user_console_deployment": app_version_data_platform_user_console,
                "data_platform_user_console_core": app_version_data_platform_user_console_core,
                "data_platform_user_console_grafana": app_version_data_platform_user_console_grafana,
                "data_platform_user_console_api": app_version_data_platform_user_console_api
            }
            
            deployment_record = {
                "customer": self.customer,
                "customer_main_domain": self.customer_root_domain,
                "customer_vault_slug": self.slug,
                "deployment_environment": self.deployment_environment,
                "deployment_name": self.data_platform_user_console_deployment_name,
                "chart_name": self.data_platform_user_console_chart_name,
                "chart_version": self.data_platform_user_console_chart_version,
                "app_name": self.app_name,
                "app_version": app_version,
                "deploy_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            logger.info("Adding deployment record to metadata collector")
            self.metadata_collector.add_deployment_record(deployment_record)
            logger.info("Platform Data User Console deployment completed successfully")
            return "Platform Data User Console deployed successfully"
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise

    @classmethod
    def from_cli_args(cls, args):
        """Create a UserConsole instance from CLI arguments"""
        logger.info("Creating UserConsole instance from CLI arguments")
        return cls(
            chart_version=args.chart_version,
            customer=args.customer,
            metadata_collector=args.metadata_collector,
            cloud_provider=args.cloud_provider,
            domain_name=args.domain_name,
            method=args.method,
            external_infisical_host=args.external_infisical_host,
            slug=args.slug,
            vault_project_id=args.vault_project_id,
            secret_manager_client_id=args.client_id,
            secret_manager_client_secret=args.client_secret,
            tsb_fastbi_web_core_image_version=args.tsb_fastbi_web_core_image_version,
            tsb_dbt_init_core_image_version=args.tsb_dbt_init_core_image_version,
            project_id=args.project_id,
            bq_project_id=args.bq_project_id,
            cluster_name=args.cluster_name,
            kube_config_path=args.kube_config_path,
            namespace=args.namespace,
            bi_system=args.bi_system,
            fast_bi_statistics_id=args.fast_bi_statistics_id
        )


if __name__ == "__main__":
    # Configure file logging if running as main script
    log_file = "user_console_deployment.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Starting User Console deployment script, logging to {log_file}")
    
    parser = argparse.ArgumentParser(
        description="User Console Deployment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Method group
    method_group = parser.add_argument_group('vault method')
    method_group.add_argument(
        '--method',
        choices=['external_infisical', 'local_vault'],
        default='local_vault',
        help='Vault method to use. Choose between external Infisical service or local vault file'
    )
    method_group.add_argument(
        '--external_infisical_host',
        help='External Infisical host (required if method is external_infisical)'
    )
    method_group.add_argument(
        '--slug',
        help='Project slug for the vault (required for external_infisical method)'
    )
    method_group.add_argument(
        '--vault_project_id',
        help='Vault project ID (required for external_infisical method)'
    )
    method_group.add_argument(
        '--client_id',
        help='Secret manager client ID (required for external_infisical method)'
    )
    method_group.add_argument(
        '--client_secret',
        help='Secret manager client secret (required for external_infisical method)'
    )

    # Required core arguments
    required_args = parser.add_argument_group('required core arguments')
    required_args.add_argument(
        '--customer',
        required=True,
        help='Customer tenant name (lowercase letters, numbers, and hyphens only)'
    )
    required_args.add_argument(
        '--chart_version',
        required=True,
        help='Chart version for the deployment'
    )
    required_args.add_argument(
        '--cloud_provider',
        required=True,
        choices=['gcp', 'aws', 'azure', 'self-managed'],
        help='Cloud provider where the cluster is running'
    )
    required_args.add_argument(
        '--domain_name',
        default='fast.bi',
        help='Domain name for the customer (default: fast.bi)'
    )
    required_args.add_argument(
        '--tsb_fastbi_web_core_image_version',
        required=True,
        help='Image version for tsb-fastbi-web-core'
    )
    required_args.add_argument(
        '--tsb_dbt_init_core_image_version',
        required=True,
        help='Image version for tsb-dbt-init-core'
    )

    # Optional arguments
    optional_args = parser.add_argument_group('optional arguments')
    optional_args.add_argument(
        '--project_id',
        help='Cloud provider project ID (default: fast-bi-{customer})'
    )
    optional_args.add_argument(
        '--bq_project_id',
        help='BigQuery project ID (default: same as project_id)'
    )
    optional_args.add_argument(
        '--cluster_name',
        help='Kubernetes cluster name (default: fast-bi-{customer}-platform)'
    )
    optional_args.add_argument(
        '--kube_config_path',
        help='Path to kubeconfig file (default: /tmp/{cluster_name}-kubeconfig.yaml)'
    )
    optional_args.add_argument(
        '--namespace',
        default='user-console',
        help='Kubernetes namespace for deployment (default: user-console)'
    )
    optional_args.add_argument(
        '--metadata_file',
        default='deployment_metadata.json',
        help='Path to metadata file (default: deployment_metadata.json)'
    )
    optional_args.add_argument(
        '--skip_metadata',
        action='store_true',
        help='Skip metadata collection (for CLI usage)'
    )
    optional_args.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    optional_args.add_argument(
        '--bi_system',
        choices=['superset', 'lightdash', 'metabase', 'looker'],
        help='BI system for Data Development Platform'
    )
    optional_args.add_argument(
        '--data_replication_default_destination_type',
        choices=['bigquery', 'snowflake', 'redshift', 'fabric'],
        help='Default destination type for data replication'
    )
    optional_args.add_argument(
        '--fast_bi_statistics_id',
        help='Fast BI statistics ID'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        logger.info(f"Deploying User Console for customer: {args.customer}")
        logger.info(f"Using vault method: {args.method}")
        
        # Create a simple metadata collector for CLI usage
        class SimpleMetadataCollector:
            def __init__(self, metadata_file):
                self.metadata_file = metadata_file
                self.deployment_records = []
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r') as f:
                            self.deployment_records = json.load(f)
                            logger.info(f"Loaded {len(self.deployment_records)} existing deployment records")
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse {metadata_file}, starting with empty records")
                        self.deployment_records = []
                else:
                    logger.info(f"Metadata file {metadata_file} not found, will create new file")
            
            def add_deployment_record(self, record):
                self.deployment_records.append(record)
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(self.metadata_file)), exist_ok=True)
                    with open(self.metadata_file, 'w') as f:
                        json.dump(self.deployment_records, f, indent=2)
                    logger.info(f"Deployment record added to {self.metadata_file}")
                except Exception as e:
                    logger.error(f"Failed to write metadata to {self.metadata_file}: {str(e)}")

        # Use the appropriate metadata collector
        if args.skip_metadata:
            logger.info("Metadata collection is disabled")
            class DummyMetadataCollector:
                def add_deployment_record(self, record):
                    logger.info("Metadata collection skipped")
            metadata_collector = DummyMetadataCollector()
        else:
            logger.info(f"Using metadata file: {args.metadata_file}")
            metadata_collector = SimpleMetadataCollector(args.metadata_file)

        # Add metadata collector to args for from_cli_args method
        args.metadata_collector = metadata_collector

        # Create deployer instance using the CLI factory method
        logger.info("Creating UserConsole instance")
        deployer = PlatformUserConsole.from_cli_args(args)
        
        # Run the deployment
        logger.info("Starting deployment process")
        result = deployer.run()
        
        logger.info("Execution Result: " + str(result))
        print("Execution Result:")
        print(result)
        
    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        print(f"File not found error: {str(e)}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid value error: {str(e)}")
        print(f"Invalid value error: {str(e)}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command execution failed: {str(e)}")
        print(f"Command execution failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("User Console deployment script completed")
