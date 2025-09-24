import subprocess
import os
import time
import datetime
from datetime import datetime
import json
import requests
import logging
import sys
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound # type: ignore
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('data_replication_deployer')

class PlatformDataReplication:
    def __init__(self, chart_version, customer, metadata_collector, cloud_provider, domain_name,
                 method="local_vault", external_infisical_host=None, slug=None, vault_project_id=None,
                 secret_manager_client_id=None, secret_manager_client_secret=None,
                 project_id=None, cluster_name=None, kube_config_path=None, region=None,
                 namespace="data-replication", data_replication_default_destination_type=None,
                 app_version=None, oauth_chart_version=None):
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
        self.region = region

        # For local development only
        self.local_postgresql = "false"

        # Cloud Provider Specific
        try:
            if self.cloud_provider == "gcp":
                self.project_id = project_id if project_id else f"fast-bi-{customer}"
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.data_replication_k8s_sa = f"data-replication-k8s-sa@{self.project_id}.iam.gserviceaccount.com" if self.project_id else None
                logger.info(f"Configured for GCP with project ID: {self.project_id}")
            elif self.cloud_provider == "aws":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.data_replication_k8s_sa = None
                logger.info(f"Configured for AWS with cluster: {self.cluster_name}")
            elif self.cloud_provider == "azure":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.data_replication_k8s_sa = None
                logger.info(f"Configured for Azure with cluster: {self.cluster_name}")
            elif self.cloud_provider == "self-managed":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.data_replication_k8s_sa = None
                logger.info(f"Configured for self-managed with cluster: {self.cluster_name}")
            else:
                raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")
        except Exception as e:
            logger.error(f"Error during cloud provider configuration: {str(e)}")
            raise
        
        # Set kubeconfig path after cluster_name is properly initialized
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
        
        # Validate cloud provider specific requirements
        if self.cloud_provider == "gcp" and not self.region:
            logger.warning("Region parameter is not provided for GCP. BigQuery will use default region 'europe-central2'")

        # Service specific
        self.customer_root_domain = f"{self.customer}.{self.domain_name}"
        self.ingress_host = f"airbyte.{self.customer_root_domain}"
        self.data_services_admin_email = f"admin@{self.customer_root_domain}"
        self.oauth_realm_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}"
        self.oauth_auth_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}/protocol/openid-connect/auth"
        self.oauth_certs_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}/protocol/openid-connect/certs"
        self.oauth_token_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}/protocol/openid-connect/token"
        self.oauth_callback_url = f"https://{self.ingress_host}/oauth2/callback"
        
        # Chart versions
        self.data_replication_chart_version = chart_version
        self.data_replication_app_version = app_version if app_version else ""
        self.data_replication_oauth_chart_version = oauth_chart_version if oauth_chart_version else "7.18.0"
        
        # Deployment names
        self.data_replication_deployment_name = "data-replication"
        self.data_replication_oauth_deployment_name = "data-replication-oauth"
        self.data_replication_psql_deployment_name = "data-replication-db-psql"
        
        # Chart repositories
        self.data_replication_chart_repo_name = "airbyte"
        self.data_replication_chart_name = "airbyte/airbyte"
        self.data_replication_chart_repo = "https://airbytehq.github.io/helm-charts"
        
        self.data_replication_oauth_chart_repo_name = "oauth2-proxy"
        self.data_replication_oauth_chart_name = "oauth2-proxy/oauth2-proxy"
        self.data_replication_oauth_chart_repo = "https://oauth2-proxy.github.io/manifests"
        
        self.data_replication_psql_chart_repo_name = "bitnami"
        self.data_replication_psql_chart_name = "oci://registry-1.docker.io/bitnamicharts/postgresql"
        self.data_replication_psql_chart_repo = "https://charts.bitnami.com/bitnami"
        self.data_replication_psql_chart_version = "16.6.7"
        
        # Values paths
        self.data_replication_values_path = f"charts/data_services_charts/data_replication/values.yaml"
        self.data_replication_render_template_values_path = f"charts/data_services_charts/data_replication/template_values.yaml"
        self.data_replication_oauth_values_path = f"charts/data_services_charts/data_replication/oauth2proxy_values.yaml"
        self.data_replication_oauth_render_template_values_path = f"charts/data_services_charts/data_replication/template_oauth2proxy_values.yaml"
        self.data_replication_psql_values_path = f"charts/data_services_charts/data_replication/postgresql_values.yaml"
        self.data_replication_psql_render_template_values_path = f"charts/data_services_charts/data_replication/template_postgresql_values.yaml"
        
        # Additional configuration
        self.data_replication_default_destination_type = data_replication_default_destination_type
        self.data_replication_service_base_api_url = f"http://{self.data_replication_deployment_name}-airbyte-server-svc.{self.namespace}.svc.cluster.local:8001/api/public"
        self.data_replication_service_base_webapp_url = f"http://{self.data_replication_deployment_name}-airbyte-webapp-svc.{self.namespace}.svc.cluster.local"

        # MetadataCollection
        self.app_name_data_replication = self.data_replication_chart_name.split('/')[1]
        self.app_name_data_replication_oauth = self.data_replication_oauth_chart_name.split('/')[1]
        self.app_name = {
            "data_replication": self.app_name_data_replication,
            "data_replication_oauth": self.app_name_data_replication_oauth
        }
        self.chart_name = {
            "data_replication": self.data_replication_chart_name,
            "data_replication_oauth": self.data_replication_oauth_chart_name
        }
        self.chart_version = {
            "data_replication": self.data_replication_chart_version,
            "data_replication_oauth": self.data_replication_oauth_chart_version
        }
        self.deployment_name = {
            "data_replication": self.data_replication_deployment_name,
            "data_replication_oauth": self.data_replication_oauth_deployment_name
        }

        # Validate template paths
        self._validate_template_paths()

    def _validate_template_paths(self):
        """Validate that all required template files exist"""
        required_paths = [
            self.data_replication_render_template_values_path,
            self.data_replication_oauth_render_template_values_path,
            self.data_replication_psql_render_template_values_path
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

    def render_data_replication_psql_values_file(self, data_replication_db_username, data_replication_db_name, data_replication_db_repl_username, postgresql_tls_update):
        """Render the PostgreSQL values file from template"""
        logger.info("Rendering PostgreSQL values file from template")
        try:
            context = {
                'chart_name': self.data_replication_psql_chart_repo_name,
                'chart_repo': self.data_replication_psql_chart_repo,
                'chart_version': self.data_replication_psql_chart_version,
                'username': data_replication_db_username,
                'database': data_replication_db_name,
                'replicationUsername': data_replication_db_repl_username,
                'namespace': self.namespace,
                'project_slug': self.slug,
                'method': self.method,
                'postgresql_tls_update': postgresql_tls_update
            }
            # Ensure output directory exists
            output_dir = os.path.dirname(self.data_replication_psql_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            self.render_template(self.data_replication_psql_render_template_values_path, self.data_replication_psql_values_path, context)
            logger.info(f"Successfully rendered PostgreSQL values file to {self.data_replication_psql_values_path}")
        except Exception as e:
            logger.error(f"Failed to render PostgreSQL values file: {str(e)}")
            raise

    def render_data_replication_values_file(self, data_replication_db_username, data_replication_db_name, data_replication_default_destination_type):
        """Render the data replication values file from template"""
        logger.info("Rendering data replication values file from template")
        try:
            context = {
                'chart_name': self.data_replication_chart_repo_name,
                'chart_repo': self.data_replication_chart_repo,
                'chart_version': self.data_replication_chart_version,
                'data_replication_k8s_sa': self.data_replication_k8s_sa,
                'username': data_replication_db_username,
                'database': data_replication_db_name,
                'app_version': self.data_replication_app_version,
                'project_slug': self.slug,
                'namespace': self.namespace,
                'cloud_provider': self.cloud_provider,
                'method': self.method,
                'customer': self.customer,
                'local_postgresql': self.local_postgresql,
                'data_replication_default_destination_type': data_replication_default_destination_type,
                'gcp_project_region': self.region if self.region else "europe-central2",
                'gcp_project_id': self.project_id
            }
            # Ensure output directory exists
            output_dir = os.path.dirname(self.data_replication_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            self.render_template(self.data_replication_render_template_values_path, self.data_replication_values_path, context)
            logger.info(f"Successfully rendered data replication values file to {self.data_replication_values_path}")
        except Exception as e:
            logger.error(f"Failed to render data replication values file: {str(e)}")
            raise

    def render_data_replication_oauth_values_file(self, data_replication_default_destination_type):
        """Render the OAuth values file from template"""
        logger.info("Rendering OAuth values file from template")
        try:
            context = {
                'chart_name': self.data_replication_oauth_chart_repo_name,
                'chart_repo': self.data_replication_oauth_chart_repo,
                'chart_version': self.data_replication_oauth_chart_version,
                'oauth_auth_url': self.oauth_auth_url,
                'oauth_realm_url': self.oauth_realm_url,
                'oauth_certs_url': self.oauth_certs_url,
                'oauth_token_url': self.oauth_token_url,
                'oauth_callback_url': self.oauth_callback_url,
                'customer_root_domain': self.customer_root_domain,
                'ingress_host': self.ingress_host,
                'project_slug': self.slug,
                'namespace': self.namespace,
                'data_services_admin_email': self.data_services_admin_email,
                'customer': self.customer,
                'data_replication_k8s_sa': self.data_replication_k8s_sa,
                'data_replication_service_base_api_url': self.data_replication_service_base_api_url,
                'data_replication_service_base_webapp_url': self.data_replication_service_base_webapp_url,
                'data_replication_default_destination_type': data_replication_default_destination_type,
                'gcp_project_region': self.region if self.region else "europe-central2",
                'gcp_project_id': self.project_id,
                'cloud_provider': self.cloud_provider,
                'method': self.method,
                'local_postgresql': self.local_postgresql
            }
            # Ensure output directory exists
            output_dir = os.path.dirname(self.data_replication_oauth_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            self.render_template(self.data_replication_oauth_render_template_values_path, self.data_replication_oauth_values_path, context)
            logger.info(f"Successfully rendered OAuth values file to {self.data_replication_oauth_values_path}")
        except Exception as e:
            logger.error(f"Failed to render OAuth values file: {str(e)}")
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
        """Authenticate with the vault and return an access token."""
        if self.method != "external_infisical":
            return None
        logger.info("Authenticating with external Infisical vault")
        try:
            auth_url = f"{self.external_infisical_host}/api/v1/auth/universal-auth/login"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {
                "clientId": self.secret_manager_client_id,
                "clientSecret": self.secret_manager_client_secret
            }
            response = requests.post(auth_url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()['accessToken']
        except Exception as e:
            logger.error(f"Failed to authenticate with vault: {str(e)}")
            raise

    def get_secret_from_vault(self, secret_name, secret_path, access_token=None, environment="prod", version=None, secret_type="shared", include_imports="false"):
        """Retrieve the secret from the vault using the appropriate method."""
        if self.method == "external_infisical":
            return self._get_secret_from_external_vault(
                secret_name, secret_path, access_token, environment, version, secret_type, include_imports
            )
        else:
            return self._get_secret_from_local_vault(secret_name, secret_path)

    def _get_secret_from_external_vault(self, secret_name, secret_path, access_token, environment, version, secret_type, include_imports):
        """Retrieve the secret from the external Infisical vault."""
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
        """Retrieve the secret from the local vault JSON file."""
        try:
            with open(self.secret_file, 'r') as f:
                vault_data = json.load(f)
            # Navigate through the JSON structure based on the secret path
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
        logger.info(f"Starting Platform Data Replication deployment for customer: {self.customer}")
        try:
            # Get access token if using external vault
            access_token = self.authenticate_with_vault() if self.method == "external_infisical" else None
            # Get secrets from vault
            logger.info("Retrieving database secrets from vault")
            data_replication_db_username = self.get_secret_from_vault(
                secret_name="username", 
                secret_path="/data-replication/database-secrets/",
                access_token=access_token
            )
            data_replication_db_name = self.get_secret_from_vault(
                secret_name="database", 
                secret_path="/data-replication/database-secrets/",
                access_token=access_token
            )
            data_replication_db_repl_username = self.get_secret_from_vault(
                secret_name="replicationUsername", 
                secret_path="/data-replication/database-secrets/",
                access_token=access_token
            )

            if self.data_replication_default_destination_type:
                data_replication_default_destination_type = self.data_replication_default_destination_type
            else:
                data_replication_default_destination_type = self.get_secret_from_vault(
                    secret_name="DATA_WAREHOUSE_PLATFORM",
                    secret_path="/data-cicd-workflows/customer-cicd-variables/",
                    access_token=access_token
                )
            # Deploy PostgreSQL only if local_postgresql is true
            if self.local_postgresql == "true":
                logger.info("Local PostgreSQL deployment is enabled")
                # Render PostgreSQL values file
                self.render_data_replication_psql_values_file(
                    data_replication_db_username=data_replication_db_username,
                    data_replication_db_name=data_replication_db_name,
                    data_replication_db_repl_username=data_replication_db_repl_username,
                    postgresql_tls_update="false"
                )
                # Deploy PostgreSQL first
                logger.info("Deploying PostgreSQL for Data Replication")
                self.deploy_service(
                    chart_repo_name=self.data_replication_psql_chart_repo_name,
                    chart_repo=self.data_replication_psql_chart_repo,
                    deployment_name=self.data_replication_psql_deployment_name,
                    chart_name=self.data_replication_psql_chart_name,
                    chart_version=self.data_replication_psql_chart_version,
                    namespace=self.namespace,
                    values_path=self.data_replication_psql_values_path
                )
                # Wait for PostgreSQL to be ready
                logger.info("Waiting for PostgreSQL to be ready...")
                self.execute_command([
                    "kubectl", "wait", "--for=condition=ready", "pod",
                    "-l", "app.kubernetes.io/instance=data-replication-db-psql",
                    "-n", self.namespace,
                    "--timeout=300s",
                    "--kubeconfig", self.kube_config
                ])
                # Update PostgreSQL TLS
                logger.info("Updating PostgreSQL TLS")
                self.render_data_replication_psql_values_file(
                    data_replication_db_username=data_replication_db_username,
                    data_replication_db_name=data_replication_db_name,
                    data_replication_db_repl_username=data_replication_db_repl_username,
                    postgresql_tls_update="true"
                )
                # Deploy PostgreSQL Update TLS
                logger.info("Deploying PostgreSQL Update TLS")
                self.deploy_service(
                    chart_repo_name=self.data_replication_psql_chart_repo_name,
                    chart_repo=self.data_replication_psql_chart_repo,
                    deployment_name=self.data_replication_psql_deployment_name,
                    chart_name=self.data_replication_psql_chart_name,
                    chart_version=self.data_replication_psql_chart_version,
                    namespace=self.namespace,
                    values_path=self.data_replication_psql_values_path
                )
                # Wait for PostgreSQL to be ready
                logger.info("Waiting for PostgreSQL to be ready...")
                self.execute_command([
                    "kubectl", "wait", "--for=condition=ready", "pod",
                    "-l", "app.kubernetes.io/instance=data-replication-db-psql",
                    "-n", self.namespace,
                    "--timeout=300s",
                    "--kubeconfig", self.kube_config
                ])
            else:
                logger.info("Using external PostgreSQL, skipping local deployment")
            # Render values files
            self.render_data_replication_oauth_values_file(data_replication_default_destination_type=data_replication_default_destination_type)
            self.render_data_replication_values_file(
                data_replication_db_username=data_replication_db_username,
                data_replication_db_name=data_replication_db_name,
                data_replication_default_destination_type=data_replication_default_destination_type
            )
            # Deploy OAuth
            logger.info("Deploying OAuth for Data Replication")
            self.deploy_service(
                chart_repo_name=self.data_replication_oauth_chart_repo_name,
                chart_repo=self.data_replication_oauth_chart_repo,
                deployment_name=self.data_replication_oauth_deployment_name,
                chart_name=self.data_replication_oauth_chart_name,
                chart_version=self.data_replication_oauth_chart_version,
                namespace=self.namespace,
                values_path=self.data_replication_oauth_values_path
            )
            # Deploy Data Replication
            logger.info("Deploying Data Replication")
            self.deploy_service(
                chart_repo_name=self.data_replication_chart_repo_name,
                chart_repo=self.data_replication_chart_repo,
                deployment_name=self.data_replication_deployment_name,
                chart_name=self.data_replication_chart_name,
                chart_version=self.data_replication_chart_version,
                namespace=self.namespace,
                values_path=self.data_replication_values_path
            )
            # Wait for Data Replication to be ready
            logger.info("Waiting for Data Replication to be ready...")
            self.execute_command([
                "kubectl", "wait", "--for=condition=ready", "pod",
                "-l", "fastbi=data-replication",
                "-n", self.namespace,
                "--timeout=300s",
                "--kubeconfig", self.kube_config
            ])
            # Wait for OAuth to be ready
            logger.info("Waiting for OAuth to be ready...")
            self.execute_command([
                "kubectl", "wait", "--for=condition=ready", "pod",
                "-l", "app=oauth2-proxy",
                "-n", self.namespace,
                "--timeout=300s",
                "--kubeconfig", self.kube_config
            ])
            # Metadata Collection
            app_version_data_replication = self.get_deployed_app_version(self.data_replication_deployment_name, self.namespace)
            app_version_data_replication_oauth = self.get_deployed_app_version(self.data_replication_oauth_deployment_name, self.namespace)
            app_version = {
                "data_replication": app_version_data_replication,
                "data_replication_oauth": app_version_data_replication_oauth
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
            logger.info("Platform Data Replication deployment completed successfully")
            return "Platform Data Replication deployed successfully"
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise

    @classmethod
    def from_cli_args(cls, args):
        """Create a PlatformDataReplication instance from CLI arguments"""
        logger.info("Creating PlatformDataReplication instance from CLI arguments")
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
            region=args.region,
            namespace=args.namespace,
            data_replication_default_destination_type=args.data_replication_default_destination_type,
            app_version=args.app_version,
            oauth_chart_version=args.oauth_chart_version
        )

def main():
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Create metadata collector based on skip_metadata flag
    if args.skip_metadata:
        logger.info("Skipping metadata collection as --skip_metadata is set")
        metadata_collector = DummyMetadataCollector()
    else:
        logger.info("Using SimpleMetadataCollector for metadata collection")
        metadata_collector = SimpleMetadataCollector(args.metadata_file)
    
    try:
        # Initialize the data replication
        logger.info(f"Initializing Platform Data Replication for customer {args.customer}")
        data_replication = PlatformDataReplication(
            customer=args.customer,
            chart_version=args.chart_version,
            cloud_provider=args.cloud_provider,
            domain_name=args.domain_name,
            project_id=args.project_id,
            cluster_name=args.cluster_name,
            kube_config_path=args.kube_config_path,
            region=args.region,
            namespace=args.namespace,
            metadata_collector=metadata_collector,
            method=args.method,
            external_infisical_host=args.external_infisical_host,
            slug=args.slug,
            vault_project_id=args.vault_project_id,
            secret_manager_client_id=args.client_id,
            secret_manager_client_secret=args.client_secret,
            data_replication_default_destination_type=args.data_replication_default_destination_type
        )
        
        # Deploy the data replication
        logger.info("Starting data replication deployment")
        data_replication.run()
        logger.info("Data replication deployment completed successfully")
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        sys.exit(1)

if __name__ == "__main__":
    # Configure file logging if running as main script
    log_file = "data_replication_deployment.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Starting Platform Data Replication deployment script, logging to {log_file}")
    
    parser = argparse.ArgumentParser(
        description="Platform Data Replication Deployment Tool",
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
        help='Chart version for Data Replication'
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

    # Optional arguments
    optional_args = parser.add_argument_group('optional arguments')
    optional_args.add_argument(
        '--project_id',
        help='Cloud provider project ID (default: fast-bi-{customer})'
    )
    optional_args.add_argument(
        '--region',
        help='Cloud provider region (required for GCP BigQuery configuration, will default to europe-central2 if not provided)'
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
        default='data-replication',
        help='Kubernetes namespace for deployment (default: data-replication)'
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
        '--data_replication_default_destination_type',
        default='Disabled',
        help='Default destination type for Data Replication (default: Disabled)'
    )
    optional_args.add_argument(
        '--app_version',
        help='Application version for Data Replication'
    )
    optional_args.add_argument(
        '--oauth_chart_version',
        help='Chart version for OAuth'
    )

    # Parse arguments
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        logger.info(f"Deploying Platform Data Replication for customer: {args.customer}")
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
        logger.info("Creating PlatformDataReplication instance")
        manager = PlatformDataReplication.from_cli_args(args)
        
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
        logger.info("Platform Data Replication deployment script completed")
