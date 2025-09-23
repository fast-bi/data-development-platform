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
from jinja2 import Environment, FileSystemLoader, TemplateNotFound # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('services_monitoring_deployer')

class PlatformMonitoring:
    def __init__(self, chart_version, customer, metadata_collector, cloud_provider, domain_name,
                 method="local_vault", external_infisical_host=None, slug=None, vault_project_id=None,
                 secret_manager_client_id=None, secret_manager_client_secret=None,
                 project_id=None, cluster_name=None, kube_config_path=None, namespace="monitoring"):
        self.deployment_environment = "infrastructure"
        self.external_infisical_host = external_infisical_host
        self.namespace = namespace
        self.project_slug = slug
        self.vault_project_id = vault_project_id
        self.secret_manager_client_id = secret_manager_client_id
        self.secret_manager_client_secret = secret_manager_client_secret
        self.customer = customer
        self.domain_name = domain_name
        self.cloud_provider = cloud_provider
        self.metadata_collector = metadata_collector
        #For local development
        self.local_postgresql = "false"

        # Validate method and required parameters
        if method not in ["local_vault", "external_infisical"]:
            raise ValueError(f"Unsupported method: {method}")
        self.method = method
        
        # Validate method-specific requirements
        if method == "external_infisical":
            if not all([vault_project_id, secret_manager_client_id, secret_manager_client_secret]):
                raise ValueError("vault_project_id, secret_manager_client_id, and secret_manager_client_secret are required for external_infisical method")
        elif method == "local_vault":
            self.secret_file = f"/tmp/{customer}_customer_vault_structure.json"
            if not os.path.exists(self.secret_file):
                raise FileNotFoundError(f"Secret file not found: {self.secret_file}")

        # Service specific
        self.chart_version = chart_version
        self.deployment_name = "monitoring"
        self.chart_repo_name = "grafana"
        self.chart_name = "grafana/grafana"
        self.chart_repo = "https://grafana.github.io/helm-charts"
        self.values_path = f"charts/infra_services_charts/services_monitoring/values.yaml"
        self.render_template_values_path = f"charts/infra_services_charts/services_monitoring/template_values.yaml"
        self.dashboard_render_template_values_path = f"charts/infra_services_charts/services_monitoring/template_dashboard_cm.yaml"
        self.dashboard_values_path = f"charts/infra_services_charts/services_monitoring/dashboard_cm.yaml"
        self.alert_render_template_values_path = f"charts/infra_services_charts/services_monitoring/template_alerts_cm.yaml"
        self.alert_values_path = f"charts/infra_services_charts/services_monitoring/alerts_cm.yaml"
        self.customer_root_domain = f"{self.customer}.{self.domain_name}"
        self.ingress_host = f"monitoring.{self.customer_root_domain}"
        self.oauth_auth_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}/protocol/openid-connect/auth"
        self.oauth_token_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}/protocol/openid-connect/token"
        self.oauth_api_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}/protocol/openid-connect/userinfo"
        self.oauth_signout_redirect_url = f"https://login.{self.customer_root_domain}/realms/{self.customer}/protocol/openid-connect/logout?post_logout_redirect_uri=https%3A%2F%2{self.customer_root_domain}"
        self.monitoring_agent_email = f"no-reply@{self.customer_root_domain}"
        
        # Cloud Provider Specific
        try:
            if self.cloud_provider == "gcp":
                self.project_id = project_id if project_id else f"fast-bi-{customer}"
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                self.monitoring_k8s_sa = f"monitoring-k8s-sa@{self.project_id}.iam.gserviceaccount.com"
                logger.info(f"Configured for GCP with project ID: {self.project_id}")
            elif self.cloud_provider == "aws":  # Leave for future clouds. Not supported yet
                self.project_id = None
                self.monitoring_k8s_sa = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for AWS with cluster: {self.cluster_name}")
            elif self.cloud_provider == "azure":  # Leave for future clouds. Not supported yet
                self.project_id = None
                self.monitoring_k8s_sa = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for Azure with cluster: {self.cluster_name}")
            elif self.cloud_provider == "self-managed":
                self.project_id = None
                self.monitoring_k8s_sa = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
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
        
        # MetadataCollection
        self.app_name = self.chart_name.split('/')[1]
        
        # Validate template paths
        self._validate_template_paths()

    def _validate_template_paths(self):
        """Validate that all required template files exist"""
        required_paths = [
            self.render_template_values_path,
            self.dashboard_render_template_values_path,
            self.alert_render_template_values_path
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

    def deploy_config_maps(self):
        """Deploy ConfigMaps for dashboards and alerts"""
        logger.info("Deploying ConfigMaps")
        try:
            # Create namespace if it doesn't exist
            kubectl_ns_command = f"kubectl create namespace {self.namespace} --save-config --dry-run=client -o=yaml | kubectl --kubeconfig={self.kube_config} apply -f -"
            self.execute_kubectl(kubectl_ns_command)
            
            # Apply ConfigMaps
            kubectl_command = [
                "kubectl", "apply", "-f",
                self.dashboard_values_path,
                "-f", self.alert_values_path,
                "--namespace", self.namespace,
                "--kubeconfig", self.kube_config
            ]
            self.execute_command(kubectl_command)
            logger.info("Successfully deployed ConfigMaps")
        except Exception as e:
            logger.error(f"Failed to deploy ConfigMaps: {str(e)}")
            raise

    def execute_kubectl(self, command):
        """Execute a kubectl command with proper error handling"""
        logger.debug(f"Executing kubectl command: {command}")
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            logger.debug(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Kubectl command failed: {command}")
            logger.error(f"Status code: {e.returncode}")
            logger.error(f"Output: {e.stdout}")
            logger.error(f"Error: {e.stderr}")
            raise Exception(f"Kubectl execution failed: {e.stderr}")

    def execute_command(self, command):
        """Execute a shell command with proper error handling"""
        cmd_str = ' '.join(command) if isinstance(command, list) else command
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

    def render_values_file(self, data_replication_db_username, data_replication_db_password, data_replication_db_database, 
                          data_orchestration_db_username, data_orchestration_db_password, data_orchestration_db_database, 
                          oauth_client_id, oauth_client_secret, data_replication_db_url, data_orchestration_db_url):
        """Render the values file from template"""
        logger.info("Rendering values file from template")
        try:
            context = {
                'chart_name': self.chart_name,
                'chart_repo': self.chart_repo,
                'chart_version': self.chart_version,
                'customer': self.customer,
                'ingress_host': self.ingress_host,
                'cloud_provider': self.cloud_provider,
                'method': self.method,
                'project_slug': self.project_slug,
                'monitoring_k8s_sa': self.monitoring_k8s_sa,
                'data_replication_db_username': data_replication_db_username,
                'data_replication_db_password': data_replication_db_password,
                'data_replication_db_database': data_replication_db_database,
                'data_orchestration_db_username': data_orchestration_db_username,
                'data_orchestration_db_password': data_orchestration_db_password,
                'data_orchestration_db_database': data_orchestration_db_database,
                'oauth_client_id': oauth_client_id,
                'oauth_client_secret': oauth_client_secret,
                'oauth_auth_url': self.oauth_auth_url,
                'oauth_token_url': self.oauth_token_url,
                'oauth_api_url': self.oauth_api_url,
                'oauth_signout_redirect_url': self.oauth_signout_redirect_url,
                'monitoring_agent_email': self.monitoring_agent_email,
                'data_replication_db_url': data_replication_db_url,
                'data_orchestration_db_url': data_orchestration_db_url
            }
            
            # Ensure output directory exists
            output_dir = os.path.dirname(self.values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
                
            self.render_template(self.render_template_values_path, self.values_path, context)
            logger.info(f"Successfully rendered values file to {self.values_path}")
        except Exception as e:
            logger.error(f"Failed to render values file: {str(e)}")
            raise

    def render_cm_files(self):
        """Render ConfigMap files from templates"""
        logger.info("Rendering ConfigMap files")
        try:
            context = {
                'project_id': self.project_id
            }
            
            # Ensure output directories exist
            for path in [self.dashboard_values_path, self.alert_values_path]:
                output_dir = os.path.dirname(path)
                if not os.path.exists(output_dir):
                    logger.info(f"Creating output directory: {output_dir}")
                    os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(self.dashboard_render_template_values_path, self.dashboard_values_path, context)
            self.render_template(self.alert_render_template_values_path, self.alert_values_path, context)
            logger.info("Successfully rendered ConfigMap files")
        except Exception as e:
            logger.error(f"Failed to render ConfigMap files: {str(e)}")
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
            auth_url = f"{self.external_infisical_host}/v1/auth/universal-auth/login"
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
        logger.info(f"Getting secret {secret_name} from external vault")
        try:
            url = f"{self.external_infisical_host}/v3/secrets/raw/{secret_name}"
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
        logger.info(f"Getting secret {secret_name} from local vault")
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
        logger.info(f"Starting Platform Monitoring deployment for customer: {self.customer}")
        try:
            # Get secrets from vault
            access_token = self.authenticate_with_vault()
            
            # Get database secrets
            data_replication_db_username = self.get_secret_from_vault(
                secret_name="username", 
                secret_path="/data-replication/database-secrets/",
                access_token=access_token
            )
            data_replication_db_password = self.get_secret_from_vault(
                secret_name="password", 
                secret_path="/data-replication/database-secrets/",
                access_token=access_token
            )
            data_replication_db_database = self.get_secret_from_vault(
                secret_name="database", 
                secret_path="/data-replication/database-secrets/",
                access_token=access_token
            )
            
            data_orchestration_db_username = self.get_secret_from_vault(
                secret_name="username", 
                secret_path="/data-orchestration/database-secrets/",
                access_token=access_token
            )
            data_orchestration_db_password = self.get_secret_from_vault(
                secret_name="password", 
                secret_path="/data-orchestration/database-secrets/",
                access_token=access_token
            )
            data_orchestration_db_database = self.get_secret_from_vault(
                secret_name="database", 
                secret_path="/data-orchestration/database-secrets/",
                access_token=access_token
            )
            
            # Get OAuth secrets
            oauth_client_id = self.get_secret_from_vault(
                secret_name="CLIENT_ID", 
                secret_path="/data-platform-monitoring/sso-clients-secrets/",
                access_token=access_token
            )
            oauth_client_secret = self.get_secret_from_vault(
                secret_name="CLIENT_SECRET", 
                secret_path="/data-platform-monitoring/sso-clients-secrets/",
                access_token=access_token
            )
            
            if self.local_postgresql == "true":
                data_replication_db_url = "data-replication-db-airbyte-read.data-replication.svc.cluster.local:5432"
                data_orchestration_db_url = "data-orchestration-postgresql-read.data-orchestration.svc.cluster.local:5432"
            else:
                data_replication_db_url = "fastbi-global-psql.global-postgresql.svc.cluster.local:5432"
                data_orchestration_db_url = "fastbi-global-psql.global-postgresql.svc.cluster.local:5432"

                # Render and deploy
            self.render_values_file(
                data_replication_db_url=data_replication_db_url,
                data_orchestration_db_url=data_orchestration_db_url,
                data_replication_db_username=data_replication_db_username,
                data_replication_db_password=data_replication_db_password,
                data_replication_db_database=data_replication_db_database,
                data_orchestration_db_username=data_orchestration_db_username,
                data_orchestration_db_password=data_orchestration_db_password,
                data_orchestration_db_database=data_orchestration_db_database,
                oauth_client_id=oauth_client_id,
                oauth_client_secret=oauth_client_secret
            )
            
            self.render_cm_files()
            self.deploy_config_maps()
            
            # Deploy service
            logger.info("Deploying monitoring service")
            self.deploy_service(
                chart_repo_name=self.chart_repo_name,
                chart_repo=self.chart_repo,
                deployment_name=self.deployment_name,
                chart_name=self.chart_name,
                chart_version=self.chart_version,
                namespace=self.namespace,
                values_path=self.values_path
            )
            
            # Metadata Collection
            app_version = self.get_deployed_app_version(self.deployment_name, self.namespace)
            deployment_record = {
                "customer": self.customer,
                "customer_main_domain": f"{self.customer}.{self.domain_name}",
                "customer_vault_slug": self.project_slug,
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
            logger.info("Platform Monitoring deployment completed successfully")
            return "Platform Monitoring deployed successfully"
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise

    @classmethod
    def from_cli_args(cls, args):
        """Create a PlatformMonitoring instance from CLI arguments"""
        logger.info("Creating PlatformMonitoring instance from CLI arguments")
        return cls(
            chart_version=args.chart_version,
            customer=args.customer,
            metadata_collector=args.metadata_collector,
            cloud_provider=args.cloud_provider,
            domain_name=args.domain_name,
            method=args.method,
            external_infisical_host=args.external_infisical_host,
            slug=args.project_slug,
            vault_project_id=args.vault_project_id,
            secret_manager_client_id=args.client_id,
            secret_manager_client_secret=args.client_secret,
            project_id=args.project_id,
            cluster_name=args.cluster_name,
            kube_config_path=args.kube_config_path,
            namespace=args.namespace
        )

if __name__ == "__main__":
    # Configure file logging if running as main script
    log_file = "services_monitoring_deployment.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Starting Platform Monitoring deployment script, logging to {log_file}")
    
    parser = argparse.ArgumentParser(
        description="Platform Monitoring Deployment Tool",
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
        help='Chart version for Grafana'
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
        '--external_infisical_host',
        help='External Infisical host (required if method is external_infisical)'
    )
    optional_args.add_argument(
        '--project_slug',
        help='Project slug for the vault (required for local_vault method)'
    )
    optional_args.add_argument(
        '--vault_project_id',
        help='Vault project ID (required for external_infisical method)'
    )
    optional_args.add_argument(
        '--client_id',
        help='Secret manager client ID (required for external_infisical method)'
    )
    optional_args.add_argument(
        '--client_secret',
        help='Secret manager client secret (required for external_infisical method)'
    )
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
        default='monitoring',
        help='Kubernetes namespace for deployment (default: monitoring)'
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

    # Parse arguments
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        logger.info(f"Deploying Platform Monitoring for customer: {args.customer}")
        logger.info(f"Cloud provider: {args.cloud_provider}")
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
        logger.info("Creating PlatformMonitoring instance")
        manager = PlatformMonitoring.from_cli_args(args)
        
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
        logger.info("Platform Monitoring deployment script completed")
