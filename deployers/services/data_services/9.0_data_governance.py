import os
import subprocess
from datetime import datetime
import json
import requests
import logging
import sys
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('data_governance_deployer')

class DataGovernanceDeployer:
    def __init__(self, chart_version, customer, metadata_collector, cloud_provider, domain_name,
                 method="local_vault", external_infisical_host=None, slug=None, vault_project_id=None,
                 secret_manager_client_id=None, secret_manager_client_secret=None,
                 project_id=None, cluster_name=None, kube_config_path=None,
                 namespace="data-governance", app_version=None, eck_es_chart_version=None, 
                 eck_es_app_version=None, eck_es_op_chart_version=None, prerequest_chart_version=None,
                 bi_system=None, data_replication_default_destination_type=None, vault_secrets=None
                 ):
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
        self.data_replication_default_destination_type = data_replication_default_destination_type
        self.vault_secrets = vault_secrets
        # For local development only
        self.local_postgresql = "false"

        # Cloud Provider Specific
        try:
            if self.cloud_provider == "gcp":
                if project_id and project_id.strip():
                    self.project_id = project_id
                    logger.info(f"Using provided project_id: {self.project_id}")
                else:
                    self.project_id = f"fast-bi-{customer}"
                    logger.warning(f"No project_id provided, using default: {self.project_id}")
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.data_governance_k8s_sa = f"data-governance-k8s-sa@{self.project_id}.iam.gserviceaccount.com"
                self.monitoring_k8s_sa = f"monitoring-k8s-sa@{self.project_id}.iam.gserviceaccount.com"
                logger.info(f"Configured for GCP with project ID: {self.project_id}")
            elif self.cloud_provider == "aws":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.data_governance_k8s_sa = None
                self.monitoring_k8s_sa = None
                logger.info(f"Configured for AWS with cluster: {self.cluster_name}")
            elif self.cloud_provider == "azure":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.data_governance_k8s_sa = None
                self.monitoring_k8s_sa = None
                logger.info(f"Configured for Azure with cluster: {self.cluster_name}")
            elif self.cloud_provider == "self-managed":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.data_governance_k8s_sa = None
                self.monitoring_k8s_sa = None
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
        self.ingress_host = f"datahub.{self.customer_root_domain}"
        self.ingress_host_gsm = f"datahub-gsm.{self.customer_root_domain}"
        self.data_services_admin_email = f"root-fastbi-data-governance-admin@{self.customer_root_domain}"
        self.oauth_realm_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}/.well-known/openid-configuration"

        # Chart versions and paths
        self.data_governance_chart_version = chart_version
        self.data_governance_app_version = app_version if app_version else "v1.0.0"
        self.data_governance_eck_es_app_version = eck_es_app_version if eck_es_app_version else "8.13.0"
        self.data_governance_deployment_name = "data-governance"
        self.data_governance_chart_repo_name = "datahub"
        self.data_governance_chart_name = "datahub/datahub"
        self.data_governance_chart_repo = "https://helm.datahubproject.io/"
        self.data_governance_values_path = "charts/data_services_charts/data_governance/dh_values.yaml"
        self.data_governance_render_template_values_path = "charts/data_services_charts/data_governance/template_dh_values.yaml"

        # Prerequisites chart
        self.data_governance_prerequest_chart_version = prerequest_chart_version if prerequest_chart_version else ""
        self.data_governance_prerequest_deployment_name = "data-governance-sys"
        self.data_governance_prerequest_chart_repo_name = "datahub"
        self.data_governance_prerequest_chart_name = "datahub/datahub-prerequisites"
        self.data_governance_prerequest_chart_repo = "https://helm.datahubproject.io/"
        self.data_governance_prerequest_values_path = "charts/data_services_charts/data_governance/dh_prerequisites_values.yaml"
        self.data_governance_prerequest_render_template_values_path = "charts/data_services_charts/data_governance/template_dh_prerequisites_values.yaml"

        # Elasticsearch operator
        self.data_governance_eck_es_chart_version = eck_es_chart_version if eck_es_chart_version else ""
        self.data_governance_eck_es_deployment_name = "data-governance-eck-es"
        self.data_governance_eck_es_chart_repo_name = "elastic"
        self.data_governance_eck_es_chart_name = "elastic/eck-elasticsearch"
        self.data_governance_eck_es_chart_repo = "https://helm.elastic.co"
        self.data_governance_eck_es_values_path = "charts/data_services_charts/data_governance/eck_es_values.yaml"
        self.data_governance_eck_es_render_template_values_path = "charts/data_services_charts/data_governance/template_eck_es_values.yaml"

        # Elasticsearch operator
        self.data_governance_eck_es_op_chart_version = eck_es_op_chart_version if eck_es_op_chart_version else ""
        self.data_governance_eck_es_op_deployment_name = "data-governance-eck-es-operator"
        self.data_governance_eck_es_op_chart_repo_name = "elastic"
        self.data_governance_eck_es_op_chart_name = "elastic/eck-operator"
        self.data_governance_eck_es_op_chart_repo = "https://helm.elastic.co"
        self.data_governance_eck_es_op_values_path = "charts/data_services_charts/data_governance/eck_operator_values.yaml"
        self.data_governance_eck_es_op_render_template_values_path = "charts/data_services_charts/data_governance/template_eck_operator_values.yaml"

        # PostgreSQL
        self.data_governance_psql_chart_version = "16.6.7"
        self.data_governance_psql_deployment_name = "data-governance-db"
        self.data_governance_psql_chart_repo_name = "bitnami"
        self.data_governance_psql_chart_name = "oci://registry-1.docker.io/bitnamicharts/postgresql"
        self.data_governance_psql_chart_repo = "https://charts.bitnami.com/bitnami"
        self.data_governance_psql_values_path = "charts/data_services_charts/data_governance/postgresql_values.yaml"
        self.data_governance_psql_render_template_values_path = "charts/data_services_charts/data_governance/template_postgresql_values.yaml"

        # Extra Data Governance values
        self.data_governance_extra_chart_repo_name = "kube-core"
        self.data_governance_extra_chart_name = "kube-core/raw"
        self.data_governance_extra_chart_repo = "https://kube-core.github.io/helm-charts"
        self.data_governance_extra_chart_version = "0.1.1"
        self.data_governance_extra_deployment_name = "data-governance-extra"
        self.data_governance_extra_values_path = "charts/data_services_charts/data_governance/values.yaml"
        self.data_governance_extra_render_template_values_path = "charts/data_services_charts/data_governance/template_values.yaml"

        # Set app_name after BI system initialization
        self.app_name = self.data_governance_chart_name.split('/')[1] if '/' in self.data_governance_chart_name else self.data_governance_chart_name

        # Validate template paths
        self._validate_template_paths()

    def _validate_template_paths(self):
        """Validate that all required template files exist"""
        required_paths = [
            self.data_governance_render_template_values_path,
            self.data_governance_prerequest_render_template_values_path,
            self.data_governance_eck_es_render_template_values_path,
            self.data_governance_eck_es_op_render_template_values_path,
            self.data_governance_psql_render_template_values_path
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

    def render_data_governance_psql_values_file(self, data_governance_psql_username, data_governance_psql_database, data_governance_psql_repl_username):
        """Render the PostgreSQL values file from template"""
        logger.info("Rendering PostgreSQL values file from template")
        try:
            context = {
                'chart_name': self.data_governance_psql_chart_name,
                'chart_repo': self.data_governance_psql_chart_repo,
                'chart_version': self.data_governance_psql_chart_version,
                'username': data_governance_psql_username,
                'database': data_governance_psql_database,
                'replication_username': data_governance_psql_repl_username,
                'namespace': self.namespace,
                'project_slug': self.slug,
                'method': self.method
            }
            
            # Ensure output directory exists
            output_dir = os.path.dirname(self.data_governance_psql_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(self.data_governance_psql_render_template_values_path, self.data_governance_psql_values_path, context)
            logger.info(f"Successfully rendered PostgreSQL values file to {self.data_governance_psql_values_path}")
        except Exception as e:
            logger.error(f"Failed to render PostgreSQL values file: {str(e)}")
            raise

    def render_data_governance_values_file(self, 
                                            data_governance_values_path, 
                                            data_governance_render_template_values_path, 
                                            chart_name, 
                                            chart_repo, 
                                            chart_version, 
                                            data_governance_eck_es_app_version,
                                            data_governance_app_name,
                                            data_governance_app_version, 
                                            ingress_host_gsm, 
                                            ingress_host,
                                            data_governance_default_admin_user, 
                                            data_governance_root_user, 
                                            data_governance_root_password, 
                                            data_governance_viewer_user, 
                                            data_governance_viewer_password,
                                            data_governance_db_username,
                                            data_governance_db_name,
                                            data_governance_db_url, 
                                            data_governance_db_host, 
                                            data_governance_db_host_for_client, 
                                            data_governance_db_port,
                                            bi_system,
                                            data_replication_default_destination_type
                                            ):
        """Render the Data Governance values file from template"""
        logger.info("Rendering Data Governance values file from template")
        try:
            context = {
                'namespace': self.namespace,
                'customer': self.customer,
                'customer_root_domain': self.customer_root_domain,
                'domain_name': self.domain_name,
                'cloud_provider': self.cloud_provider,
                'monitoring_k8s_sa': self.monitoring_k8s_sa,
                'method': self.method,
                'project_slug': self.slug,
                'local_postgresql': self.local_postgresql,
                'chart_name': chart_name,
                'chart_repo': chart_repo,
                'chart_version': chart_version,
                'bi_system': bi_system,
                'data_replication_default_destination_type': data_replication_default_destination_type,
                'vault_secrets': self.vault_secrets,
                'data_governance_deployment_name': self.data_governance_deployment_name,
                'data_governance_app_name': data_governance_app_name,
                'data_governance_app_version': data_governance_app_version,
                'data_governance_eck_es_app_version': data_governance_eck_es_app_version,
                'ingress_host_gsm': ingress_host_gsm,
                'ingress_host': ingress_host,
                'data_governance_default_admin_user': data_governance_default_admin_user,
                'data_governance_root_user': data_governance_root_user,
                'data_governance_root_password': data_governance_root_password,
                'data_governance_viewer_user': data_governance_viewer_user,
                'data_governance_viewer_password': data_governance_viewer_password,
                'oauth_realm_url': self.oauth_realm_url,
                'data_governance_db_username': data_governance_db_username,
                'data_governance_db_name': data_governance_db_name,
                'data_governance_db_url': data_governance_db_url,
                'data_governance_db_host': data_governance_db_host,
                'data_governance_db_host_for_client': data_governance_db_host_for_client,
                'data_governance_db_port': data_governance_db_port
            }
            
            # Ensure output directory exists
            output_dir = os.path.dirname(data_governance_values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(data_governance_render_template_values_path, data_governance_values_path, context)
            logger.info(f"Successfully rendered Data Governance values file to {data_governance_values_path}")
        except Exception as e:
            logger.error(f"Failed to render Data Governance values file: {str(e)}")
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
        logger.info(f"Starting Platform Data Analysis deployment for customer: {self.customer}")
        try:
            # Get access token if using external vault
            access_token = self.authenticate_with_vault() if self.method == "external_infisical" else None
            
            # Get secrets from vault
            logger.info("Retrieving secrets from vault")
            data_governance_default_admin_user = self.get_secret_from_vault(
                secret_name="default_admin_user",
                secret_path="/data-governance/root-secrets",
                access_token=access_token
            )

            data_governance_root_user = self.get_secret_from_vault(
                secret_name="adminUser",
                secret_path="/data-governance/root-secrets",
                access_token=access_token
            )
            data_governance_root_password = self.get_secret_from_vault(
                secret_name="adminPassword",
                secret_path="/data-governance/root-secrets",
                access_token=access_token
            )
            data_governance_viewer_user = self.get_secret_from_vault(
                secret_name="viewerUser",
                secret_path="/data-governance/root-secrets",
                access_token=access_token
            )
            data_governance_viewer_password = self.get_secret_from_vault(
                secret_name="viewerPassword",
                secret_path="/data-governance/root-secrets",
                access_token=access_token
            )
            data_governance_db_username = self.get_secret_from_vault(
                secret_name="username",
                secret_path="/data-governance/database-secrets",
                access_token=access_token
            )
            data_governance_psql_repl_username = self.get_secret_from_vault(
                secret_name="replicationUsername",
                secret_path="/data-governance/database-secrets",
                access_token=access_token
            )
            data_governance_db_name = self.get_secret_from_vault(
                secret_name="database",
                secret_path="/data-governance/database-secrets",
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

            if self.local_postgresql == "true":
                data_governance_db_port = "5432"
                data_governance_db_host = f"data-governance-psql.{self.namespace}.svc.cluster.local:{data_governance_db_port}"
                data_governance_db_url = f"jdbc:postgresql://data-governance-psql.{self.namespace}.svc.cluster.local:5432/datahub?sslmode=prefer"
                data_governance_db_host_for_client = "data-governance-psql"
            else:
                data_governance_db_port = "5432"
                data_governance_db_host = f"fastbi-global-psql.global-postgresql.svc.cluster.local:{data_governance_db_port}"
                data_governance_db_url = "jdbc:postgresql://fastbi-global-psql.global-postgresql.svc.cluster.local:5432/datahub?sslmode=prefer"
                data_governance_db_host_for_client = "fastbi-global-psql.global-postgresql.svc.cluster.local"


            # Deploy PostgreSQL if local_postgresql is True
            if self.local_postgresql == "true":
                # Render PostgreSQL values file
                self.render_data_governance_psql_values_file(
                    data_governance_psql_username=data_governance_db_username,
                    data_governance_psql_database=data_governance_db_name,
                    data_governance_psql_repl_username=data_governance_psql_repl_username
                )

                # Deploy PostgreSQL first
                logger.info("Deploying PostgreSQL for Data Analysis")
                self.deploy_service(
                    chart_repo_name=self.data_governance_psql_chart_repo_name,
                    chart_repo=self.data_governance_psql_chart_repo,
                    deployment_name=self.data_governance_psql_deployment_name,
                    chart_name=self.data_governance_psql_chart_name,
                    chart_version=self.data_governance_psql_chart_version,
                    namespace=self.namespace,
                    values_path=self.data_governance_psql_values_path
                )
                
                # Wait for PostgreSQL to be ready
                logger.info("Waiting for PostgreSQL to be ready...")
                self.execute_command([
                    "kubectl", "wait", "--for=condition=ready", "pod",
                    "-l", "app.kubernetes.io/name=postgresql",
                    "-n", self.namespace,
                    "--timeout=300s",
                    "--kubeconfig", self.kube_config
                ])
            else:
                logger.info("Using external PostgreSQL, skipping local deployment")

            # Render Data Governance values file - Render Data Governance Extra Values
            self.render_data_governance_values_file(
                data_governance_values_path = self.data_governance_extra_values_path,
                data_governance_render_template_values_path = self.data_governance_extra_render_template_values_path,
                chart_name = self.data_governance_extra_chart_name,
                chart_repo = self.data_governance_extra_chart_repo,
                chart_version = self.data_governance_extra_chart_version,
                data_governance_app_name = self.app_name,
                data_governance_app_version = self.app_version,
                data_governance_eck_es_app_version = None,
                ingress_host_gsm = None,
                ingress_host = None,
                data_governance_default_admin_user = None,
                data_governance_root_user = None,
                data_governance_root_password = data_governance_root_password,
                data_governance_viewer_user = None,
                data_governance_viewer_password = None,
                data_governance_db_username = None,
                data_governance_db_name = None,
                data_governance_db_url = None,
                data_governance_db_host = None,
                data_governance_db_host_for_client = None,
                data_governance_db_port = None,
                bi_system = bi_system,
                data_replication_default_destination_type = data_replication_default_destination_type
            )

            # Render Data Governance values file - Render Data Governance ECK Operator
            self.render_data_governance_values_file(
                data_governance_values_path = self.data_governance_eck_es_op_values_path,
                data_governance_render_template_values_path = self.data_governance_eck_es_op_render_template_values_path,
                chart_name = self.data_governance_eck_es_op_chart_name,
                chart_repo = self.data_governance_eck_es_op_chart_repo,
                chart_version = self.data_governance_eck_es_op_chart_version,
                data_governance_app_name = None,
                data_governance_app_version = None,
                data_governance_eck_es_app_version = None,
                ingress_host_gsm = None,
                ingress_host = None,
                data_governance_default_admin_user = None,
                data_governance_root_user = None,
                data_governance_root_password = None,
                data_governance_viewer_user = None,
                data_governance_viewer_password = None,
                data_governance_db_username = None,
                data_governance_db_name = None,
                data_governance_db_url = None,
                data_governance_db_host = None,
                data_governance_db_host_for_client = None,
                data_governance_db_port = None,
                bi_system = None,
                data_replication_default_destination_type = None
            )

            # Render Data Governance values file - Render Data Governance ECK ES
            self.render_data_governance_values_file(
                data_governance_values_path = self.data_governance_eck_es_values_path,
                data_governance_render_template_values_path = self.data_governance_eck_es_render_template_values_path,
                chart_name = self.data_governance_eck_es_chart_name,
                chart_repo = self.data_governance_eck_es_chart_repo,
                chart_version = self.data_governance_eck_es_chart_version,
                data_governance_app_name = None,
                data_governance_app_version = None,
                data_governance_eck_es_app_version = self.data_governance_eck_es_app_version,
                ingress_host_gsm = None,
                ingress_host = None,
                data_governance_default_admin_user = None,
                data_governance_root_user = None,
                data_governance_root_password = None,
                data_governance_viewer_user = None,
                data_governance_viewer_password = None,
                data_governance_db_username = None,
                data_governance_db_name = None,
                data_governance_db_url = None,
                data_governance_db_host = None,
                data_governance_db_host_for_client = None,
                data_governance_db_port = None,
                bi_system = None,
                data_replication_default_destination_type = None
            )
            # Render Data Governance values file - Render Data Governance Prerequest
            self.render_data_governance_values_file(
                data_governance_values_path = self.data_governance_prerequest_values_path,
                data_governance_render_template_values_path = self.data_governance_prerequest_render_template_values_path,
                chart_name = self.data_governance_prerequest_chart_name,
                chart_repo = self.data_governance_prerequest_chart_repo,
                chart_version = self.data_governance_prerequest_chart_version,
                data_governance_app_name = None,
                data_governance_app_version = None,
                data_governance_eck_es_app_version = None,
                ingress_host_gsm = None,
                ingress_host = None,
                data_governance_default_admin_user = None,
                data_governance_root_user = None,
                data_governance_root_password = None,
                data_governance_viewer_user = None,
                data_governance_viewer_password = None,
                data_governance_db_username = None,
                data_governance_db_name = None,
                data_governance_db_url = None,
                data_governance_db_host = None,
                data_governance_db_host_for_client = None,
                data_governance_db_port = None,
                bi_system = None,
                data_replication_default_destination_type = None
            )
            # Render Data Governance values file - Render Data Governance
            self.render_data_governance_values_file(
                data_governance_values_path = self.data_governance_values_path,
                data_governance_render_template_values_path = self.data_governance_render_template_values_path,
                chart_name = self.data_governance_chart_name,
                chart_repo = self.data_governance_chart_repo,
                chart_version = self.data_governance_chart_version,
                data_governance_eck_es_app_version = self.data_governance_eck_es_app_version,
                data_governance_app_name = self.app_name,
                data_governance_app_version = self.app_version,
                ingress_host_gsm = self.ingress_host_gsm,
                ingress_host = self.ingress_host,
                data_governance_default_admin_user = data_governance_default_admin_user,
                data_governance_root_user = data_governance_root_user,
                data_governance_root_password = data_governance_root_password,
                data_governance_viewer_user = data_governance_viewer_user,
                data_governance_viewer_password = data_governance_viewer_password,
                data_governance_db_username = data_governance_db_username,
                data_governance_db_name = data_governance_db_name,
                data_governance_db_url = data_governance_db_url,
                data_governance_db_host = data_governance_db_host,
                data_governance_db_host_for_client = data_governance_db_host_for_client,
                data_governance_db_port = data_governance_db_port,
                bi_system = None,
                data_replication_default_destination_type = None
            )

            # Deploy Data Governance extra values file
            logger.info(f"Deploying extra {self.data_governance_extra_chart_name} for Data Governance")
            self.deploy_service(
                chart_repo_name=self.data_governance_extra_chart_repo_name,
                chart_repo=self.data_governance_extra_chart_repo,
                deployment_name=self.data_governance_extra_deployment_name,
                chart_name=self.data_governance_extra_chart_name,
                chart_version=self.data_governance_extra_chart_version,
                namespace=self.namespace,
                values_path=self.data_governance_extra_values_path
            )
            
            # Deploy Data Governance ECK Operator
            logger.info(f"Deploying {self.data_governance_eck_es_op_chart_name} for Data Governance")
            self.deploy_service(
                chart_repo_name=self.data_governance_eck_es_op_chart_repo_name,
                chart_repo=self.data_governance_eck_es_op_chart_repo,
                deployment_name=self.data_governance_eck_es_op_deployment_name,
                chart_name=self.data_governance_eck_es_op_chart_name,
                chart_version=self.data_governance_eck_es_op_chart_version,
                namespace=self.namespace,
                values_path=self.data_governance_eck_es_op_values_path
            )
            
            # Deploy Data Governance ECK ES
            logger.info(f"Deploying {self.data_governance_eck_es_chart_name} for Data Governance")
            self.deploy_service(
                chart_repo_name=self.data_governance_eck_es_chart_repo_name,
                chart_repo=self.data_governance_eck_es_chart_repo,
                deployment_name=self.data_governance_eck_es_deployment_name,
                chart_name=self.data_governance_eck_es_chart_name,
                chart_version=self.data_governance_eck_es_chart_version,
                namespace=self.namespace,
                values_path=self.data_governance_eck_es_values_path
            )

            # Deploy Data Governance Prerequest
            logger.info(f"Deploying {self.data_governance_prerequest_chart_name} for Data Governance")
            self.deploy_service(
                chart_repo_name=self.data_governance_prerequest_chart_repo_name,
                chart_repo=self.data_governance_prerequest_chart_repo,
                deployment_name=self.data_governance_prerequest_deployment_name,    
                chart_name=self.data_governance_prerequest_chart_name,
                chart_version=self.data_governance_prerequest_chart_version,
                namespace=self.namespace,
                values_path=self.data_governance_prerequest_values_path
            )

            # Deploy Data Governance
            logger.info(f"Deploying {self.data_governance_chart_name} for Data Governance")
            self.deploy_service(
                chart_repo_name=self.data_governance_chart_repo_name,
                chart_repo=self.data_governance_chart_repo,
                deployment_name=self.data_governance_deployment_name,
                chart_name=self.data_governance_chart_name,
                chart_version=self.data_governance_chart_version,
                namespace=self.namespace,
                values_path=self.data_governance_values_path
            )
            
            # Render Data Governance extra values file
            # self.render_extra_values_file()
            # Deploy extra resources if needed
            # logger.info(f"Deploying extra resources for Data Governance")
            # self.deploy_extra_resources()
            
            # Wait for Data Governance to be ready
            logger.info("Waiting for Data Governance to be ready...")
            self.execute_command([
                "kubectl", "wait", "--for=condition=ready", "pod",
                "-l", "fastbi=data-governance",
                "-n", self.namespace,
                "--timeout=300s",
                "--kubeconfig", self.kube_config
            ])

            # Metadata Collection
            app_version_data_governance_eck_es_op = self.get_deployed_app_version(deployment_name=self.data_governance_eck_es_op_deployment_name, namespace=self.namespace)
            app_version_data_governance_eck_es = self.get_deployed_app_version(deployment_name=self.data_governance_eck_es_deployment_name, namespace=self.namespace)
            app_version_data_governance_psql = self.get_deployed_app_version(deployment_name=self.data_governance_psql_deployment_name, namespace=self.namespace) if self.local_postgresql == "true" else None
            app_version_data_governance_dh_prerequest = self.get_deployed_app_version(deployment_name=self.data_governance_prerequest_deployment_name, namespace=self.namespace)
            app_version_data_governance_dh = self.get_deployed_app_version(deployment_name=self.data_governance_deployment_name, namespace=self.namespace)
            
            app_version = {
                "data_governance_eck_es_op": app_version_data_governance_eck_es_op,
                "data_governance_eck_es": app_version_data_governance_eck_es,
                "data_governance_psql": app_version_data_governance_psql,
                "data_governance_dh_prerequest": app_version_data_governance_dh_prerequest,
                "data_governance_dh": app_version_data_governance_dh
            }
            
            deployment_record = {
                "customer": self.customer,
                "customer_main_domain": self.customer_root_domain,
                "customer_vault_slug": self.slug,
                "deployment_environment": self.deployment_environment,
                "deployment_name": self.data_governance_deployment_name,
                "chart_name": self.data_governance_chart_name,
                "chart_version": self.data_governance_chart_version,
                "app_name": self.app_name,
                "app_version": app_version,
                "deploy_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            logger.info("Adding deployment record to metadata collector")
            self.metadata_collector.add_deployment_record(deployment_record)
            logger.info("Platform Data Governance deployment completed successfully")
            return "Platform Data Governance deployed successfully"

        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise

    @classmethod
    def from_cli_args(cls, args):
        """Create a DataGovernanceDeployer instance from CLI arguments"""
        logger.info("Creating DataGovernanceDeployer instance from CLI arguments")
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
            eck_es_chart_version=args.eck_es_chart_version,
            eck_es_app_version=args.eck_es_app_version,
            eck_es_op_chart_version=args.eck_es_op_chart_version,
            prerequest_chart_version=args.prerequest_chart_version,
            bi_system=args.bi_system,
            data_replication_default_destination_type=args.data_replication_default_destination_type,
            vault_secrets=args.vault_secrets
        )

if __name__ == "__main__":
    # Configure file logging if running as main script
    log_file = "data_governance_deployment.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Starting Platform Data Governance deployment script, logging to {log_file}")
    
    parser = argparse.ArgumentParser(
        description="Platform Data Governance Deployment Tool",
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
        help='Chart version for Data Governance'
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
        '--cluster_name',
        help='Kubernetes cluster name (default: fast-bi-{customer}-platform)'
    )
    optional_args.add_argument(
        '--kube_config_path',
        help='Path to kubeconfig file (default: /tmp/{cluster_name}-kubeconfig.yaml)'
    )
    optional_args.add_argument(
        '--namespace',
        default='data-governance',
        help='Kubernetes namespace for deployment (default: data-governance)'
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
        help='Application version for Data Governance'
    )
    optional_args.add_argument(
        '--eck_es_chart_version',
        help='Chart version for ECK Elasticsearch'
    )
    optional_args.add_argument(
        '--eck_es_app_version',
        help='Application version for ECK Elasticsearch'
    )
    optional_args.add_argument(
        '--eck_es_op_chart_version',
        help='Chart version for ECK Operator'
    )
    optional_args.add_argument(
        '--prerequest_chart_version',
        help='Chart version for Prerequisites'
    )
    optional_args.add_argument(
        '--bi_system',
        help='BI system for Data Development Platform'
    )
    optional_args.add_argument(
        '--data_replication_default_destination_type',
        help='Data replication default destination type for Data Development Platform'
    )
    optional_args.add_argument(
        '--vault_secrets',
        help='Vault secrets for Data Governance'
    )
    # Parse arguments
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        logger.info(f"Deploying Platform Data Governance for customer: {args.customer}")
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
        logger.info("Creating DataGovernanceDeployer instance")
        manager = DataGovernanceDeployer.from_cli_args(args)
        
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
        logger.info("Platform Data Governance deployment script completed")
