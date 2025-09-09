import subprocess
import os
import datetime
from datetime import datetime
import json
import requests
import logging
import sys
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_analysis_deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('data_analysis_deployer')

class DataAnalysisDeployer:
    def __init__(self, chart_version, customer, metadata_collector, cloud_provider, domain_name,
                 method="local_vault", external_infisical_host=None, slug=None, vault_project_id=None,
                 secret_manager_client_id=None, secret_manager_client_secret=None,
                 project_id=None, cluster_name=None, kube_config_path=None,
                 namespace="data-analysis", app_version=None, bi_system="lightdash"):
        self.deployment_environment = "data-services"
        self.external_infisical_host = external_infisical_host
        self.cloud_provider = cloud_provider
        self.domain_name = domain_name
        self.namespace = namespace
        self.slug = slug
        self.vault_project_id = vault_project_id
        self.secret_manager_client_id = secret_manager_client_id
        self.secret_manager_client_secret = secret_manager_client_secret
        self.customer = customer
        self.metadata_collector = metadata_collector
        self.chart_version = chart_version
        self.app_version = app_version
        self.bi_system = bi_system

        # For local development only
        self.local_postgresql = "false"

        # Cloud Provider Specific
        try:
            if self.cloud_provider == "gcp":
                self.project_id = project_id if project_id else f"fast-bi-{customer}"
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.bi_data_k8s_sa = f"bi-data-k8s-sa@{self.project_id}.iam.gserviceaccount.com"
                logger.info(f"Configured for GCP with project ID: {self.project_id}")
            elif self.cloud_provider == "aws":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.bi_data_k8s_sa = None
                logger.info(f"Configured for AWS with cluster: {self.cluster_name}")
            elif self.cloud_provider == "azure":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.bi_data_k8s_sa = None
                logger.info(f"Configured for Azure with cluster: {self.cluster_name}")
            elif self.cloud_provider == "self-managed":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.bi_data_k8s_sa = None
                logger.info(f"Configured for self-managed with cluster: {self.cluster_name}")
            else:
                raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")
        except Exception as e:
            logger.error(f"Error during cloud provider configuration: {str(e)}")
            raise

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

        # Service specific
        self.customer_root_domain = f"{self.customer}.{self.domain_name}"
        self.ingress_host = f"bi.{self.customer_root_domain}"
        self.bi_basic_user = "root-fastbi-bi-admin"
        self.bi_basic_user_name = "Administrator"
        self.bi_basic_user_last_name = f"{self.customer}_FastBI"
        self.bi_admin_email = f"root-fastbi-bi-admin@{self.customer_root_domain}"
        self.bi_smtp_mail_from = f"noreply@{self.customer_root_domain}"

        # OAuth URLs
        self.oauth_realm_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}"
        self.oauth_real_well_known_url = f"{self.oauth_realm_url}/.well-known/openid-configuration"
        self.oauth_auth_url = f"{self.oauth_realm_url}/protocol/openid-connect/auth"
        self.oauth_userinfo_url = f"{self.oauth_realm_url}/protocol/openid-connect/userinfo"
        self.oauth_token_url = f"{self.oauth_realm_url}/protocol/openid-connect/token"
        self.oauth_token_introspection_url = f"{self.oauth_realm_url}/protocol/openid-connect/token/introspect"
        self.oauth_protocol_url = f"{self.oauth_realm_url}/protocol/"

        # S3 endpoint
        self.s3_enpoint = "http://minio.minio.svc.cluster.local"

        # Chart versions and paths
        self.data_analysis_chart_repo_name = "kube-core"
        self.data_analysis_chart_name = "kube-core/raw"
        self.data_analysis_chart_repo = "https://kube-core.github.io/helm-charts"
        self.data_analysis_chart_version = "0.1.1"

        self.bi_psql_chart_repo_name = "bitnami"
        self.bi_psql_chart_name = "bitnami/postgresql"
        self.bi_psql_chart_repo = "https://charts.bitnami.com/bitnami"
        self.bi_psql_chart_version = "16.6.2"

        # Data Analysis Deployment names
        self.bi_psql_deployment_name = "data-analysis-bi-psql"
        self.data_analysis_deployment_name = "data-analysis-hub-extra"

        # Values paths
        self.data_analysis_values_path = f"charts/data_services_charts/data_analysis/values.yaml"
        self.data_analysis_render_template_values_path = f"charts/data_services_charts/data_analysis/template_values.yaml"
        self.bi_psql_values_path = f"charts/data_services_charts/data_analysis/postgresql_values.yaml"
        self.bi_psql_render_template_values_path = f"charts/data_services_charts/data_analysis/template_postgresql_values.yaml"
        
        # Initialize BI system specific variables
        self._initialize_bi_system()

        # Set app_name after BI system initialization
        self.app_name = self.chart_name.split('/')[1] if '/' in self.chart_name else self.chart_name

        # Validate template paths
        self._validate_template_paths()

    def _initialize_bi_system(self):
        """Initialize BI system specific variables"""
        if self.bi_system == "superset":
            self._initialize_superset()
        elif self.bi_system == "lightdash":
            self._initialize_lightdash()
        elif self.bi_system == "metabase":
            self._initialize_metabase()
        elif self.bi_system == "looker":
            self._initialize_looker()
        else:
            raise ValueError(f"Unsupported BI system: {self.bi_system}")

    def _initialize_superset(self):
        """Initialize Superset specific variables"""
        self.deployment_name = "data-analysis-hub"
        self.chart_repo_name = "superset"
        self.chart_name = "superset/superset"
        self.chart_repo = "https://apache.github.io/superset"
        self.values_path = f"charts/data_services_charts/data_analysis/superset/values.yaml"
        self.render_template_values_path = f"charts/data_services_charts/data_analysis/superset/template_values.yaml"

    def _initialize_lightdash(self):
        """Initialize Lightdash specific variables"""
        self.deployment_name = "data-analysis-hub"
        self.chart_repo_name = "lightdash"
        self.chart_name = "lightdash/lightdash"
        self.chart_repo = "https://lightdash.github.io/helm-charts"
        self.values_path = f"charts/data_services_charts/data_analysis/lightdash/values.yaml"
        self.render_template_values_path = f"charts/data_services_charts/data_analysis/lightdash/template_values.yaml"

    def _initialize_metabase(self):
        """Initialize Metabase specific variables"""
        self.deployment_name = "data-analysis-hub"
        self.chart_repo_name = "metabase"
        self.chart_name = "metabase/metabase"
        self.chart_repo = "https://pmint93.github.io/helm-charts"
        self.values_path = f"charts/data_services_charts/data_analysis/metabase/values.yaml"
        self.render_template_values_path = f"charts/data_services_charts/data_analysis/metabase/template_values.yaml"

    def _initialize_looker(self):
        """Initialize Looker specific variables"""
        self.deployment_name = "data-analysis-looker"
        self.chart_repo_name = "looker"
        self.chart_name = "looker"
        self.chart_repo = "https://looker.github.io/helm-charts"
        self.values_path = f"charts/data_services_charts/data_analysis/looker/values.yaml"
        self.render_template_values_path = f"charts/data_services_charts/data_analysis/looker/template_values.yaml"

    def _validate_template_paths(self):
        """Validate that all required template files exist"""
        required_paths = [
            self.bi_psql_render_template_values_path,
            self.render_template_values_path
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
                "--timeout", "30m",
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

    def render_data_bi_psql_values_file(self, data_bi_psql_username, data_bi_psql_database, data_bi_psql_repl_username):
        """Render the PostgreSQL values file from template"""
        logger.info("Rendering PostgreSQL values file from template")
        try:
            context = {
                'chart_name': self.bi_psql_chart_repo_name,
                'chart_repo': self.bi_psql_chart_repo,
                'chart_version': self.bi_psql_chart_version,
                'username': data_bi_psql_username,
                'database': data_bi_psql_database,
                'replication_username': data_bi_psql_repl_username,
                'namespace': self.namespace,
                'project_slug': self.slug,
                'method': self.method
            }
            
            # Ensure output directory exists
            output_dir = os.path.dirname(self.bi_psql_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(self.bi_psql_render_template_values_path, self.bi_psql_values_path, context)
            logger.info(f"Successfully rendered PostgreSQL values file to {self.bi_psql_values_path}")
        except Exception as e:
            logger.error(f"Failed to render PostgreSQL values file: {str(e)}")
            raise

    def render_data_analysis_values_file(self, data_analysis_values_path, data_analysis_render_template_values_path, chart_name, chart_repo, chart_version, bi_smtp_host, bi_smtp_port, bi_smtp_user, bi_smtp_password, bi_cache_redis_password, bi_psql_username, bi_psql_database, bi_psql_repl_user_name, bi_psql_password, bi_psql_host, bi_psql_port, bi_cookie_secret, oauth_client_id, oauth_client_secret, oauth_client_secret_token, bi_basic_user, bi_basic_user_name, bi_basic_user_last_name, bi_admin_email, bi_admin_password, jwt_secret):
        """Render the Data Analysis values file from template"""
        logger.info("Rendering Data Analysis values file from template")
        try:
            context = {
                # Lightdash 
                'bi_system': self.bi_system,
                'data_analysis_deployment_name': self.deployment_name,
                'data_analysis_app_name': self.app_name,
                'data_analysis_app_version': self.app_version,
                'namespace': self.namespace,
                'customer': self.customer,
                'customer_root_domain': self.customer_root_domain,
                'domain_name': self.domain_name,
                'cloud_provider': self.cloud_provider,
                'method': self.method,
                'project_slug': self.slug,
                'local_postgresql': self.local_postgresql,
                'chart_name': chart_name,
                'chart_repo': chart_repo,
                'chart_version': chart_version,
                'ingress_host': self.ingress_host,
                'oauth_real_well_known_url': self.oauth_real_well_known_url,
                'oauth_protocol_url': self.oauth_protocol_url,
                'oauth_realm_url': self.oauth_realm_url,
                'bi_smtp_host': bi_smtp_host,
                'bi_smtp_port': bi_smtp_port,
                'bi_smtp_user': bi_smtp_user,
                'bi_smtp_password': bi_smtp_password,
                'bi_smtp_mail_from': self.bi_smtp_mail_from,
                'bi_cache_redis_password': bi_cache_redis_password,
                'bi_psql_username': bi_psql_username,
                'bi_psql_database': bi_psql_database,
                'bi_psql_repl_username': bi_psql_repl_user_name,
                'bi_psql_password': bi_psql_password,
                'bi_psql_host': bi_psql_host,
                'bi_psql_port': bi_psql_port,
                'bi_data_k8s_sa': self.bi_data_k8s_sa,
                'bi_cookie_secret': bi_cookie_secret,
                'oauth_client_id': oauth_client_id,
                'oauth_client_secret': oauth_client_secret,
                'oauth_client_secret_token': oauth_client_secret_token,
                'bi_basic_user': bi_basic_user,
                'bi_basic_user_name': bi_basic_user_name,
                'bi_basic_user_last_name': bi_basic_user_last_name,
                'bi_admin_email': bi_admin_email,
                'bi_admin_password': bi_admin_password,
                'bi_app_version': self.app_version,
                'jwt_secret': jwt_secret,
                's3_enpoint': self.s3_enpoint,
            }
            
            # Ensure output directory exists
            output_dir = os.path.dirname(data_analysis_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(data_analysis_render_template_values_path, data_analysis_values_path, context)
            logger.info(f"Successfully rendered Data Analysis values file to {data_analysis_values_path}")
        except Exception as e:
            logger.error(f"Failed to render Data Analysis values file: {str(e)}")
            raise

    def render_extra_values_file(self):
        """Render the extra values file from template"""
        logger.info("Rendering extra values file from template")
        try:
            context = {
                'chart_name': self.chart_repo_name,
                'chart_repo': self.chart_repo,
                'chart_version': self.chart_version,
                'namespace': self.namespace,
                'project_slug': self.slug,
                'method': self.method,
                'customer': self.customer,
                'domain_name': self.domain_name,
                'cloud_provider': self.cloud_provider
            }
            
            # Ensure output directory exists
            output_dir = os.path.dirname(self.bi_extra_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(self.bi_extra_render_template_values_path, self.bi_extra_values_path, context)
            logger.info(f"Successfully rendered extra values file to {self.bi_extra_values_path}")
        except Exception as e:
            logger.error(f"Failed to render extra values file: {str(e)}")
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
                logger.debug(f"Template rendered successfully")
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
        logger.info(f"Starting Platform Data Analysis deployment for customer: {self.customer}")
        try:
            # Get access token if using external vault
            access_token = self.authenticate_with_vault() if self.method == "external_infisical" else None
            
            # Get secrets from vault
            logger.info("Retrieving secrets from vault")

            bi_smtp_host = self.get_secret_from_vault(
                secret_name="smtp_host",
                secret_path="/data-analysis/smtp-secrets/",
                access_token=access_token
            )
            bi_smtp_port = self.get_secret_from_vault(
                secret_name="smtp_port",
                secret_path="/data-analysis/smtp-secrets/",
                access_token=access_token
            )
            bi_smtp_user = self.get_secret_from_vault(
                secret_name="smtp_username",
                secret_path="/data-analysis/smtp-secrets/",
                access_token=access_token
            )
            bi_smtp_password = self.get_secret_from_vault(
                secret_name="password",
                secret_path="/data-analysis/smtp-secrets/",
                access_token=access_token
            )
            bi_cache_redis_password = self.get_secret_from_vault(
                secret_name="password",
                secret_path="/data-analysis/redis-secrets/",
                access_token=access_token
            )
            bi_psql_username = self.get_secret_from_vault(
                secret_name="username",
                secret_path="/data-analysis/database-secrets/",
                access_token=access_token
            )
            
            bi_psql_password = self.get_secret_from_vault(
                secret_name="password",
                secret_path="/data-analysis/database-secrets/",
                access_token=access_token
            )

            bi_psql_database = self.get_secret_from_vault(
                secret_name="database",
                secret_path="/data-analysis/database-secrets/",
                access_token=access_token
            )

            bi_psql_repl_user_name = self.get_secret_from_vault(
                secret_name="replicationUsername",
                secret_path="/data-analysis/database-secrets/",
                access_token=access_token
            )
            
            bi_cookie_secret = self.get_secret_from_vault(
                secret_name="COOKIE_SECRET",
                secret_path="/data-analysis/sso-clients-secrets/",
                access_token=access_token
            )

            oauth_client_id = self.get_secret_from_vault(
                secret_name="CLIENT_ID",
                secret_path="/data-analysis/sso-clients-secrets/",
                access_token=access_token
            )

            oauth_client_secret = self.get_secret_from_vault(
                secret_name="CLIENT_SECRET",
                secret_path="/data-analysis/sso-clients-secrets/",
                access_token=access_token
            )
            
                        # Get BI system specific secrets
            if self.bi_system == "superset":
                bi_admin_password = self.get_secret_from_vault(
                    secret_name="password",
                    secret_path="/data-analysis/superset/root-secrets/",
                    access_token=access_token
                )
                jwt_secret = self.get_secret_from_vault(
                    secret_name="SUPERSET_SECRET_KEY",
                    secret_path="/data-analysis/superset/root-secrets/",
                    access_token=access_token
                )
            elif self.bi_system == "metabase":
                jwt_secret = None
                bi_admin_password = self.get_secret_from_vault(
                    secret_name="METABASE_PASSWORD",
                    secret_path="/data-analysis/metabase/root-secrets/",
                    access_token=access_token
                )
            elif self.bi_system == "lightdash":
                jwt_secret = None
                bi_admin_password = self.get_secret_from_vault(
                    secret_name="adminPassword",
                    secret_path="/data-analysis/lightdash/root-secrets/",
                    access_token=access_token
                )
            else:
                raise ValueError(f"Unsupported BI system: {self.bi_system}")    


            if self.local_postgresql == "true":
                bi_psql_host = f"data-analysis-bi-psql.{self.namespace}.svc.cluster.local"
            else:
                bi_psql_host = "fastbi-global-psql.global-postgresql.svc.cluster.local"

            bi_psql_port = "5432"

            # Deploy PostgreSQL if local_postgresql is True
            if self.local_postgresql == "true":
                # Render PostgreSQL values file
                self.render_data_bi_psql_values_file(
                    data_bi_psql_username=bi_psql_username,
                    data_bi_psql_database=bi_psql_database,
                    data_bi_psql_repl_username=bi_psql_repl_user_name
                )

                # Deploy PostgreSQL first
                logger.info("Deploying PostgreSQL for Data Analysis")
                self.deploy_service(
                    chart_repo_name=self.bi_psql_chart_repo_name,
                    chart_repo=self.bi_psql_chart_repo,
                    deployment_name=self.bi_psql_deployment_name,
                    chart_name=self.bi_psql_chart_name,
                    chart_version=self.bi_psql_chart_version,
                    namespace=self.namespace,
                    values_path=self.bi_psql_values_path
                )
                
                # Wait for PostgreSQL to be ready
                logger.info("Waiting for PostgreSQL to be ready...")
                self.execute_command([
                    "kubectl", "wait", "--for=condition=ready", "pod",
                    "-l", "app.kubernetes.io/instance=data-analysis-bi-psql",
                    "-n", self.namespace,
                    "--timeout=300s",
                    "--kubeconfig", self.kube_config
                ])
            else:
                logger.info("Using external PostgreSQL, skipping local deployment")
            
            # Render BI system values file extra values file
            self.render_data_analysis_values_file(
            data_analysis_values_path = self.data_analysis_values_path,
            data_analysis_render_template_values_path = self.data_analysis_render_template_values_path,
            chart_name = self.data_analysis_chart_name,
            chart_repo = self.data_analysis_chart_repo,
            chart_version = self.data_analysis_chart_version,
            bi_smtp_host = None,
            bi_smtp_port = None,
            bi_smtp_user = None,
            bi_smtp_password = None,
            bi_psql_username = None,
            bi_psql_password = None,
            bi_psql_database = None,
            bi_psql_repl_user_name = None,
            bi_psql_host = bi_psql_host,
            bi_psql_port = bi_psql_port,
            bi_cookie_secret = None,
            oauth_client_id = None,
            oauth_client_secret = None,
            oauth_client_secret_token = None,
            bi_basic_user = None,
            bi_basic_user_name = None,
            bi_basic_user_last_name = None,
            bi_admin_email = None,
            bi_admin_password = None,
            bi_cache_redis_password = None,
            jwt_secret = None
            )

            # Deploy BI system extra values file
            logger.info(f"Deploying extra {self.bi_system} for Data Analysis")
            self.deploy_service(
                chart_repo_name=self.data_analysis_chart_repo_name,
                chart_repo=self.data_analysis_chart_repo,
                deployment_name=self.data_analysis_deployment_name,
                chart_name=self.data_analysis_chart_name,
                chart_version=self.data_analysis_chart_version,
                namespace=self.namespace,
                values_path=self.data_analysis_values_path
            )
            
            # Render BI system values file
            self.render_data_analysis_values_file(
            data_analysis_values_path = self.values_path,
            data_analysis_render_template_values_path = self.render_template_values_path,
            chart_name = self.chart_name,
            chart_repo = self.chart_repo,
            chart_version = self.chart_version,
            bi_smtp_host = bi_smtp_host,
            bi_smtp_port = bi_smtp_port,
            bi_smtp_user = bi_smtp_user,
            bi_smtp_password = bi_smtp_password,
            bi_psql_username = bi_psql_username,
            bi_psql_password = bi_psql_password,
            bi_psql_database = bi_psql_database,
            bi_psql_repl_user_name = bi_psql_repl_user_name,
            bi_psql_host = bi_psql_host,
            bi_psql_port = bi_psql_port,
            bi_cache_redis_password = bi_cache_redis_password,
            bi_cookie_secret = bi_cookie_secret,
            oauth_client_id = oauth_client_id,
            oauth_client_secret = oauth_client_secret,
            oauth_client_secret_token = bi_cookie_secret,
            bi_basic_user = self.bi_basic_user,
            bi_basic_user_name = self.bi_basic_user_name,
            bi_basic_user_last_name = self.bi_basic_user_last_name,
            bi_admin_email = self.bi_admin_email,
            bi_admin_password = bi_admin_password,
            jwt_secret = jwt_secret
            )
            
            # Deploy BI system
            logger.info(f"Deploying {self.bi_system} for Data Analysis")
            self.deploy_service(
                chart_repo_name=self.chart_repo_name,
                chart_repo=self.chart_repo,
                deployment_name=self.deployment_name,
                chart_name=self.chart_name,
                chart_version=self.chart_version,
                namespace=self.namespace,
                values_path=self.values_path
            )
            
            # Deploy extra resources if needed
            # self.deploy_extra_resources()
            
            # Wait for Data Analysis to be ready
            logger.info("Waiting for Data Analysis to be ready...")
            self.execute_command([
                "kubectl", "wait", "--for=condition=ready", "pod",
                "-l", f"fastbi=data-analysis-hub",
                "-n", self.namespace,
                "--timeout=300s",
                "--kubeconfig", self.kube_config
            ])

            # Metadata Collection
            app_version_data_analysis_psql = self.get_deployed_app_version(self.bi_psql_deployment_name, self.namespace) if self.local_postgresql == "true" else None
            app_version_data_analysis = self.get_deployed_app_version(self.deployment_name, self.namespace)
            
            app_version = {
                "data_analysis_psql": app_version_data_analysis_psql,
                "data_analysis": app_version_data_analysis
            }
            
            deployment_record = {
                "customer": self.customer,
                "customer_main_domain": self.customer_root_domain,
                "customer_vault_slug": self.slug,
                "deployment_environment": self.deployment_environment,
                "deployment_name": self.deployment_name,
                "chart_name": self.chart_name,
                "chart_version": self.chart_version,
                "app_name": self.app_name,
                "app_version": app_version,
                "deploy_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            logger.info("Adding deployment record to metadata collector")
            self.metadata_collector.add_deployment_record(deployment_record)
            logger.info("Platform Data Analysis deployment completed successfully")
            return "Platform Data Analysis deployed successfully"

        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise

    @classmethod
    def from_cli_args(cls, args):
        """Create a PlatformDataAnalysis instance from CLI arguments"""
        logger.info("Creating PlatformDataAnalysis instance from CLI arguments")
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
            project_id=args.project_id,
            cluster_name=args.cluster_name,
            kube_config_path=args.kube_config_path,
            namespace=args.namespace,
            app_version=args.app_version,
            bi_system=args.bi_system
        )

if __name__ == "__main__":
    # Configure file logging if running as main script
    log_file = "data_analysis_deployment.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Starting Platform Data Analysis deployment script, logging to {log_file}")
    
    parser = argparse.ArgumentParser(
        description="Platform Data Analysis Deployment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Method group
    method_group = parser.add_argument_group('vault method')
    method_group.add_argument(
        '--method',
        choices=['external_infisical', 'local_vault'],
        default='local_vault',
        help='Vault method to use. Choose between external Infisical service or local HashiCorp vault'
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
        help='Chart version for Data Analysis'
    )
    required_args.add_argument(
        '--cloud_provider',
        required=True,
        choices=['gcp', 'aws', 'azure', 'self-managed'],
        help='Cloud provider where the cluster is running'
    )
    required_args.add_argument(
        '--domain_name',
        required=True,
        help='Domain name for the customer'
    )
    required_args.add_argument(
        '--bi_system',
        required=True,
        choices=['superset', 'lightdash', 'metabase', 'looker'],
        help='BI system to deploy'
    )

    # Optional arguments
    optional_args = parser.add_argument_group('optional arguments')
    optional_args.add_argument(
        '--project_id',
        help='Cloud provider project ID (default: fast-bi-{customer})'
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
        default='data-analysis',
        help='Kubernetes namespace for deployment (default: data-analysis)'
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
        '--app_version',
        help='Application version for Data Analysis'
    )

    # Parse arguments
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        logger.info(f"Deploying Platform Data Analysis for customer: {args.customer}")
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

        # Create manager instance using the CLI factory method
        logger.info("Creating DataAnalysisDeployer instance")
        manager = DataAnalysisDeployer.from_cli_args(args)
        
        # Run the deployment
        logger.info("Starting deployment process")
        result = manager.run()
        
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
        logger.info("Platform Data Analysis deployment script completed")
